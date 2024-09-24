import datetime
from unittest import TestCase
from unittest.mock import ANY, create_autospec, patch

from pydantic import TypeAdapter
from requests import HTTPError, Response

from devdocs2zim.client import (
    DevdocsClient,
    DevdocsIndex,
    DevdocsIndexEntry,
    DevdocsIndexType,
    DevdocsMetadata,
    DevdocsMetadataLinks,
    NavigationSection,
    SortPrecedence,
)

# NOTE: Deserializataion tests in this file are performed against the full object
# to ensure additions of new fields will cause all relevant tests to fail.


class TestDevdocsMetadataLinks(TestCase):
    def test_unmarshal_minimal(self):
        links = DevdocsMetadataLinks.model_validate_json(r"{}")

        self.assertEqual(
            DevdocsMetadataLinks(
                home="",
                code="",
            ),
            links,
        )

    def test_unmarshal_full(self):
        links = DevdocsMetadataLinks.model_validate_json(
            r'{"code":"https://code.code", "home":"https://home.home"}'
        )

        self.assertEqual(
            DevdocsMetadataLinks(
                home="https://home.home",
                code="https://code.code",
            ),
            links,
        )


class TestDevdocsMetadata(TestCase):
    def test_unmarshal_minimal(self):
        metadata = DevdocsMetadata.model_validate_json(
            r"""
            {
                "name": "MyLanguage",
                "slug": "mylanguage~3.14"
            }
            """
        )

        self.assertEqual(
            DevdocsMetadata(name="MyLanguage", slug="mylanguage~3.14"),
            metadata,
        )

    def test_unmarshal_full(self):
        # Example fetched from https://devdocs.io/docs.json on 2024-07-17.
        # Attribution line modified for brevity.
        metadata = DevdocsMetadata.model_validate_json(
            r"""
            {
                "name": "Kubernetes",
                "slug": "kubernetes~1.28",
                "type": "kubernetes",
                "links": {
                "home": "https://kubernetes.io/",
                "code": "https://github.com/kubernetes/kubernetes"
                },
                "version": "1.28",
                "release": "1.28",
                "mtime": 1707071525,
                "db_size": 951091,
                "attribution": "&copy; 2022 The Kubernetes Authors"
            }
            """
        )

        self.assertEqual(
            DevdocsMetadata(
                name="Kubernetes",
                slug="kubernetes~1.28",
                links=DevdocsMetadataLinks(
                    home="https://kubernetes.io/",
                    code="https://github.com/kubernetes/kubernetes",
                ),
                release="1.28",
                version="1.28",
                attribution="&copy; 2022 The Kubernetes Authors",
            ),
            metadata,
        )

    def test_slug_without_version_no_version(self):
        metadata = DevdocsMetadata(name="test", slug="test")

        self.assertEqual("test", metadata.slug_without_version)

    def test_slug_without_version_version(self):
        metadata = DevdocsMetadata(name="test", slug="test~1.23")

        self.assertEqual("test", metadata.slug_without_version)

    def test_placeholders_minimal(self):
        metadata = DevdocsMetadata(name="test", slug="test~1.23")

        placeholders = metadata.placeholders(clock=lambda: datetime.date(2001, 2, 3))

        self.assertEqual(
            {
                "name": "test",
                "full_name": "test",
                "slug": "test~1.23",
                "clean_slug": "test-1.23",
                "version": "",
                "release": "",
                "attribution": "",
                "home_link": "",
                "code_link": "",
                "slug_without_version": "test",
                "period": "2001-02",
            },
            placeholders,
        )

    def test_placeholders_full(self):
        metadata = DevdocsMetadata(
            name="Kubernetes",
            slug="kubernetes~1.28",
            links=DevdocsMetadataLinks(
                home="https://kubernetes.io/",
                code="https://github.com/kubernetes/kubernetes",
            ),
            release="1.28",
            version="1.28.1",
            attribution="&copy; 2022 The Kubernetes Authors",
        )

        placeholders = metadata.placeholders(clock=lambda: datetime.date(2001, 2, 3))

        self.assertEqual(
            {
                "name": "Kubernetes",
                "full_name": "Kubernetes 1.28.1",
                "slug": "kubernetes~1.28",
                "clean_slug": "kubernetes-1.28",
                "version": "1.28.1",
                "release": "1.28",
                "attribution": "&copy; 2022 The Kubernetes Authors",
                "home_link": "https://kubernetes.io/",
                "code_link": "https://github.com/kubernetes/kubernetes",
                "slug_without_version": "kubernetes",
                "period": "2001-02",
            },
            placeholders,
        )


