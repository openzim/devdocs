import argparse
import io
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import create_autospec

from PIL.Image import open as pilopen

from devdocs2zim.client import (
    DevdocsClient,
    DevdocsIndex,
    DevdocsIndexEntry,
    DevdocsIndexType,
    DevdocsMetadata,
)
from devdocs2zim.entrypoint import zim_defaults
from devdocs2zim.generator import (
    DocFilter,
    Generator,
    InvalidFormatError,
    MissingDocumentError,
    ZimConfig,
)


class TestZimConfig(TestCase):
    def defaults(self) -> ZimConfig:
        return ZimConfig(
            file_name_format="default_file_name_format",
            name_format="default_name_format",
            title_format="default_title_format",
            publisher="default_publisher",
            creator="default_creator",
            description_format="default_description_format",
            long_description_format="default_long_description_format",
            tags="default_tag1;default_tag2",
            logo_format="default_logo_format",
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
                    "--file-name-format",
                    "file-name-format",
                    "--title-format",
                    "title-format",
                    "--description-format",
                    "description-format",
                    "--long-description-format",
                    "long-description-format",
                    "--tags",
                    "tag1;tag2",
                    "--logo-format",
                    "logo-format",
                ]
            )
        )

        self.assertEqual(
            ZimConfig(
                creator="creator",
                publisher="publisher",
                name_format="name-format",
                file_name_format="file-name-format",
                title_format="title-format",
                description_format="description-format",
                long_description_format="long-description-format",
                tags="tag1;tag2",
                logo_format="logo-format",
            ),
            got,
        )

    def test_format_none_needed(self):
        defaults = self.defaults()

        formatted = defaults.format({})

        self.assertEqual(defaults, formatted)

    def test_format_only_allowed(self):
        to_format = ZimConfig(
            file_name_format="{replace_me}",
            name_format="{replace_me}",
            title_format="{replace_me}",
            publisher="{replace_me}",
            creator="{replace_me}",
            description_format="{replace_me}",
            long_description_format="{replace_me}",
            tags="{replace_me}",
            logo_format="{replace_me}",
        )

        got = to_format.format({"replace_me": "replaced"})

        self.assertEqual(
            ZimConfig(
                file_name_format="replaced",
                name_format="replaced",
                title_format="replaced",
                publisher="{replace_me}",
                creator="{replace_me}",
                description_format="replaced",
                long_description_format="replaced",
                tags="replaced",
                logo_format="replaced",
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
                csv_slugs=None,
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
                csv_slugs=["first", "second"],
                skip_slug_regex=None,
            ),
            got,
        )
        self.assertEqual(
            ["first", "second"],
            got.slugs,
        )

    def test_flags_slug_csv(self):
        parser = argparse.ArgumentParser()
        DocFilter.add_flags(parser)

        got = DocFilter.of(parser.parse_args(args=["--slug", "first,second"]))

        self.assertEqual(
            DocFilter(
                all=False,
                first=None,
                csv_slugs=["first,second"],
                skip_slug_regex=None,
            ),
            got,
        )
        self.assertEqual(
            ["first", "second"],
            got.slugs,
        )

    def test_flags_first(self):
        parser = argparse.ArgumentParser()
        DocFilter.add_flags(parser)

        got = DocFilter.of(parser.parse_args(args=["--first", "3"]))

        self.assertEqual(
            DocFilter(
                all=False,
                first=3,
                csv_slugs=None,
                skip_slug_regex=None,
            ),
            got,
        )

    def test_flags_missing_selector(self):
        parser = argparse.ArgumentParser(exit_on_error=False)
        DocFilter.add_flags(parser)

        self.assertRaises(argparse.ArgumentError, parser.parse_args, args=[])

    def test_flags_regex(self):
        parser = argparse.ArgumentParser()
        DocFilter.add_flags(parser)

        got = DocFilter.of(parser.parse_args(args=["--all", "--skip-slug-regex", "^$"]))

        self.assertEqual(
            DocFilter(
                all=True,
                first=None,
                csv_slugs=None,
                skip_slug_regex="^$",
            ),
            got,
        )

    def test_filter_all(self):
        doc_filter = DocFilter(
            all=True, first=None, csv_slugs=None, skip_slug_regex=None
        )

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
            all=False, first=None, csv_slugs=["foo", "bazz"], skip_slug_regex=None
        )

        got = doc_filter.filter(
            [
                DevdocsMetadata(name="foo", slug="foo"),
                DevdocsMetadata(name="bar", slug="bar"),
                DevdocsMetadata(name="bazz", slug="bazz"),
            ]
        )

        self.assertEqual(2, len(got))

    def test_filter_slugs_csvs(self):
        doc_filter = DocFilter(
            all=False, first=None, csv_slugs=["foo,bazz"], skip_slug_regex=None
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
        doc_filter = DocFilter(
            all=True, first=None, csv_slugs=None, skip_slug_regex="^b"
        )

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
            all=False, first=None, csv_slugs=["does_not_exist"], skip_slug_regex=None
        )

        self.assertRaises(MissingDocumentError, doc_filter.filter, [])

    def test_filter_first(self):
        doc_filter = DocFilter(all=False, first=2, csv_slugs=None, skip_slug_regex=None)

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


