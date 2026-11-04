from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PyPdfError


def extract_pages(content: bytes, extension: str) -> list[dict]:
    """Return dictionaries containing text and page_number for .txt or .pdf files.

    PDF page numbers start at 1. Text files use None for page_number.
    Raise ValueError for unsupported, unreadable, or empty content. No OCR is run.
    """
    if extension == ".txt":
        try:
            text = content.decode("utf-8-sig").strip()
        except UnicodeDecodeError:
            raise ValueError("The document must contain UTF-8 text.") from None
    elif extension == ".pdf":
        pages = extract_pdf_pages(content)
        text = "\n\n".join(page["text"] for page in pages).strip()
    else:
        raise ValueError("Unsupported document format.")

    if not text:
        if extension == ".pdf":
            raise ValueError(
                "No readable text found. Scanned PDFs need OCR, which is not supported yet."
            )
        raise ValueError("The document contains no text.")
    if "\x00" in text:
        raise ValueError("The document contains binary data.")
    if extension == ".txt":
        return [{"page_number": None, "text": text}]
    return pages


def extract_pdf_pages(content: bytes) -> list[dict]:
    """Keep physical PDF page numbers, including pages without readable text."""
    try:
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted:
            raise ValueError(
                "Encrypted PDFs are not supported. Upload an unencrypted copy."
            )

        pages = []
        for page_number, page in enumerate(reader.pages, start=1):
            pages.append(
                {"page_number": page_number, "text": page.extract_text() or ""}
            )
        return pages
    except (PyPdfError, OSError, NotImplementedError):
        raise ValueError(
            "The PDF could not be read. It may be damaged or unsupported."
        ) from None
