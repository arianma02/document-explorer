from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from pydantic import BaseModel

from app.extraction import extract_text


app = FastAPI(title="Document Explorer")
MAX_DOCUMENT_BYTES = 2 * 1024 * 1024


class ExtractedDocument(BaseModel):
    filename: str
    text: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/documents", response_model=ExtractedDocument)
def upload_document(file: UploadFile):
    try:
        filename = file.filename or ""
        extension = Path(filename).suffix.lower()
        if extension not in (".txt", ".pdf"):
            raise HTTPException(415, "Upload a UTF-8 .txt file or a PDF.")

        # Read one extra byte so oversized files are detected without loading all of them.
        content = file.file.read(MAX_DOCUMENT_BYTES + 1)
        if len(content) > MAX_DOCUMENT_BYTES:
            raise HTTPException(413, "The document must be 2 MB or smaller.")

        try:
            text = extract_text(content, extension)
        except ValueError as error:
            raise HTTPException(422, str(error)) from None

        return ExtractedDocument(filename=filename, text=text)
    finally:
        file.file.close()
