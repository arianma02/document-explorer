from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from psycopg import sql

from app.database import DEFAULT_DATABASE_URL, get_connection
from app.main import app


@pytest.fixture(scope="module")
def database():
    """Use a disposable local database, including when migration setup fails."""
    database_name = "test_documents_" + uuid4().hex
    create_query = sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
    with psycopg.connect(DEFAULT_DATABASE_URL, autocommit=True) as connection:
        connection.execute(create_query)

    server_url = DEFAULT_DATABASE_URL.rsplit("/", 1)[0]
    test_database_url = server_url + "/" + database_name
    try:
        with patch("app.database.get_database_url", return_value=test_database_url):
            migrations_file = Path(__file__).resolve().parents[1] / "alembic.ini"
            command.upgrade(Config(str(migrations_file)), "head")
            yield
    finally:
        drop_query = sql.SQL("DROP DATABASE {}").format(sql.Identifier(database_name))
        with psycopg.connect(DEFAULT_DATABASE_URL, autocommit=True) as connection:
            connection.execute(drop_query)


@pytest.fixture(scope="module")
def api_client(database):
    with TestClient(app) as client:
        yield client


@pytest.fixture
def client(api_client):
    with get_connection() as connection:
        connection.execute("DELETE FROM documents")
    return api_client
