import logging
import pathlib

from zimscraperlib.logging import (  # pyright: ignore[reportMissingTypeStubs]
    getLogger,  # pyright: ignore[reportUnknownVariableType]
)

from devdocs2zim.__about__ import __version__

NAME = "devdocs2zim"
VERSION = __version__
ROOT_DIR = pathlib.Path(__file__).parent

DEVDOCS_FRONTEND_URL = "https://devdocs.io"
DEVDOCS_DOCUMENTS_URL = "https://documents.devdocs.io"

# As of 2024-07-28 all documentation appears to be in English.
LANGUAGE_ISO_639_3 = "eng"

logger = getLogger(NAME, level=logging.DEBUG)
