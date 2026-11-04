from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from pydantic import BaseModel


app = FastAPI(title="Document Explorer")
MAX_DOCUMENT_BYTES = 2 * 1024 * 1024


class ExtractedDocument(BaseModel):
    filename: str
    text: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/documents", response_model=ExtractedDocument)
async def upload_document(file: UploadFile):
    try:
        filename = file.filename or ""
        if Path(filename).suffix.lower() != ".txt":
            raise HTTPException(415, "Upload a UTF-8 .txt file.")

        # Read one extra byte so oversized files are detected without loading all of them.
        content = await file.read(MAX_DOCUMENT_BYTES + 1)
        if len(content) > MAX_DOCUMENT_BYTES:
            raise HTTPException(413, "The document must be 2 MB or smaller.")

        try:
            text = content.decode("utf-8-sig").strip()
        except UnicodeDecodeError:
            raise HTTPException(422, "The document must contain UTF-8 text.") from None

        if not text:
            raise HTTPException(422, "The document contains no text.")
        if "\x00" in text:
            raise HTTPException(422, "The document contains binary data.")

        return ExtractedDocument(filename=filename, text=text)
    finally:
        await file.close()