class TestGenerator(TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        output_folder = self.temp_dir.__enter__()

        self.mock_client = create_autospec(DevdocsClient)

        self.generator = Generator(
            devdocs_client=self.mock_client,
            doc_filter=DocFilter(
                all=True, first=None, csv_slugs=None, skip_slug_regex=None
            ),
            output_folder=output_folder,
            zim_config=zim_defaults(),
            zimui_dist=str(Path(__file__).parent / "testdata" / "zimui"),
        )

    def tearDown(self):
        self.temp_dir.__exit__(None, None, None)

    def test_asset_path_missing(self):
        self.assertRaises(ValueError, Generator.asset_path, "does_not_exist")

    def test_asset_path_exists(self):
        got = Generator.asset_path("README.md")

        self.assertTrue(got.exists())

    def test_load_common_files(self):
        got = self.generator.load_common_files()

        # Check names because they're referenced in templates
        self.assertEqual(
            {"licenses.txt", "application.css", "assets/index.css", "assets/index.js"},
            {f.path for f in got},  # type: ignore
        )

    def test_run_no_documents(self):
        got = self.generator.run()

        self.assertEqual([], got)

    def test_run_e2e(self):
        self.mock_client.read_application_css.return_value = ".mock_css {}"
        self.mock_client.list_docs.return_value = [
            DevdocsMetadata(name="MockDoc", slug="mockdoc")
        ]
        self.mock_client.get_index.return_value = DevdocsIndex(
            entries=[
                DevdocsIndexEntry(
                    name="Mock Entry", path="mock-entry", type="Mock Header"
                ),
                DevdocsIndexEntry(
                    name="Missing Entry", path="missing", type="Mock Header"
                ),
            ],
            types=[
                DevdocsIndexType(name="Mock Header", count=1, slug="headers"),
            ],
        )
        self.mock_client.get_db.return_value = {
            "mock-entry": "Entry Value",
            "index": "Index Value",
        }

        got = self.generator.run()

        self.assertEqual(1, len(got))

    def test_page_titles_no_fragment(self):
        pages = [
            DevdocsIndexEntry(name="Mock Sub1", path="mock#subheading1", type=None),
            DevdocsIndexEntry(name="Mock Top", path="mock", type=None),
            DevdocsIndexEntry(name="Mock Sub2", path="mock#subheading2", type=None),
        ]

        got = Generator.page_titles(pages)

        self.assertEqual({"mock": "Mock Top"}, got)

    def test_page_titles_only_fragment(self):
        pages = [
            DevdocsIndexEntry(name="Mock Sub1", path="mock#subheading1", type=None),
            DevdocsIndexEntry(name="Mock Sub2", path="mock#subheading2", type=None),
        ]

        got = Generator.page_titles(pages)

        # First fragment wins if no page points to the top
        self.assertEqual({"mock": "Mock Sub1"}, got)

    def test_fetch_logo_bytes_jpeg(self):
        jpg_path = str(Path(__file__).parent / "testdata" / "test.jpg")

        got = Generator.fetch_logo_bytes(jpg_path)

        self.assertIsNotNone(got)
        with pilopen(io.BytesIO(got)) as image:
            self.assertEqual((48, 48), image.size)
            self.assertEqual("PNG", image.format)

    def test_fetch_logo_bytes_png(self):
        png_path = str(Path(__file__).parent / "testdata" / "test.png")

        got = Generator.fetch_logo_bytes(png_path)

        self.assertIsNotNone(got)
        with pilopen(io.BytesIO(got)) as image:
            self.assertEqual((48, 48), image.size)
            self.assertEqual("PNG", image.format)

    def test_fetch_logo_bytes_svg(self):
        png_path = str(Path(__file__).parent / "testdata" / "test.svg")

        got = Generator.fetch_logo_bytes(png_path)

        self.assertIsNotNone(got)
        with pilopen(io.BytesIO(got)) as image:
            self.assertEqual((48, 48), image.size)
            self.assertEqual("PNG", image.format)

    def test_fetch_logo_bytes_does_not_exist_fails(self):
        self.assertRaises(OSError, Generator.fetch_logo_bytes, "does_not_exist")

    def test_fetch_logo_bytes_returns_none_fails(self):
        self.assertRaises(Exception, Generator.fetch_logo_bytes, "")
