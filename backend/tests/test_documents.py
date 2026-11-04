import unittest
from pathlib import Path
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from psycopg import OperationalError
from psycopg.errors import CheckViolation

from app.database import get_connection
from app.embeddings import MODEL_ID
from app.main import app
from tests.database_helpers import prepare_test_database


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def setUpModule():
    """unittest runs this once before the tests in this file."""
    prepare_test_database()


class DocumentUploadTests(unittest.TestCase):
    def setUp(self):
        with get_connection() as connection:
            connection.execute("DELETE FROM documents")
        self.client = self.enterContext(TestClient(app))

    def upload(self, content, filename="notes.txt", content_type="text/plain"):
        return self.client.post(
            "/documents", files={"file": (filename, content, content_type)}
        )

    def test_returns_filename_and_extracted_text(self):
        response = self.upload(b"Hello")
        self.assertEqual(response.status_code, 201)
        result = response.json()
        self.assertGreater(result["id"], 0)
        self.assertEqual(result["filename"], "notes.txt")
        self.assertEqual(result["text"], "Hello")
        self.assertIn("created_at", result)

    def test_accepts_uppercase_extension(self):
        response = self.upload(b"Hello", "notes.TXT")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["text"], "Hello")

    def test_rejects_unsupported_extension(self):
        self.assertEqual(self.upload(b"Hello", "notes.docx").status_code, 415)

    def test_returns_extraction_errors_as_422(self):
        response = self.upload(b"\xff")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"], "The document must contain UTF-8 text."
        )
        self.assertEqual(self.client.get("/documents").json(), [])

    def test_enforces_size_boundary(self):
        limit = 2 * 1024 * 1024
        self.assertEqual(self.upload(b"a" * limit).status_code, 201)
        self.assertEqual(self.upload(b"a" * (limit + 1)).status_code, 413)

    def test_requires_a_file(self):
        self.assertEqual(self.client.post("/documents").status_code, 422)

    def test_uploads_pdf_and_returns_extracted_text(self):
        content = (FIXTURES_DIR / "two_pages.pdf").read_bytes()
        response = self.upload(content, "notes.PDF", "application/pdf")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["filename"], "notes.PDF")
        self.assertEqual(response.json()["text"], "First page\n\nSecond page")

    def test_retrieves_saved_text_through_a_new_client(self):
        filename = "Robert'); DROP TABLE documents;--.txt"
        content = "Hello, världen! 'quoted text'".encode("utf-8")
        uploaded = self.upload(content, filename).json()
        with TestClient(app) as another_client:
            response = another_client.get(f"/documents/{uploaded['id']}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), uploaded)
        self.assertEqual(response.json()["filename"], filename)
        self.assertEqual(response.json()["text"], content.decode("utf-8"))

    def test_lists_newest_documents_first_with_pagination(self):
        self.assertEqual(self.client.get("/documents").json(), [])
        uploaded = []
        for filename in ("first.txt", "second.txt", "third.txt"):
            uploaded.append(self.upload(b"Hello", filename).json())
        response = self.client.get("/documents?limit=1&offset=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {
                    "id": uploaded[1]["id"],
                    "filename": "second.txt",
                    "created_at": uploaded[1]["created_at"],
                }
            ],
        )
        self.assertEqual(
            [item["id"] for item in self.client.get("/documents").json()],
            [item["id"] for item in reversed(uploaded)],
        )

    def test_returns_404_for_missing_document(self):
        response = self.client.get("/documents/9223372036854775807")
        self.assertEqual(response.status_code, 404)

    def test_returns_ordered_pdf_passages_with_page_numbers(self):
        content = (FIXTURES_DIR / "two_pages.pdf").read_bytes()
        uploaded = self.upload(content, "pages.pdf", "application/pdf").json()
        response = self.client.get(f"/documents/{uploaded['id']}/passages")
        self.assertEqual(response.status_code, 200)
        passages = response.json()
        self.assertEqual(
            [item["text"] for item in passages], ["First page", "Second page"]
        )
        self.assertEqual([item["page_number"] for item in passages], [1, 2])
        self.assertEqual([item["position"] for item in passages], [1, 2])
        self.assertTrue(all(item["document_id"] == uploaded["id"] for item in passages))

    def test_text_passages_have_no_page_number(self):
        uploaded = self.upload(("word " * 151).encode()).json()
        passages = self.client.get(f"/documents/{uploaded['id']}/passages").json()
        self.assertEqual([len(item["text"].split()) for item in passages], [150, 1])
        self.assertEqual([item["page_number"] for item in passages], [None, None])

    def test_missing_document_passages_return_404(self):
        response = self.client.get("/documents/9223372036854775807/passages")
        self.assertEqual(response.status_code, 404)

    def test_failed_passage_insert_rolls_back_document(self):
        invalid_passages = [{"position": 0, "page_number": None, "text": "Valid text"}]
        with patch("app.main.split_passages", return_value=invalid_passages):
            with self.assertRaises(CheckViolation):
                self.upload(b"Valid document text")
        self.assertEqual(self.client.get("/documents").json(), [])

    def test_migration_backfills_existing_documents_without_page_numbers(self):
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        # Only the disposable database is downgraded to simulate an existing installation.
        command.downgrade(config, "001")
        original_text = "old  text\n" + "word " * 150
        with get_connection() as connection:
            row = connection.execute(
                "INSERT INTO documents (filename, text) VALUES (%s, %s) RETURNING id",
                ("existing.pdf", original_text),
            ).fetchone()
        command.upgrade(config, "head")
        document = self.client.get(f"/documents/{row['id']}").json()
        passages = self.client.get(f"/documents/{row['id']}/passages").json()
        self.assertEqual(document["text"], original_text)
        self.assertEqual([len(item["text"].split()) for item in passages], [150, 2])
        self.assertEqual([item["page_number"] for item in passages], [None, None])

    def test_rejects_invalid_pagination_and_document_ids(self):
        for path in (
            "/documents?limit=0",
            "/documents?limit=101",
            "/documents?offset=-1",
            "/documents/0",
            "/documents/not-a-number",
            "/documents/9223372036854775808",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 422)

    def test_upload_stores_embeddings_with_model_version(self):
        uploaded = self.upload(b"Solar panels generate electricity.").json()
        with get_connection() as connection:
            rows = connection.execute(
                "SELECT embedding, embedding_model FROM passages WHERE document_id = %s",
                (uploaded["id"],),
            ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(rows[0]["embedding"]), 384)
        self.assertEqual(rows[0]["embedding_model"], MODEL_ID)

    def test_token_heavy_text_is_split_without_losing_words(self):
        text = "electroencephalography " * 150
        uploaded = self.upload(text.encode()).json()
        response = self.client.get(f"/documents/{uploaded['id']}/passages")
        passages = response.json()
        self.assertGreater(len(passages), 1)
        self.assertEqual(
            " ".join(item["text"] for item in passages).split(), text.split()
        )
        for passage in passages:
            tokens = app.state.embedding_model.tokenizer.encode(passage["text"])
            self.assertLessEqual(len(tokens.ids), 256)

    def test_rejects_documents_over_processing_limit(self):
        text = "word " * (150 * 100 + 1)
        response = self.upload(text.encode())
        self.assertEqual(response.status_code, 413)
        self.assertEqual(self.client.get("/documents").json(), [])

    def test_rejects_single_word_that_exceeds_token_limit(self):
        response = self.upload(("energy-" * 300).encode())
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.get("/documents").json(), [])

    def test_database_outage_returns_503_without_connection_details(self):
        with patch(
            "app.database.get_connection",
            side_effect=OperationalError("private details"),
        ):
            responses = [
                self.upload(b"Hello"),
                self.client.get("/documents"),
                self.client.get("/documents/1"),
                self.client.get("/graph"),
            ]
        for response in responses:
            self.assertEqual(response.status_code, 503)
            self.assertEqual(
                response.json(), {"detail": "Database temporarily unavailable."}
            )
