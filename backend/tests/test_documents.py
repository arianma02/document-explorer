from pathlib import Path
from unittest.mock import patch

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from psycopg import OperationalError
from psycopg.errors import CheckViolation

from app.database import get_connection
from app.embeddings import MODEL_ID
from app.main import app

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def upload(client, content, filename="notes.txt", content_type="text/plain"):
    return client.post("/documents", files={"file": (filename, content, content_type)})


def test_returns_filename_and_extracted_text(client):
    response = upload(client, b"Hello")
    assert response.status_code == 201
    result = response.json()
    assert result["id"] > 0
    assert result["filename"] == "notes.txt"
    assert result["text"] == "Hello"
    assert "created_at" in result


def test_accepts_uppercase_extension(client):
    response = upload(client, b"Hello", "notes.TXT")
    assert response.status_code == 201
    assert response.json()["text"] == "Hello"


def test_rejects_unsupported_extension(client):
    assert upload(client, b"Hello", "notes.docx").status_code == 415


def test_returns_extraction_errors_as_422(client):
    response = upload(client, b"\xff")
    assert response.status_code == 422
    assert response.json()["detail"] == "The document must contain UTF-8 text."
    assert client.get("/documents").json() == []


def test_enforces_size_boundary(client):
    limit = 2 * 1024 * 1024
    assert upload(client, b"a" * limit).status_code == 201
    assert upload(client, b"a" * (limit + 1)).status_code == 413


def test_requires_a_file(client):
    assert client.post("/documents").status_code == 422


def test_uploads_pdf_and_returns_extracted_text(client):
    content = (FIXTURES_DIR / "two_pages.pdf").read_bytes()
    response = upload(client, content, "notes.PDF", "application/pdf")
    assert response.status_code == 201
    assert response.json()["filename"] == "notes.PDF"
    assert response.json()["text"] == "First page\n\nSecond page"


def test_retrieves_saved_text_through_a_new_client(client):
    filename = "Robert'); DROP TABLE documents;--.txt"
    content = "Hello, världen! 'quoted text'".encode("utf-8")
    uploaded = upload(client, content, filename).json()
    with TestClient(app) as another_client:
        response = another_client.get(f"/documents/{uploaded['id']}")
    assert response.status_code == 200
    assert response.json() == uploaded
    assert response.json()["filename"] == filename
    assert response.json()["text"] == content.decode("utf-8")


def test_lists_newest_documents_first_with_pagination(client):
    assert client.get("/documents").json() == []
    uploaded = []
    for filename in ("first.txt", "second.txt", "third.txt"):
        uploaded.append(upload(client, b"Hello", filename).json())
    response = client.get("/documents?limit=1&offset=1")
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": uploaded[1]["id"],
            "filename": "second.txt",
            "created_at": uploaded[1]["created_at"],
        }
    ]
    assert [item["id"] for item in client.get("/documents").json()] == [
        item["id"] for item in reversed(uploaded)
    ]


def test_returns_404_for_missing_document(client):
    response = client.get("/documents/9223372036854775807")
    assert response.status_code == 404


def test_returns_ordered_pdf_passages_with_page_numbers(client):
    content = (FIXTURES_DIR / "two_pages.pdf").read_bytes()
    uploaded = upload(client, content, "pages.pdf", "application/pdf").json()
    response = client.get(f"/documents/{uploaded['id']}/passages")
    assert response.status_code == 200
    passages = response.json()
    assert [item["text"] for item in passages] == ["First page", "Second page"]
    assert [item["page_number"] for item in passages] == [1, 2]
    assert [item["position"] for item in passages] == [1, 2]
    assert all(item["document_id"] == uploaded["id"] for item in passages)


def test_text_passages_have_no_page_number(client):
    uploaded = upload(client, ("word " * 151).encode()).json()
    passages = client.get(f"/documents/{uploaded['id']}/passages").json()
    assert [len(item["text"].split()) for item in passages] == [150, 1]
    assert [item["page_number"] for item in passages] == [None, None]


def test_missing_document_passages_return_404(client):
    response = client.get("/documents/9223372036854775807/passages")
    assert response.status_code == 404


def test_failed_passage_insert_rolls_back_document(client):
    invalid_passages = [{"position": 0, "page_number": None, "text": "Valid text"}]
    with patch("app.main.split_passages", return_value=invalid_passages):
        with pytest.raises(CheckViolation):
            upload(client, b"Valid document text")
    assert client.get("/documents").json() == []