class TestDevdocsIndexEntry(TestCase):
    def test_unmarshal(self):
        entry = DevdocsIndexEntry.model_validate_json(
            r"""
               {
                "name": "Accept-Encoding",
                "path": "headers/accept-encoding",
                "type": "Headers"
                }
            """
        )

        self.assertEqual(
            DevdocsIndexEntry(
                name="Accept-Encoding",
                path="headers/accept-encoding",
                type="Headers",
            ),
            entry,
        )

    def test_path_without_fragment_no_fragment(self):
        entry = DevdocsIndexEntry(
            name="Test",
            path="test",
            type="TestCategory",
        )

        self.assertEqual(
            "test",
            entry.path_without_fragment,
        )

    def test_path_without_fragment_has_fragment(self):
        entry = DevdocsIndexEntry(
            name="Test",
            path="test#some-fragment",
            type="TestCategory",
        )

        self.assertEqual(
            "test",
            entry.path_without_fragment,
        )


class TestDevdocsIndexType(TestCase):
    def test_unmarshal(self):
        index_type = DevdocsIndexType.model_validate_json(
            r"""
                {
                "name": "Headers",
                "count": 145,
                "slug": "headers"
                }
            """
        )

        self.assertEqual(
            DevdocsIndexType(
                name="Headers",
                count=145,
                slug="headers",
            ),
            index_type,
        )

    def test_sort_precedence_default(self):
        index_type = DevdocsIndexType(
            name="ZIM Readers",
            count=0,
            slug="",
        )

        got = index_type.sort_precedence()

        self.assertEqual(SortPrecedence.CONTENT, got)

    def test_sort_precedence_before(self):
        index_type = DevdocsIndexType(
            name="(Tutorial) Creating a ZIM",
            count=0,
            slug="",
        )

        got = index_type.sort_precedence()

        self.assertEqual(SortPrecedence.BEFORE_CONTENT, got)

    def test_sort_precedence_after(self):
        index_type = DevdocsIndexType(
            name="Appendix A: List of ZIMs",
            count=0,
            slug="",
        )

        got = index_type.sort_precedence()

        self.assertEqual(SortPrecedence.AFTER_CONTENT, got)


class TestNavigationSection(TestCase):
    def test_count_empty(self):
        section = NavigationSection(name="", links=[])

        got = section.count

        self.assertEqual(0, got)

    def test_count_non_empty(self):
        section = NavigationSection(
            name="",
            links=[
                DevdocsIndexEntry(name="Foo 1", path="foo#1", type=None),
            ],
        )

        got = section.count

        self.assertEqual(1, got)

    def test_opens_for_page(self):
        section = NavigationSection(
            name="",
            links=[
                DevdocsIndexEntry(name="Foo 1", path="foo#1", type=None),
                DevdocsIndexEntry(name="Foo 2", path="foo#2", type=None),
                DevdocsIndexEntry(name="Bar", path="bar", type=None),
            ],
        )

        self.assertTrue(section.opens_for_page("foo"))
        self.assertTrue(section.opens_for_page("bar"))
        self.assertFalse(section.opens_for_page("bazz"))

    def test_opens_for_page_index(self):
        section = NavigationSection(
            name="",
            links=[
                DevdocsIndexEntry(name="Index", path="index", type=None),
            ],
        )

        # Links to the index are special cases and shouldn't open.
        self.assertFalse(section.opens_for_page("index"))


class TestDevdocsIndex(TestCase):
    def test_unmarshal_minimal(self):
        index = DevdocsIndex.model_validate_json(r"""{"entries": [],"types": []}""")

        self.assertEqual(
            DevdocsIndex(
                entries=[],
                types=[],
            ),
            index,
        )

    def test_unmarshal(self):
        index = DevdocsIndex.model_validate_json(
            r"""
            {
                "entries": [{
                    "name": "Accept-Encoding",
                    "path": "headers/accept-encoding",
                    "type": "Headers"
                }],
                "types": [{
                    "name": "Headers",
                    "count": 145,
                    "slug": "headers"
                }]
            }
            """
        )

        self.assertEqual(
            DevdocsIndex(
                entries=[
                    DevdocsIndexEntry(
                        name="Accept-Encoding",
                        path="headers/accept-encoding",
                        type="Headers",
                    ),
                ],
                types=[
                    DevdocsIndexType(
                        name="Headers",
                        count=145,
                        slug="headers",
                    ),
                ],
            ),
            index,
        )

    def test_build_navigation(self):
        index = DevdocsIndex(
            entries=[
                DevdocsIndexEntry(name="Appendix 1", path="", type="Appendix"),
                DevdocsIndexEntry(name="Middle 1", path="", type="Middle"),
                DevdocsIndexEntry(name="Appendix 2", path="", type="Appendix"),
                DevdocsIndexEntry(name="Tutorial 1", path="", type="Tutorials"),
                DevdocsIndexEntry(name="Middle 2", path="", type="Middle"),
                DevdocsIndexEntry(name="Tutorial 2", path="", type="Tutorials"),
            ],
            types=[
                DevdocsIndexType(name="Appendix", count=2, slug=""),
                DevdocsIndexType(name="Tutorials", count=2, slug=""),
                DevdocsIndexType(name="Middle", count=2, slug=""),
            ],
        )

        got = index.build_navigation()

        self.assertEqual(
            [
                NavigationSection(
                    name="Tutorials",
                    links=[
                        DevdocsIndexEntry(name="Tutorial 1", path="", type="Tutorials"),
                        DevdocsIndexEntry(name="Tutorial 2", path="", type="Tutorials"),
                    ],
                ),
                NavigationSection(
                    name="Middle",
                    links=[
                        DevdocsIndexEntry(name="Middle 1", path="", type="Middle"),
                        DevdocsIndexEntry(name="Middle 2", path="", type="Middle"),
                    ],
                ),
                NavigationSection(
                    name="Appendix",
                    links=[
                        DevdocsIndexEntry(name="Appendix 1", path="", type="Appendix"),
                        DevdocsIndexEntry(name="Appendix 2", path="", type="Appendix"),
                    ],
                ),
            ],
            got,
        )

    def test_build_navigation_ignores_none(self):
        index = DevdocsIndex(
            entries=[
                DevdocsIndexEntry(name="Appendix 1", path="", type=None),
            ],
            types=[
                DevdocsIndexType(name="Appendix", count=1, slug=""),
            ],
        )

        got = index.build_navigation()

        self.assertEqual(
            [
                NavigationSection(
                    name="Appendix",
                    links=[],
                ),
            ],
            got,
        )


