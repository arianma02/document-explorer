from datetime import datetime

from pydantic import BaseModel


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


class Connection(BaseModel):
    source: int
    target: int
    score: float
    source_passage: Passage
    target_passage: Passage


class DocumentGraph(BaseModel):
    nodes: list[DocumentSummary]
    edges: list[Connection]
