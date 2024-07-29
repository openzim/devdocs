import argparse
import os
import re
from collections import defaultdict

from pydantic import BaseModel
from zimscraperlib.constants import (  # pyright: ignore[reportMissingTypeStubs]
    MAXIMUM_DESCRIPTION_METADATA_LENGTH,
    MAXIMUM_LONG_DESCRIPTION_METADATA_LENGTH,
    RECOMMENDED_MAX_TITLE_LENGTH,
)

from devdocs2zim.client import (
    DevdocsClient,
    DevdocsMetadata,
)
from devdocs2zim.constants import logger


class InvalidFormatError(Exception):
    """Raised when a user supplied template has an invalid parameter."""

    pass


class ZimConfig(BaseModel):
    """Common configuration for building ZIM files."""

    # File name/name for the ZIM.
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

    def run(self) -> None:
        """Run the generator to fetch content and produce ZIMs."""

        # Load docs first to fail fast before fetching additional resources.
        all_docs = self.devdocs_client.list_docs()
        selected_doc_metadata = self.doc_filter.filter(all_docs)

        # List all docs and copy one by one
        for doc_metadata in selected_doc_metadata:
            logger.info(f"Fetching {doc_metadata.slug}")

        raise NotImplementedError("ZIM creation is not yet implemented")
