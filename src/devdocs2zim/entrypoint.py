import argparse
import logging

from devdocs2zim.client import DevdocsClient
from devdocs2zim.constants import (
    DEVDOCS_DOCUMENTS_URL,
    DEVDOCS_FRONTEND_URL,
    NAME,
    VERSION,
    logger,
)
from devdocs2zim.generator import DocFilter, Generator, ZimConfig


def main() -> None:
    parser = argparse.ArgumentParser(
        prog=NAME,
    )

    parser.add_argument(
        "--debug", help="Enable verbose output", action="store_true", default=False
    )

    parser.add_argument(
        "--version",
        help="Display scraper version and exit",
        action="version",
        version=VERSION,
    )

    parser.add_argument(
        "--output",
        help="Output folder for ZIMs. Default: /output",
        default="/output",
        dest="output_folder",
    )

    # ZIM configuration flags
    ZimConfig.add_flags(
        parser,
        ZimConfig(
            name_format="devdocs_{slug_without_version}_{version}",
            creator="DevDocs",
            publisher="openZIM",
            title_format="{full_name} Docs",
            description_format="{full_name} docs by DevDocs",
            long_description_format=None,
            tags="devdocs;{slug_without_version}",
        ),
    )

    # Document selection flags
    DocFilter.add_flags(parser)

    # Client configuration flags
    parser.add_argument(
        "--devdocs-frontend-url",
        help="Scheme and hostname for the devdocs frontend.",
        default=DEVDOCS_FRONTEND_URL,
    )

    parser.add_argument(
        "--devdocs-documents-url",
        help="Scheme and hostname for the devdocs documents server.",
        default=DEVDOCS_DOCUMENTS_URL,
    )

    args = parser.parse_args()

    logger.setLevel(level=logging.DEBUG if args.debug else logging.INFO)

    try:
        zim_config = ZimConfig.of(args)
        doc_filter = DocFilter.of(args)
        devdocs_client = DevdocsClient(
            documents_url=args.devdocs_documents_url,
            frontend_url=args.devdocs_frontend_url,
        )

        Generator(
            devdocs_client=devdocs_client,
            zim_config=zim_config,
            output_folder=args.output_folder,
            doc_filter=doc_filter,
        ).run()
    except Exception as e:
        logger.exception(e)
        logger.error(f"Generation failed with the following error: {e}")
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()