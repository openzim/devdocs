import json
from pathlib import Path
from typing import Any

import pytest
from zimscraperlib.zim import Archive

# Text the scraper writes in place of a page which is missing from DevDocs
MISSING_PAGE_TEXT = "This documentation is missing."


def test_is_file(zim_file_path: Path):
    """Ensure ZIM file exists"""
    assert zim_file_path.exists()
    assert zim_file_path.is_file()


def test_zim_main_page(zim_fh: Archive):
    """Ensure main page redirects to the landing page"""

    main_entry = zim_fh.main_entry
    assert main_entry.is_redirect
    assert main_entry.get_redirect_entry().path == "index"


def test_zim_metadata(zim_fh: Archive):
    """Ensure ZIM metadata are present and correct"""

    assert zim_fh.get_text_metadata("Name") == "tests_en_devdocs_git"
    assert zim_fh.get_text_metadata("Title") == "Git Test"
    assert zim_fh.get_text_metadata("Description") == "Test ZIM for Git"
    assert zim_fh.get_text_metadata("Language") == "eng"
    assert zim_fh.get_text_metadata("Publisher") == "openZIM"
    assert zim_fh.get_text_metadata("Creator") == "DevDocs"
    assert "devdocs2zim " in zim_fh.get_text_metadata("Scraper")


def test_zim_tags(zim_fh: Archive):
    """Ensure expected tags are present"""

    tags = zim_fh.get_text_metadata("Tags").split(";")
    for expected_tag in ["devdocs", "git"]:
        assert expected_tag in tags


def test_zim_illustration(zim_fh: Archive):
    """Ensure the 48x48 illustration is a PNG image"""

    illustration = zim_fh.get_metadata("Illustration_48x48@1")
    assert illustration.startswith(b"\x89PNG")


@pytest.mark.parametrize(
    "item_path,expected_mimetype",
    [
        pytest.param("index", "text/html", id="index"),
        pytest.param("git-add", "text/html", id="git-add"),
        pytest.param("git-commit", "text/html", id="git-commit"),
        pytest.param("gitglossary", "text/html", id="gitglossary"),
        pytest.param("navbar.json", "application/json", id="navbar.json"),
        pytest.param("licenses.txt", "text/plain", id="licenses.txt"),
        pytest.param("application.css", "text/css", id="application.css"),
    ],
)
def test_zim_content_expected_files(
    zim_fh: Archive, item_path: str, expected_mimetype: str
):
    """Ensure expected files are present with the right mimetype"""

    item = zim_fh.get_item(item_path)
    assert item.mimetype == expected_mimetype
    assert len(item.content) > 0


@pytest.mark.parametrize("item_path", ["assets/index.js", "assets/index.css"])
def test_zim_content_zimui_assets(zim_fh: Archive, item_path: str):
    """Ensure the ZIM UI assets are present"""

    assert len(zim_fh.get_item(item_path).content) > 0


def _navbar_hrefs(node: dict[str, Any]) -> list[str]:
    hrefs = [node["href"]] if "href" in node else []
    for child in node.get("children", []):
        hrefs.extend(_navbar_hrefs(child))
    return hrefs


def test_zim_navbar(zim_fh: Archive):
    """Ensure every page linked in the navbar is in the ZIM"""

    navbar = json.loads(zim_fh.get_content("navbar.json"))
    assert navbar["name"] == "Git"
    assert navbar["landingHref"] == "index"
    hrefs = _navbar_hrefs(navbar)
    assert hrefs
    for href in hrefs:
        assert zim_fh.has_entry_by_path(href.split("#")[0]), href


def test_zim_no_missing_page(zim_fh: Archive):
    """Ensure no page has been replaced by the missing page message"""

    checked_pages = 0
    for entry_id in range(zim_fh.entry_count):
        entry = zim_fh.get_entry_by_id(entry_id)
        if entry.is_redirect:
            continue
        item = entry.get_item()
        if item.mimetype != "text/html":
            continue
        assert MISSING_PAGE_TEXT not in bytes(item.content).decode(), entry.path
        checked_pages += 1
    # Make sure the test did not pass without checking any page
    assert checked_pages > 0


def test_zim_search(zim_fh: Archive):
    """Ensure full-text search and title suggestions are working"""

    assert zim_fh.has_fulltext_index
    assert zim_fh.has_title_index
    assert "git-commit" in zim_fh.get_search_results("commit", 0, 10)
    assert "git-commit" in zim_fh.get_suggestions("git com", 0, 10)
