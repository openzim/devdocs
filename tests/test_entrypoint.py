import argparse

from devdocs2zim.entrypoint import zim_defaults
from devdocs2zim.generator import ZimConfig


def test_zim_defaults_validity():
    parser = argparse.ArgumentParser()
    ZimConfig.add_flags(parser, zim_defaults())

    # Assert parsing the defaults doesn't raise an error.
    ZimConfig.of(parser.parse_args([]))
