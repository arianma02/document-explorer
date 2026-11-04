import unittest
from pathlib import Path

from app.extraction import extract_pages


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TextExtractionTests(unittest.TestCase):
    def test_preserves_unicode_and_internal_line_breaks(self):
        content = "  Hello, världen!\nSecond paragraph.  ".encode("utf-8")
        self.assertEqual(
            extract_pages(content, ".txt"),
            [{"page_number": None, "text": "Hello, världen!\nSecond paragraph."}],
        )

    def test_removes_utf8_bom(self):
        self.assertEqual(
            extract_pages(b"\xef\xbb\xbfHello", ".txt"),
            [{"page_number": None, "text": "Hello"}],
        )

    def test_rejects_empty_or_whitespace_only_text(self):
        for content in (b"", b" \r\n\t"):
            with self.subTest(content=content):
                with self.assertRaisesRegex(
                    ValueError, "The document contains no text"
                ):
                    extract_pages(content, ".txt")

    def test_rejects_invalid_encoding(self):
        with self.assertRaisesRegex(ValueError, "UTF-8"):
            extract_pages(b"\xff\xfeHello", ".txt")

    def test_rejects_null_characters(self):
        with self.assertRaisesRegex(ValueError, "binary data"):
            extract_pages(b"Hello\x00world", ".txt")


class PdfExtractionTests(unittest.TestCase):
    def test_extracts_text_from_multiple_pages(self):
        content = (FIXTURES_DIR / "two_pages.pdf").read_bytes()
        self.assertEqual(
            extract_pages(content, ".pdf"),
            [
                {"page_number": 1, "text": "First page"},
                {"page_number": 2, "text": "Second page"},
            ],
        )

    def test_rejects_pdf_without_text(self):
        with self.assertRaisesRegex(ValueError, "No readable text"):
            extract_pages((FIXTURES_DIR / "blank.pdf").read_bytes(), ".pdf")

    def test_rejects_encrypted_pdf(self):
        content = (FIXTURES_DIR / "encrypted.pdf").read_bytes()
        with self.assertRaisesRegex(ValueError, "Encrypted"):
            extract_pages(content, ".pdf")

    def test_rejects_invalid_pdf(self):
        with self.assertRaisesRegex(ValueError, "could not be read"):
            extract_pages(b"not a PDF", ".pdf")
