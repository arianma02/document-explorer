from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PyPdfError


def extract_text(content: bytes, extension: str) -> str:
    """Extract UTF-8 text or PDF text using a lowercase .txt or .pdf extension.

    Raise ValueError for unsupported, unreadable, or empty content. No OCR is run.
    """
    if extension == ".txt":
        try:
            text = content.decode("utf-8-sig").strip()
        except UnicodeDecodeError:
            raise ValueError("The document must contain UTF-8 text.") from None
    elif extension == ".pdf":
        text = extract_pdf_text(content)
    else:
        raise ValueError("Unsupported document format.")

    if not text:
        if extension == ".pdf":
            raise ValueError("No readable text found. Scanned PDFs need OCR, which is not supported yet.")
        raise ValueError("The document contains no text.")
    if "\x00" in text:
        raise ValueError("The document contains binary data.")
    return text


def extract_pdf_text(content: bytes) -> str:
    """Extract page text without preserving layout or explicit page numbers."""
    try:
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported. Upload an unencrypted copy.")

        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\n\n".join(pages).strip()
    except (PyPdfError, OSError, NotImplementedError):
        raise ValueError("The PDF could not be read. It may be damaged or unsupported.") from None
