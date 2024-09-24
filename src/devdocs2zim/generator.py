import argparse
import datetime
import os
import re
from collections import defaultdict
from pathlib import Path

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel
from zimscraperlib.constants import (  # pyright: ignore[reportMissingTypeStubs]
    MAXIMUM_DESCRIPTION_METADATA_LENGTH,
    MAXIMUM_LONG_DESCRIPTION_METADATA_LENGTH,
    RECOMMENDED_MAX_TITLE_LENGTH,
)
from zimscraperlib.zim import (  # pyright: ignore[reportMissingTypeStubs]
    Creator,
    StaticItem,
)
from zimscraperlib.zim.indexing import (  # pyright: ignore[reportMissingTypeStubs]
    IndexData,
)

# pyright: ignore[reportMissingTypeStubs]
from devdocs2zim.client import (
    DevdocsClient,
    DevdocsIndex,
    DevdocsIndexEntry,
    DevdocsMetadata,
)
from devdocs2zim.constants import LANGUAGE_ISO_639_3, NAME, ROOT_DIR, VERSION, logger

# Content to display for pages missing from DevDocs.
MISSING_PAGE = (
    "<h2>This documentation is missing.</h2>"
    "<p>This is an error with the openZIM DevDocs scraper, not your ZIM reader e.g. "
    'Kiwix. Please <a href="https://github.com/openzim/devdocs/issues">'
    "file an issue with the scraper</a>.</p>"
)


class InvalidFormatError(Exception):
    """Raised when a user supplied template has an invalid parameter."""

    pass


class ZimConfig(BaseModel):
    """Common configuration for building ZIM files."""

    # File name for the ZIM.
    file_name_format: str
    # Name for the ZIM.
    name_format: str
    # Human readable title for the ZIM.
    title_format: str
    # Publisher for the ZIM.
    publisher: str
    # Creator of the content in the ZIM.
    creator: str
    # Short description for the ZIM.
    description_format: str
    # Long description for the ZIM.
    long_description_format: str | None
    # Semicolon delimited list of tags to apply to the ZIM.
    tags: str

    @staticmethod
    def add_flags(parser: argparse.ArgumentParser, defaults: "ZimConfig"):
        """Adds flags to the given parser with the given defaults."""
        parser.add_argument(
            "--creator",
            help=f"Name of content creator. Default: {defaults.creator!r}",
            default=defaults.creator,
        )

        parser.add_argument(
            "--publisher",
            help=f"Custom publisher name. Default: {defaults.publisher!r}",
            default=defaults.publisher,
        )

        parser.add_argument(
            "--file-name-format",
            help="Custom file name format for individual ZIMs. "
            f"Default: {defaults.file_name_format!r}",
            default=defaults.file_name_format,
            metavar="FORMAT",
        )

        parser.add_argument(
            "--name-format",
            help="Custom name format for individual ZIMs. "
            f"Default: {defaults.name_format!r}",
            default=defaults.name_format,
            metavar="FORMAT",
        )

        parser.add_argument(
            "--title-format",
            help=f"Custom title format for individual ZIMs. "
            f"Value will be truncated to {RECOMMENDED_MAX_TITLE_LENGTH} chars. "
            f"Default: {defaults.title_format!r}",
            default=defaults.title_format,
            metavar="FORMAT",
        )

        parser.add_argument(
            "--description-format",
            help="Custom description format for individual ZIMs. Value will be "
            f"truncated to {MAXIMUM_DESCRIPTION_METADATA_LENGTH} chars. "
            f"Default: {defaults.title_format!r}",
            default=defaults.description_format,
            metavar="FORMAT",
        )

        parser.add_argument(
            "--long-description-format",
            help="Custom long description format for your ZIM. Value will be "
            f"truncated to {MAXIMUM_LONG_DESCRIPTION_METADATA_LENGTH} chars. "
            f"Default: {defaults.long_description_format!r}",
            default=defaults.long_description_format,
            metavar="FORMAT",
        )

        # Due to https://github.com/python/cpython/issues/60603 defaulting an array in
        # argparse doesn't work so we expose the underlying semicolon delimited string.
        parser.add_argument(
            "--tags",
            help="A semicolon (;) delimited list of tags to add to the ZIM."
            "Formatting is supported. "
            f"Default: {defaults.tags!r}",
            default=defaults.tags,
        )

    @staticmethod
    def of(namespace: argparse.Namespace) -> "ZimConfig":
        """Parses a namespace to create a new ZimConfig."""
        return ZimConfig.model_validate(namespace, from_attributes=True)

    def format(self, placeholders: dict[str, str]) -> "ZimConfig":
        """Creates a ZimConfig with placeholders replaced and results truncated.

        Raises: InvalidFormatError if one of the placeholders is invalid.
        """

        def fmt(string: str) -> str:
            try:
                return string.format(**placeholders)
            except KeyError as e:
                valid_placeholders = ", ".join(sorted(placeholders.keys()))
                raise InvalidFormatError(
                    f"Invalid placeholder {e!s} in {string!r}, "
                    f"valid placeholders are: {valid_placeholders}"
                ) from e

        def check_length(string: str, field_name: str, length: int) -> str:
            if len(string) > length:
                raise ValueError(
                    f"{field_name} '{string[:15]}…' ({len(string)} chars) "
                    f"is longer than the allowed {length} chars"
                )

            return string

        return ZimConfig(
            file_name_format=fmt(self.file_name_format),
            name_format=fmt(self.name_format),
            title_format=check_length(
                fmt(self.title_format),
                "formatted title",
                RECOMMENDED_MAX_TITLE_LENGTH,
            ),
            publisher=self.publisher,
            creator=self.creator,
            description_format=check_length(
                fmt(self.description_format),
                "formatted description",
                MAXIMUM_DESCRIPTION_METADATA_LENGTH,
            ),
            long_description_format=(
                check_length(
                    fmt(self.long_description_format),
                    "formatted long description",
                    MAXIMUM_LONG_DESCRIPTION_METADATA_LENGTH,
                )
                if self.long_description_format
                else None
            ),
            tags=fmt(self.tags),
        )


