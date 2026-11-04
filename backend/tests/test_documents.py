import unittest

from fastapi.testclient import TestClient

from app.main import app
from tests.pdf_helpers import make_pdf


class DocumentUploadTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def upload(self, content, filename="notes.txt", content_type="text/plain"):
        return self.client.post(
            "/documents", files={"file": (filename, content, content_type)}
        )

    def test_returns_filename_and_extracted_text(self):
        response = self.upload(b"Hello")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"filename": "notes.txt", "text": "Hello"})

    def test_accepts_uppercase_extension(self):
        response = self.upload(b"Hello", "notes.TXT")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["text"], "Hello")

    def test_rejects_unsupported_extension(self):
        self.assertEqual(self.upload(b"Hello", "notes.docx").status_code, 415)

    def test_returns_extraction_errors_as_422(self):
        response = self.upload(b"\xff")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "The document must contain UTF-8 text.")

    def test_enforces_size_boundary(self):
        limit = 2 * 1024 * 1024
        self.assertEqual(self.upload(b"a" * limit).status_code, 200)
        self.assertEqual(self.upload(b"a" * (limit + 1)).status_code, 413)

    def test_requires_a_file(self):
        self.assertEqual(self.client.post("/documents").status_code, 422)

    def test_uploads_pdf_and_returns_extracted_text(self):
        content = make_pdf(["First page", "Second page"])
        response = self.upload(content, "notes.PDF", "application/pdf")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"filename": "notes.PDF", "text": "First page\n\nSecond page"},
        )
