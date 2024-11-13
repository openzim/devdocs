import logging
import pathlib

from zimscraperlib.logging import (  # pyright: ignore[reportMissingTypeStubs]
    getLogger,  # pyright: ignore[reportUnknownVariableType]
)

from devdocs2zim.__about__ import __version__

NAME = "devdocs2zim"
VERSION = __version__
ROOT_DIR = pathlib.Path(__file__).parent
DEFAULT_LOGO_PATH = ROOT_DIR.joinpath("third_party", "devdocs", "devdocs_48.png")

DEVDOCS_FRONTEND_URL = "https://devdocs.io"
DEVDOCS_DOCUMENTS_URL = "https://documents.devdocs.io"

# As of 2024-07-28 all documentation appears to be in English.
LANGUAGE_ISO_639_3 = "eng"

# File name for the licenses.txt template and output.
LICENSE_FILE = "licenses.txt"

# Implicit key of the landing page for each DevDocs document
DEVDOCS_LANDING_PAGE = "index"

logger = getLogger(NAME, level=logging.DEBUG)