class MissingDocumentError(Exception):
    """Raised when the user specified a slug that doesn't exist."""

    pass


class DocFilter(BaseModel):
    """Supports filtering documents by user provied attributes."""

    # If truthy, all documents are fetched.
    all: bool | None
    # If > 0 and not None, allow the first N of each slug without version.
    first: int | None
    # If specified, only the given slugs are allowed.
    slugs: list[str] | None

    # If specified, slugs matching the regex are skipped.
    skip_slug_regex: str | None

    @staticmethod
    def add_flags(parser: argparse.ArgumentParser):
        """Adds flags to the given parser with the given defaults."""

        # Force the user to explicitly specify all, or a set of resources to download
        # to prevent mistakes.
        doc_selection = parser.add_mutually_exclusive_group(required=True)
        doc_selection.add_argument(
            "--all",
            action="store_true",
            help="Fetch all Devdocs resources, and produce one ZIM per resource.",
        )
        doc_selection.add_argument(
            "--slug",
            help="Fetch the provided Devdocs resource. "
            "Slugs are the first path entry in the Devdocs URL. "
            "For example, the slug for: `https://devdocs.io/gcc~12/` is `gcc~12`. "
            "Use --slug several times to fetch multiple docs.",
            action="append",
            dest="slugs",
            metavar="SLUG",
        )
        doc_selection.add_argument(
            "--first",
            help="Fetch the first number of items per slug as shown in the DevDocs UI.",
            type=int,
            metavar="N",
        )

        parser.add_argument(
            "--skip-slug-regex",
            help="Skips slugs matching the given regular expression.",
            metavar="REGEX",
        )

    @staticmethod
    def of(namespace: argparse.Namespace) -> "DocFilter":
        """Parses a namespace to create a new DocFilter."""
        return DocFilter.model_validate(namespace, from_attributes=True)

    def filter(self, docs: list[DevdocsMetadata]) -> list[DevdocsMetadata]:
        """Filters docs based on the user's choices."""

        selected: list[DevdocsMetadata] = []
        count_by_type: dict[str, int] = defaultdict(int)
        for metadata in docs:
            if self.skip_slug_regex:
                if re.match(self.skip_slug_regex, metadata.slug):
                    continue

            if self.slugs is not None:
                if metadata.slug in self.slugs:
                    selected.append(metadata)
            elif self.first is not None:
                if count_by_type[metadata.slug_without_version] < self.first:
                    selected.append(metadata)
                    count_by_type[metadata.slug_without_version] += 1
            else:
                selected.append(metadata)

        if self.slugs is not None:
            found_slugs = {metadata.slug for metadata in selected}
            missing = set(self.slugs) - found_slugs
            if len(missing) > 0:
                missing_list = ", ".join(sorted(missing))
                raise MissingDocumentError(
                    f"Unable to find documents with the following slugs: {missing_list}"
                )

        return selected


