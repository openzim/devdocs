import argparse
from unittest import TestCase

from devdocs2zim.client import DevdocsMetadata
from devdocs2zim.generator import (
    DocFilter,
    InvalidFormatError,
    MissingDocumentError,
    ZimConfig,
)


class TestZimConfig(TestCase):
    def defaults(self) -> ZimConfig:
        return ZimConfig(
            name_format="default_name_format",
            title_format="default_title_format",
            publisher="default_publisher",
            creator="default_creator",
            description_format="default_description_format",
            long_description_format="default_long_description_format",
            tags="default_tag1;default_tag2",
        )

    def test_flag_parsing_defaults(self):
        defaults = self.defaults()
        parser = argparse.ArgumentParser()
        ZimConfig.add_flags(parser, defaults)

        got = ZimConfig.of(parser.parse_args(args=[]))

        self.assertEqual(defaults, got)

    def test_flag_parsing_overrides(self):
        parser = argparse.ArgumentParser()
        ZimConfig.add_flags(parser, self.defaults())

        got = ZimConfig.of(
            parser.parse_args(
                args=[
                    "--creator",
                    "creator",
                    "--publisher",
                    "publisher",
                    "--name-format",
                    "name-format",
                    "--title-format",
                    "title-format",
                    "--description-format",
                    "description-format",
                    "--long-description-format",
                    "long-description-format",
                    "--tags",
                    "tag1;tag2",
                ]
            )
        )

        self.assertEqual(
            ZimConfig(
                creator="creator",
                publisher="publisher",
                name_format="name-format",
                title_format="title-format",
                description_format="description-format",
                long_description_format="long-description-format",
                tags="tag1;tag2",
            ),
            got,
        )

    def test_format_none_needed(self):
        defaults = self.defaults()

        formatted = defaults.format({})

        self.assertEqual(defaults, formatted)

    def test_format_only_allowed(self):
        to_format = ZimConfig(
            name_format="{replace_me}",
            title_format="{replace_me}",
            publisher="{replace_me}",
            creator="{replace_me}",
            description_format="{replace_me}",
            long_description_format="{replace_me}",
            tags="{replace_me}",
        )

        got = to_format.format({"replace_me": "replaced"})

        self.assertEqual(
            ZimConfig(
                name_format="replaced",
                title_format="replaced",
                publisher="{replace_me}",
                creator="{replace_me}",
                description_format="replaced",
                long_description_format="replaced",
                tags="replaced",
            ),
            got,
        )

    def test_format_long_title_fails(self):
        to_format = self.defaults()
        to_format.title_format = "a" * 10000

        self.assertRaises(ValueError, to_format.format, {})

    def test_format_long_description_fails(self):
        to_format = self.defaults()
        to_format.description_format = "a" * 10000

        self.assertRaises(ValueError, to_format.format, {})

    def test_format_long_long_description_fails(self):
        to_format = self.defaults()
        to_format.long_description_format = "a" * 10000

        self.assertRaises(ValueError, to_format.format, {})

    def test_format_invalid(self):
        to_format = self.defaults()
        to_format.name_format = "{invalid_placeholder}"

        self.assertRaises(
            InvalidFormatError, to_format.format, {"valid1": "", "valid2": ""}
        )


class TestDocFilter(TestCase):
    def test_flags_all(self):
        parser = argparse.ArgumentParser()
        DocFilter.add_flags(parser)

        got = DocFilter.of(parser.parse_args(args=["--all"]))

        self.assertEqual(
            DocFilter(
                all=True,
                first=None,
                slugs=None,
                skip_slug_regex=None,
            ),
            got,
        )

    def test_flags_slug(self):
        parser = argparse.ArgumentParser()
        DocFilter.add_flags(parser)

        got = DocFilter.of(
            parser.parse_args(args=["--slug", "first", "--slug", "second"])
        )

        self.assertEqual(
            DocFilter(
                all=False,
                first=None,
                slugs=["first", "second"],
                skip_slug_regex=None,
            ),
            got,
        )

    def test_flags_first(self):
        parser = argparse.ArgumentParser()
        DocFilter.add_flags(parser)

        got = DocFilter.of(parser.parse_args(args=["--first", "3"]))

        self.assertEqual(
            DocFilter(
                all=False,
                first=3,
                slugs=None,
                skip_slug_regex=None,
            ),
            got,
        )

    def test_flags_missing_selector(self):
        parser = argparse.ArgumentParser(exit_on_error=False)
        DocFilter.add_flags(parser)

        self.assertRaises(SystemExit, parser.parse_args, args=[])

    def test_flags_regex(self):
        parser = argparse.ArgumentParser()
        DocFilter.add_flags(parser)

        got = DocFilter.of(parser.parse_args(args=["--all", "--skip-slug-regex", "^$"]))

        self.assertEqual(
            DocFilter(
                all=True,
                first=None,
                slugs=None,
                skip_slug_regex="^$",
            ),
            got,
        )

    def test_filter_all(self):
        doc_filter = DocFilter(all=True, first=None, slugs=None, skip_slug_regex=None)

        got = doc_filter.filter(
            [
                DevdocsMetadata(name="foo", slug="foo"),
                DevdocsMetadata(name="bar", slug="bar"),
                DevdocsMetadata(name="bazz", slug="bazz"),
            ]
        )

        self.assertEqual(3, len(got))

    def test_filter_slugs(self):
        doc_filter = DocFilter(
            all=False, first=None, slugs=["foo", "bazz"], skip_slug_regex=None
        )

        got = doc_filter.filter(
            [
                DevdocsMetadata(name="foo", slug="foo"),
                DevdocsMetadata(name="bar", slug="bar"),
                DevdocsMetadata(name="bazz", slug="bazz"),
            ]
        )

        self.assertEqual(2, len(got))

    def test_filter_all_regex(self):
        doc_filter = DocFilter(all=True, first=None, slugs=None, skip_slug_regex="^b")

        got = doc_filter.filter(
            [
                DevdocsMetadata(name="foo", slug="foo"),
                DevdocsMetadata(name="bar", slug="bar"),
                DevdocsMetadata(name="bazz", slug="bazz"),
            ]
        )

        self.assertEqual(1, len(got))

    def test_filter_slugs_missing(self):
        doc_filter = DocFilter(
            all=False, first=None, slugs=["does_not_exist"], skip_slug_regex=None
        )

        self.assertRaises(MissingDocumentError, doc_filter.filter, [])

    def test_filter_first(self):
        doc_filter = DocFilter(all=False, first=2, slugs=None, skip_slug_regex=None)

        got = doc_filter.filter(
            [
                DevdocsMetadata(name="foo 1", slug="foo~1"),
                DevdocsMetadata(name="foo 2", slug="foo~2"),
                DevdocsMetadata(name="foo 3", slug="foo~3"),
                DevdocsMetadata(name="bar 1", slug="bar~1"),
                DevdocsMetadata(name="bar 2", slug="bar~2"),
                DevdocsMetadata(name="bazz", slug="bazz"),
            ]
        )

        self.assertEqual(
            [
                DevdocsMetadata(name="foo 1", slug="foo~1"),
                DevdocsMetadata(name="foo 2", slug="foo~2"),
                DevdocsMetadata(name="bar 1", slug="bar~1"),
                DevdocsMetadata(name="bar 2", slug="bar~2"),
                DevdocsMetadata(name="bazz", slug="bazz"),
            ],
            got,
        )
