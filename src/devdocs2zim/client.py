import datetime
import re
from collections import defaultdict
from collections.abc import Callable
from enum import Enum
from functools import cached_property

import requests
from pydantic import BaseModel, TypeAdapter, computed_field

from devdocs2zim.constants import logger

HTTP_TIMEOUT_SECONDS = 15

# These regular expressions are extracted from the DevDocs frontend.
# The expression definitions haven't changed in ~8 years as of 2024-07-28:
# https://github.com/freeCodeCamp/devdocs/blob/e28f81d3218bdbad7eac0540c58c11c7fe1d33d3/assets/javascripts/collections/types.js#L3
BEFORE_CONTENT_PATTERN = re.compile(
    r"(^|\()(guides?|tutorials?|reference|book|getting\ started|manual|examples)($|[\):])",  # noqa: E501
    re.IGNORECASE,
)
AFTER_CONTENT_PATTERN = re.compile(r"appendix", re.IGNORECASE)


class DevdocsMetadataLinks(BaseModel):
    """Project links for a specific documentation set."""

    # Home page for the project.
    home: str = ""
    # Link to the project's source code.
    code: str = ""


class DevdocsMetadata(BaseModel):
    """Metadata about a documentation set."""

    # Human readable name for the documentation.
    name: str
    # Directory name devdocs puts the docs under. Takes the format:
    # name[~version] e.g. "python" or "python-3.10".
    slug: str
    # Links to project resources.
    links: DevdocsMetadataLinks | None = None
    # Shortened version displayed in devdocs, if any. Second part of the slug.
    version: str = ""
    # Specific release of the software the documentation is for, if any.
    release: str = ""
    # License and attribution information, if any.
    attribution: str = ""

    @property
    def slug_without_version(self):
        return self.slug.split("~")[0]

    def placeholders(
        self, clock: Callable[[], datetime.date] = datetime.date.today
    ) -> dict[str, str]:
        """Gets placeholders for filenames.

        Arguments:
          clock: Override the default clock to use for producing the "period".
        """
        home_link = ""
        code_link = ""
        if self.links is not None:
            home_link = self.links.home
            code_link = self.links.code

        full_name = self.name
        if self.version:
            full_name += f" {self.version}"

        # properties are inspired by what devdocs uses for their frontend:
        # https://github.com/freeCodeCamp/devdocs/blob/6caa5eb1b18ab8d34034f319024bd81877035b36/lib/app.rb#L110
        return {
            "name": self.name,
            "full_name": full_name,
            "slug": self.slug,
            "clean_slug": re.sub(r"[^.a-zA-Z0-9]", "-", self.slug),
            "version": self.version,
            "release": self.release,
            "attribution": self.attribution,
            "home_link": home_link,
            "code_link": code_link,
            "slug_without_version": self.slug_without_version,
            "period": clock().strftime("%Y-%m"),
        }


class DevdocsIndexEntry(BaseModel):
    """A link to a document in the sidebar."""

    # Display name for the entry.
    name: str

    # Path to the entry in the db.json file. This may contain a fragment identifier
    # linking to an anchor tag e.g. #fragment that would not exist in the db.json file.
    path: str

    # Name of the type (section) the entry is located under.
    # If None, the entry is not displayed.
    type: str | None

    @property
    def path_without_fragment(self) -> str:
        """Key in db.json for the file's contents."""
        return self.path.split("#")[0]


class SortPrecedence(Enum):
    """Represents where to place section in the navbar."""

    # NOTE: Definition order must match display order.

    BEFORE_CONTENT = 0
    CONTENT = 1
    AFTER_CONTENT = 2


class DevdocsIndexType(BaseModel):
    """A section header for documentation."""

    # Display name for the section.
    name: str

    # Number of documents in the section.
    count: int

    # Section slug. This appears to be unused.
    slug: str

    def sort_precedence(self) -> SortPrecedence:
        """Determines where this section should be displayed in the navigation."""
        if BEFORE_CONTENT_PATTERN.match(self.name):
            return SortPrecedence.BEFORE_CONTENT

        if AFTER_CONTENT_PATTERN.match(self.name):
            return SortPrecedence.AFTER_CONTENT

        return SortPrecedence.CONTENT


