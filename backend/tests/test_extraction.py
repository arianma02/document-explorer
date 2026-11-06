from pathlib import Path

import pytest

from app.extraction import extract_pages

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_preserves_unicode_and_internal_line_breaks():
    content = "  Hello, världen!\nSecond paragraph.  ".encode("utf-8")
    assert extract_pages(content, ".txt") == [
        {"page_number": None, "text": "Hello, världen!\nSecond paragraph."}
    ]


def test_removes_utf8_bom():
    assert extract_pages(b"\xef\xbb\xbfHello", ".txt") == [
        {"page_number": None, "text": "Hello"}
    ]


def test_rejects_empty_or_whitespace_only_text():
    for content in (b"", b" \r\n\t"):
        with pytest.raises(ValueError, match="The document contains no text"):
            extract_pages(content, ".txt")


def test_rejects_invalid_encoding():
    with pytest.raises(ValueError, match="UTF-8"):
        extract_pages(b"\xff\xfeHello", ".txt")


def test_rejects_null_characters():
    with pytest.raises(ValueError, match="binary data"):
        extract_pages(b"Hello\x00world", ".txt")


def test_extracts_text_from_multiple_pages():
    content = (FIXTURES_DIR / "two_pages.pdf").read_bytes()
    assert extract_pages(content, ".pdf") == [
        {"page_number": 1, "text": "First page"},
        {"page_number": 2, "text": "Second page"},
    ]


def test_rejects_pdf_without_text():
    with pytest.raises(ValueError, match="No readable text"):
        extract_pages((FIXTURES_DIR / "blank.pdf").read_bytes(), ".pdf")


def test_rejects_encrypted_pdf():
    content = (FIXTURES_DIR / "encrypted.pdf").read_bytes()
    with pytest.raises(ValueError, match="Encrypted"):
        extract_pages(content, ".pdf")


def test_rejects_invalid_pdf():
    with pytest.raises(ValueError, match="could not be read"):
        extract_pages(b"not a PDF", ".pdf")
