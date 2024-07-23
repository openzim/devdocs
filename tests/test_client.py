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

        placeholders = metadata.placeholders()

        self.assertEqual(
            {
                "name": "test",
                "full_name": "test",
                "slug": "test~1.23",
                "version": "",
                "release": "",
                "attribution": "",
                "home_link": "",
                "code_link": "",
                "slug_without_version": "test",
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

        placeholders = metadata.placeholders()

        self.assertEqual(
            {
                "name": "Kubernetes",
                "full_name": "Kubernetes 1.28.1",
                "slug": "kubernetes~1.28",
                "version": "1.28.1",
                "release": "1.28",
                "attribution": "&copy; 2022 The Kubernetes Authors",
                "home_link": "https://kubernetes.io/",
                "code_link": "https://github.com/kubernetes/kubernetes",
                "slug_without_version": "kubernetes",
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