class NavigationSection(BaseModel):
    """Represents a single section of a devdocs navigation tree."""

    # Heading information for the group of links.
    name: str
    # Links to display in the section.
    links: list[DevdocsIndexEntry]

    @computed_field
    @property
    def count(self) -> int:
        """Number of links in the section."""
        return len(self.links)

    @cached_property
    def _contained_pages(self) -> set[str]:
        return {link.path_without_fragment for link in self.links}

    def opens_for_page(self, page_path: str) -> bool:
        """Returns whether this section should be rendered open for the given page."""

        # Some docs like Lua or CoffeeScript have all of their content in the index.
        # Others like RequireJS are split between index and additional pages.
        # We don't want sections opening when the user navigates to the index.
        if page_path == "index":
            return False

        return page_path in self._contained_pages


class DevdocsIndex(BaseModel):
    """Represents entries in the /<slug>/index.json file for each resource."""

    # List of entries.
    entries: list[DevdocsIndexEntry]

    # List of "types" or section headings.
    # These are displayed in the order they're found grouped by sort_precedence.
    types: list[DevdocsIndexType]

    def build_navigation(self) -> list[NavigationSection]:
        """Builds a navigation hierarchy that's soreted correctly for rendering."""

        sections_by_precedence: dict[SortPrecedence, list[DevdocsIndexType]] = (
            defaultdict(list)
        )
        for section in self.types:
            sections_by_precedence[section.sort_precedence()].append(section)

        links_by_section_name: dict[str, list[DevdocsIndexEntry]] = defaultdict(list)
        for entry in self.entries:
            if entry.type is None:
                continue
            links_by_section_name[entry.type].append(entry)

        output: list[NavigationSection] = []
        for precedence in SortPrecedence:
            for section in sections_by_precedence[precedence]:
                output.append(
                    NavigationSection(
                        name=section.name,
                        links=links_by_section_name[section.name],
                    )
                )

        return output


class DevdocsClient:
    """Utility functions to read data from devdocs."""

    def __init__(self, documents_url: str, frontend_url: str) -> None:
        """Initializes DevdocsClient.

        Paremters:
            documents_url: Scheme, hostname, and port for the Devdocs documents server
                e.g. `https://documents.devdocs.io`.
            frontend_url: Scheme, hostname, and port for the Devdocs frontend server
                e.g. `https://devdocs.io`.
        """
        self.documents_url = documents_url
        self.frontend_url = frontend_url

    def _get_text(self, url: str) -> str:
        """Perform a GET request and return the response as decoded text."""

        logger.debug(f"Fetching {url}")

        resp = requests.get(
            url=url,
            allow_redirects=True,
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()

        return resp.text

    def read_frontend_file(self, file_path: str) -> str:
        """Read a file from the devdocs frontend server.

        Parameters:
          file_path: Path of the file relative to the root.
        """
        return self._get_text(f"{self.frontend_url}/{file_path}")

    def read_application_css(self) -> str:
        """Read the app's CSS which includes classes for normalizing content."""

        return self.read_frontend_file("application.css")

    def list_docs(self) -> list[DevdocsMetadata]:
        """List the documents devdocs currently has published."""

        # NOTE: There is also a backend file named docs.json, but it
        # is missing attribution information.
        file_contents = self.read_frontend_file("docs.json")

        return TypeAdapter(list[DevdocsMetadata]).validate_json(file_contents)

    def read_doc_file(self, doc_slug: str, file_name: str) -> str:
        """Read a file from the devdocs documents server.

        Parameters:
          doc_slug: The document's slug e.g. language~v123.
          file_name: Name of the file under the slug e.g. index.json.
        """

        # As of 2024-07-17 the largest file is scala~2.12_library/db.json at 144M.
        # Tested by building the devdocs container image.
        #
        # This amount should fit in memory fine, but we need to be careful not to
        # cache these large vaules in memory.
        return self._get_text(f"{self.documents_url}/{doc_slug}/{file_name}")

    def get_index(self, doc_slug: str) -> DevdocsIndex:
        """Fetch the set of headings and entries that make up the navigation sidebar."""

        file_contents = self.read_doc_file(doc_slug, "index.json")

        return DevdocsIndex.model_validate_json(file_contents)

    def get_meta(self, doc_slug: str) -> DevdocsMetadata:
        """Fetch metadata about the given document.

        Prefer using list_docs and filtering if possible because
        the metadata returned there is more complete.
        """
        file_contents = self.read_doc_file(doc_slug, "meta.json")

        return DevdocsMetadata.model_validate_json(file_contents)

    def get_db(self, doc_slug: str) -> dict[str, str]:
        """Fetch the contents of the pages in the index."""
        file_contents = self.read_doc_file(doc_slug, "db.json")

        return TypeAdapter(dict[str, str]).validate_json(file_contents)
