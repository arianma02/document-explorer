import unittest
from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.main import app


class DocumentUploadTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def upload(self, content, filename="notes.txt"):
        return self.client.post(
            "/documents", files={"file": (filename, content, "text/plain")}
        )

    def test_extracts_unicode_text(self):
        response = self.upload("  Hello, världen!\nSecond paragraph.  ".encode("utf-8"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"filename": "notes.txt", "text": "Hello, världen!\nSecond paragraph."},
        )

    def test_accepts_utf8_bom_and_uppercase_extension(self):
        response = self.upload(b"\xef\xbb\xbfHello", "notes.TXT")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["text"], "Hello")

    def test_rejects_unsupported_extension(self):
        self.assertEqual(self.upload(b"Hello", "notes.docx").status_code, 415)

    def test_rejects_empty_or_whitespace_only_text(self):
        for content in (b"", b" \r\n\t"):
            with self.subTest(content=content):
                self.assertEqual(self.upload(content).status_code, 422)

    def test_rejects_invalid_encoding_and_binary_data(self):
        for content in (b"\xff\xfeHello", b"Hello\x00world"):
            with self.subTest(content=content):
                self.assertEqual(self.upload(content).status_code, 422)

    def test_enforces_size_boundary(self):
        limit = 2 * 1024 * 1024
        self.assertEqual(self.upload(b"a" * limit).status_code, 200)
        self.assertEqual(self.upload(b"a" * (limit + 1)).status_code, 413)

    def test_requires_a_file(self):
        self.assertEqual(self.client.post("/documents").status_code, 422)

    def make_pdf(self, page_texts, password=None):
        writer = PdfWriter()
        font = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        })
        for text in page_texts:
            page = writer.add_blank_page(width=300, height=300)
            page[NameObject("/Resources")] = DictionaryObject({
                NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})
            })
            stream = DecodedStreamObject()
            stream.set_data(f"BT /F1 12 Tf 20 200 Td ({text}) Tj ET".encode("ascii"))
            page[NameObject("/Contents")] = stream
        if password:
            writer.encrypt(password)
        output = BytesIO()
        writer.write(output)
        return output.getvalue()

    def test_extracts_text_from_multiple_pdf_pages(self):
        content = self.make_pdf(["First page", "Second page"])
        response = self.upload(content, "notes.PDF")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["text"], "First page\n\nSecond page")

    def test_rejects_pdf_without_text(self):
        response = self.upload(self.make_pdf([""]), "blank.pdf")
        self.assertEqual(response.status_code, 422)
        self.assertIn("No readable text", response.json()["detail"])

    def test_rejects_encrypted_pdf(self):
        response = self.upload(self.make_pdf(["Secret"], password="test"), "locked.pdf")
        self.assertEqual(response.status_code, 422)
        self.assertIn("Encrypted", response.json()["detail"])

    def test_rejects_invalid_pdf(self):
        response = self.upload(b"not a PDF", "broken.pdf")
        self.assertEqual(response.status_code, 422)
        self.assertIn("could not be read", response.json()["detail"])
