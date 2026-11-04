import os

import psycopg
from psycopg.rows import dict_row


DEFAULT_DATABASE_URL = (
    "postgresql://document_explorer:local_development_only@127.0.0.1:5433/document_explorer"
)


def get_database_url():
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def get_connection():
    """Open a connection returning dictionaries.

    Use it in a with block to commit on success, roll back on error, and close.
    """
    return psycopg.connect(get_database_url(), row_factory=dict_row, connect_timeout=5)


def save_document(filename: str, text: str):
    with get_connection() as connection:
        row = connection.execute(
            """
            INSERT INTO documents (filename, text)
            VALUES (%s, %s)
            RETURNING id, filename, text, created_at
            """,
            (filename, text),
        ).fetchone()
    return row


def list_documents(limit: int, offset: int):
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT id, filename, created_at FROM documents
            ORDER BY id DESC LIMIT %s OFFSET %s
            """,
            (limit, offset),
        ).fetchall()


def get_document(document_id: int):
    with get_connection() as connection:
        return connection.execute(
            "SELECT id, filename, text, created_at FROM documents WHERE id = %s",
            (document_id,),
        ).fetchone()
