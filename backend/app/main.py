from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import PurePath

from fastapi import FastAPI, HTTPException, Path, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from psycopg import OperationalError
from pydantic import BaseModel

from app.database import get_document, get_passages, list_documents, save_document
from app.extraction import extract_pages
from app.embeddings import EmbeddingModel, MODEL_ID
from app.passages import split_passages


@asynccontextmanager
async def lifespan(app):
    """Load one shared model before the API starts accepting requests."""
    app.state.embedding_model = EmbeddingModel()
    yield


app = FastAPI(title="Document Explorer", lifespan=lifespan)
MAX_DOCUMENT_BYTES = 2 * 1024 * 1024
MAX_DOCUMENT_PASSAGES = 100
# PostgreSQL BIGINT is a signed 64-bit integer.
MAX_DOCUMENT_ID = 2**63 - 1


class DocumentSummary(BaseModel):
    id: int
    filename: str
    created_at: datetime


class Document(DocumentSummary):
    text: str


class Passage(BaseModel):
    id: int
    document_id: int
    position: int
    page_number: int | None
    text: str


@app.exception_handler(OperationalError)
def database_unavailable(request, error):
    return JSONResponse(
        status_code=503, content={"detail": "Database temporarily unavailable."}
    )


@app.get("/health")
def health():
    """Check the API responds without checking the database."""
    return {"status": "ok"}


@app.post("/documents", response_model=Document, status_code=201)
def upload_document(file: UploadFile, request: Request):
    """Save extracted UTF-8 text or PDF text, up to 2 MiB of uploaded bytes.

    The original file is not stored. Scanned PDFs requiring OCR are unsupported.
    Documents are limited to 100 passages to bound synchronous processing time.
    """
    try:
        filename = file.filename or ""
        extension = PurePath(filename).suffix.lower()
        if extension not in (".txt", ".pdf"):
            raise HTTPException(415, "Upload a UTF-8 .txt file or a PDF.")

        # Read one extra byte so oversized files are detected without loading all of them.
        content = file.file.read(MAX_DOCUMENT_BYTES + 1)
        if len(content) > MAX_DOCUMENT_BYTES:
            raise HTTPException(413, "The document must be 2 MiB or smaller.")

        try:
            pages = extract_pages(content, extension)
            model = request.app.state.embedding_model
            passages = split_passages(pages, model.tokenizer)
            if len(passages) > MAX_DOCUMENT_PASSAGES:
                raise HTTPException(
                    413, "The document exceeds the demo limit of 100 passages."
                )
            for passage in passages:
                passage["embedding"] = model.embed(passage["text"])
                passage["embedding_model"] = MODEL_ID
        except ValueError as error:
            raise HTTPException(422, str(error)) from None

        text = "\n\n".join(page["text"] for page in pages).strip()
        return save_document(filename, text, passages)
    finally:
        file.file.close()


@app.get("/documents", response_model=list[DocumentSummary])
def documents(
    limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0)
):
    """List newest documents first without including their full text."""
    return list_documents(limit, offset)


@app.get("/documents/{document_id}", response_model=Document)
def document(document_id: int = Path(ge=1, le=MAX_DOCUMENT_ID)):
    result = get_document(document_id)
    if result is None:
        raise HTTPException(404, "Document not found.")
    return result


@app.get("/documents/{document_id}/passages", response_model=list[Passage])
def document_passages(document_id: int = Path(ge=1, le=MAX_DOCUMENT_ID)):
    if get_document(document_id) is None:
        raise HTTPException(404, "Document not found.")
    return get_passages(document_id)
