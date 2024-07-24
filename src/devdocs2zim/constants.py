import logging

from zimscraperlib.logging import (  # pyright: ignore[reportMissingTypeStubs]
    getLogger,  # pyright: ignore[reportUnknownVariableType]
)

from devdocs2zim.__about__ import __version__

NAME = "devdocs2zim"
VERSION = __version__

DEVDOCS_FRONTEND_URL = "https://devdocs.io"
DEVDOCS_DOCUMENTS_URL = "https://documents.devdocs.io"

logger = getLogger(NAME, level=logging.DEBUG)