class TestDevdocsClient(TestCase):
    def setUp(self):
        self.client = DevdocsClient(
            documents_url="https://docs.docs",
            frontend_url="https://frontend.frontend",
        )

        self.requests_patcher = patch("devdocs2zim.client.requests", autospec=True)
        self.mock_requests = self.requests_patcher.start()
        self.mock_response = create_autospec(Response)
        self.mock_requests.get.return_value = self.mock_response

    def tearDown(self):
        self.requests_patcher.stop()

    def test_read_frontend_file_normal(self):
        self.mock_response.text = "file-contents"

        contents = self.client.read_frontend_file("path/to/foo.txt")

        self.assertEqual("file-contents", contents)
        self.mock_requests.get.assert_called_with(
            url="https://frontend.frontend/path/to/foo.txt",
            allow_redirects=True,
            timeout=ANY,
        )

    def test_read_frontend_file_errors(self):
        self.mock_response.raise_for_status.side_effect = HTTPError("test error")

        self.assertRaises(HTTPError, self.client.read_frontend_file, "path/to/foo.txt")

    def test_read_doc_file_normal(self):
        self.mock_response.text = "file-contents"

        contents = self.client.read_doc_file("html", "index.json")

        self.assertEqual("file-contents", contents)
        self.mock_requests.get.assert_called_with(
            url="https://docs.docs/html/index.json",
            allow_redirects=True,
            timeout=ANY,
        )

    def test_read_doc_file_errors(self):
        self.mock_response.raise_for_status.side_effect = HTTPError("test error")

        self.assertRaises(HTTPError, self.client.read_doc_file, "html", "index.json")

    def test_read_application_css(self):
        self.mock_response.text = "some-css"

        contents = self.client.read_application_css()

        self.assertEqual("some-css", contents)
        self.mock_requests.get.assert_called_with(
            url="https://frontend.frontend/application.css",
            allow_redirects=ANY,
            timeout=ANY,
        )

    def test_list_docs(self):
        want_docs = [
            DevdocsMetadata(name="MyLang V1", slug="mylang~1.0"),
            DevdocsMetadata(name="MyLang V2", slug="mylang~2.0"),
        ]
        self.mock_response.text = (
            TypeAdapter(list[DevdocsMetadata]).dump_json(want_docs).decode()
        )

        got_docs = self.client.list_docs()

        self.assertEqual(want_docs, got_docs)
        self.mock_requests.get.assert_called_with(
            url="https://frontend.frontend/docs.json", allow_redirects=ANY, timeout=ANY
        )

    def test_get_index(self):
        want = DevdocsIndex(entries=[], types=[])
        self.mock_response.text = want.model_dump_json()

        got = self.client.get_index("mylang~1.0")

        self.assertEqual(want, got)
        self.mock_requests.get.assert_called_with(
            url="https://docs.docs/mylang~1.0/index.json",
            allow_redirects=ANY,
            timeout=ANY,
        )

    def test_get_meta(self):
        want = DevdocsMetadata(name="MyLang V1", slug="mylang~1.0")
        self.mock_response.text = want.model_dump_json()

        got = self.client.get_meta("mylang~1.0")

        self.assertEqual(want, got)
        self.mock_requests.get.assert_called_with(
            url="https://docs.docs/mylang~1.0/meta.json",
            allow_redirects=ANY,
            timeout=ANY,
        )

    def test_get_db(self):
        want = {"index": "data"}
        self.mock_response.text = TypeAdapter(dict[str, str]).dump_json(want).decode()

        got = self.client.get_db("mylang~1.0")

        self.assertEqual(want, got)
        self.mock_requests.get.assert_called_with(
            url="https://docs.docs/mylang~1.0/db.json", allow_redirects=ANY, timeout=ANY
        )