def test_migration_backfills_existing_documents_without_page_numbers(client):
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    # Only the disposable test database is downgraded.
    command.downgrade(config, "001")
    original_text = "old  text\n" + "word " * 150
    with get_connection() as connection:
        row = connection.execute(
            "INSERT INTO documents (filename, text) VALUES (%s, %s) RETURNING id",
            ("existing.pdf", original_text),
        ).fetchone()
    command.upgrade(config, "head")
    document = client.get(f"/documents/{row['id']}").json()
    passages = client.get(f"/documents/{row['id']}/passages").json()
    assert document["text"] == original_text
    assert [len(item["text"].split()) for item in passages] == [150, 2]
    assert [item["page_number"] for item in passages] == [None, None]


def test_rejects_invalid_pagination_and_document_ids(client):
    for path in (
        "/documents?limit=0",
        "/documents?limit=101",
        "/documents?offset=-1",
        "/documents/0",
        "/documents/not-a-number",
        "/documents/9223372036854775808",
    ):
        assert client.get(path).status_code == 422


def test_upload_stores_embeddings_with_model_version(client):
    uploaded = upload(client, b"Solar panels generate electricity.").json()
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT embedding, embedding_model FROM passages WHERE document_id = %s",
            (uploaded["id"],),
        ).fetchall()
    assert len(rows) == 1
    assert len(rows[0]["embedding"]) == 384
    assert rows[0]["embedding_model"] == MODEL_ID


def test_token_heavy_text_is_split_without_losing_words(client):
    text = "electroencephalography " * 150
    uploaded = upload(client, text.encode()).json()
    response = client.get(f"/documents/{uploaded['id']}/passages")
    passages = response.json()
    assert len(passages) > 1
    assert " ".join(item["text"] for item in passages).split() == text.split()
    for passage in passages:
        tokens = app.state.embedding_model.tokenizer.encode(passage["text"])
        assert len(tokens.ids) <= 256


def test_rejects_documents_over_processing_limit(client):
    text = "word " * (150 * 100 + 1)
    response = upload(client, text.encode())
    assert response.status_code == 413
    assert client.get("/documents").json() == []


def test_rejects_single_word_that_exceeds_token_limit(client):
    response = upload(client, ("energy-" * 300).encode())
    assert response.status_code == 422
    assert client.get("/documents").json() == []


def test_database_outage_returns_503_without_connection_details(client):
    with patch(
        "app.database.get_connection", side_effect=OperationalError("private details")
    ):
        responses = [
            upload(client, b"Hello"),
            client.get("/documents"),
            client.get("/documents/1"),
            client.get("/graph"),
            client.delete("/documents/1"),
        ]
    for response in responses:
        assert response.status_code == 503
        assert response.json() == {"detail": "Database temporarily unavailable."}


def test_delete_removes_only_the_selected_document_and_its_passages(client):
    first = upload(client, b"Solar panels generate electricity.", "same.txt").json()
    second = upload(client, b"Solar panels generate electricity.", "same.txt").json()
    assert len(client.get("/graph").json()["edges"]) == 1
    response = client.delete(f"/documents/{first['id']}")
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/documents/{first['id']}").status_code == 404
    assert client.get(f"/documents/{first['id']}/passages").status_code == 404
    assert client.get(f"/documents/{second['id']}").json() == second
    with get_connection() as connection:
        remaining = connection.execute("SELECT document_id FROM passages").fetchall()
    assert remaining
    assert all(row["document_id"] == second["id"] for row in remaining)
    graph = client.get("/graph").json()
    assert [node["id"] for node in graph["nodes"]] == [second["id"]]
    assert graph["edges"] == []


def test_deleting_a_missing_document_returns_404(client):
    assert client.delete("/documents/9223372036854775807").status_code == 404


def test_delete_rejects_invalid_ids_without_removing_documents(client):
    uploaded = upload(client, b"Keep this document").json()
    for document_id in ("0", "-1", "not-a-number", "9223372036854775808"):
        assert client.delete(f"/documents/{document_id}").status_code == 422
    assert client.get(f"/documents/{uploaded['id']}").status_code == 200


def test_unknown_api_routes_return_404(client):
    for path in ("/does-not-exist", "/documents/1/does-not-exist"):
        assert client.get(path).status_code == 404