class Generator:
    """Generates ZIMs based on the user's configuration."""

    def __init__(
        self,
        devdocs_client: DevdocsClient,
        zim_config: ZimConfig,
        doc_filter: DocFilter,
        output_folder: str,
    ) -> None:
        """Initializes Generator.

        Parameters:
            devdocs_client: Client that connects with DevDocs.io
            zim_config: Configuration for ZIM metadata.
            doc_filter: User supplied filter selecting with docs to convert.
            output_folder: Directory to write ZIMs into.
        """
        self.devdocs_client = devdocs_client
        self.zim_config = zim_config
        self.doc_filter = doc_filter
        self.output_folder = output_folder

        os.makedirs(self.output_folder, exist_ok=True)

        # jinja2 environment setup
        self.env = Environment(  # type: ignore
            loader=FileSystemLoader(ROOT_DIR.joinpath("templates")),
            autoescape=select_autoescape(),
        )

        self.page_template = self.env.get_template("page.html")  # type: ignore
        self.licenses_template = self.env.get_template("licenses.txt")  # type: ignore

        self.logo_path = self.asset_path("devdocs_48.png")
        self.copyright_path = self.asset_path("COPYRIGHT")
        self.license_path = self.asset_path("LICENSE")

    @staticmethod
    def asset_path(name: str) -> Path:
        """Returns the path to name in the third_party/devdocs folder.

        Raises ValueError if the resource doesn't exist.
        """
        path = ROOT_DIR.joinpath("third_party", "devdocs", name)
        if not path.exists():
            raise ValueError(f"File not found at {path}")
        return path

    def load_common_files(self) -> list[StaticItem]:
        """Loads common assets for the output."""
        static_files: list[StaticItem] = []

        logger.info("Fetching common CSS...")
        app_css = self.devdocs_client.read_application_css()
        logger.debug(f"  Found app CSS with {len(app_css)} chars.")
        static_files.append(
            StaticItem(
                path="application.css",
                content=app_css,
                is_front=False,
                mimetype="text/css",
                auto_index=False,
            )
        )

        static_files.append(
            StaticItem(
                # Documentation doesn't have file extensions so this
                # file won't conflict with the dynamic content.
                path="licenses.txt",
                content=self.licenses_template.render(  # type: ignore
                    copyright=self.copyright_path.read_text(),
                    license=self.license_path.read_text(),
                ),
                is_front=True,
                mimetype="text/plain",
                auto_index=False,
            )
        )

        return static_files

    def run(self) -> list[Path]:
        """Run the generator to fetch content and produce ZIMs."""

        # Load docs first to fail fast before fetching additional resources.
        all_docs = self.devdocs_client.list_docs()
        selected_doc_metadata = self.doc_filter.filter(all_docs)

        # Check formatting early to bail if any templates are invalid.
        for doc_metadata in selected_doc_metadata:
            self.zim_config.format(doc_metadata.placeholders())

        common_resources = self.load_common_files()

        # List all docs and copy one by one
        generated: list[Path] = []
        for doc_metadata in selected_doc_metadata:
            # TODO(#11): Add progress tracker here.
            generated.append(
                self.generate_zim(
                    doc_metadata,
                    common_resources,
                )
            )

        return generated

    def generate_zim(
        self, doc_metadata: DevdocsMetadata, common_resources: list[StaticItem]
    ) -> Path:
        """Generates a zim for a single document.

        Returns the path to the gernated ZIM.
        """
        logger.info(f"Generating ZIM for {doc_metadata.slug}")

        formatted_config = self.zim_config.format(doc_metadata.placeholders())
        zim_path = Path(self.output_folder, f"{formatted_config.file_name_format}.zim")

        # Don't clobber existing files so a user can resume a failed run.
        if zim_path.exists():
            logger.warning(f"  Skipping, {zim_path} already exists.")
            return zim_path

        logger.info(f"  Writing to: {zim_path}")

        creator = Creator(zim_path, "index")
        creator.config_metadata(
            Name=formatted_config.name_format,
            Title=formatted_config.title_format,
            Publisher=formatted_config.publisher,
            Date=datetime.datetime.now(tz=datetime.UTC).date(),
            Creator=formatted_config.creator,
            Description=formatted_config.description_format,
            LongDescription=formatted_config.long_description_format,
            # As of 2024-07-28 all documentation is in English.
            Language=LANGUAGE_ISO_639_3,
            Tags=formatted_config.tags,
            Scraper=f"{NAME} v{VERSION}",
            Illustration_48x48_at_1=self.logo_path.read_bytes(),
        )

        # Start creator early to detect problems early.
        with creator as started_creator:
            logger.info("  Fetching the index...")
            index = self.devdocs_client.get_index(doc_metadata.slug)
            logger.debug(f"  The index has {len(index.entries)} entries.")

            logger.info("  Fetching the document database...")
            db = self.devdocs_client.get_db(doc_metadata.slug)
            logger.debug(f"  The database has {len(db)} entries.")

            self.add_zim_contents(
                creator=started_creator,
                doc_metadata=doc_metadata,
                index=index,
                db=db,
                common_resources=common_resources,
            )
        return zim_path

    @staticmethod
    def page_titles(pages: list[DevdocsIndexEntry]) -> dict[str, str]:
        """Returns a map between page paths in the DB and their "best" title.

        The best title is either the first navigation item that opens the page
        to the top (i.e. without a path fragment) or the first navigation item
        that opens the page if none open to the top.
        """

        page_to_title: dict[str, str] = {}
        for page in pages:
            path_without_fragment = page.path_without_fragment
            if path_without_fragment == page.path:
                page_to_title[path_without_fragment] = page.name
            elif path_without_fragment not in page_to_title:
                page_to_title[path_without_fragment] = page.name

        return page_to_title

    def add_zim_contents(
        self,
        creator: Creator,
        doc_metadata: DevdocsMetadata,
        index: DevdocsIndex,
        db: dict[str, str],
        common_resources: list[StaticItem],
    ):
        """Adds the doc conents to the ZIM.

        Parameters:
          creator: ZIM writer.
          doc_metadata: Document metadata for generating common pages.
          index: Documentation index for the navigation bar.
          db: Mapping between documentation path and HTML content.
          common_resources: Static content to add to the documentation.
        """

        logger.info("  Adding common resources...")
        for resource in common_resources:
            creator.add_item(resource)  # type: ignore

        page_to_title = self.page_titles(index.entries)
        # Explicitly inject the index which exists for every documentation set
        # but isn't in the dynamic list of pages.
        page_to_title["index"] = f"{doc_metadata.name} Documentation"

        nav_sections = index.build_navigation()

        logger.info(f"  Rendering {len(page_to_title)} pages...")
        counter = 0
        for path, title in page_to_title.items():
            num_slashes = path.count("/")
            rel_prefix = "../" * num_slashes

            content = db.get(path, MISSING_PAGE)
            if path not in db:
                logger.warning(
                    f"  DevDocs is missing content for {title!r} at {path!r}."
                )

            plain_content = " ".join(
                BeautifulSoup(content, features="lxml").find_all(string=True)
            )

            # NOTE: Profiling indicates Jinja templating takes about twice
            # the CPU time as adding items without compression. This appears to
            # be because of the navigation bar.
            page_content = self.page_template.render(  # type: ignore
                rel_prefix=rel_prefix,
                nav_sections=nav_sections,
                devdocs_metadata=doc_metadata,
                title=title,
                path=path,
                # Fill missing DevDocs content with indications that the issue
                # isn't with this generator.
                content=content,
            )
            creator.add_item_for(  # type: ignore
                path,
                title=title,
                content=page_content,  # type: ignore
                is_front=True,
                # Compression is needed because navigation is similar across pages.
                # Large documentation like Ansible may have ~6000 items in the
                # navigation bar.
                should_compress=True,
                mimetype="text/html",
                # Only index page content rather than navigation data.
                index_data=IndexData(
                    title=title,
                    content=plain_content,
                ),
            )

            # Tracking metadta
            counter += 1
            if counter % 100 == 0:
                logger.info(f"  Progress {counter} / {len(page_to_title)} pages")

        logger.info("  Finished adding contents.")
