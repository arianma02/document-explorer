import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import psycopg
from alembic import command
from alembic.config import Config
from psycopg import sql

from app.database import DEFAULT_DATABASE_URL


def prepare_test_database():
    """Create an isolated database on local PostgreSQL, which must be running."""
    unique_id = uuid4().hex
    database_name = "test_documents_" + unique_id

    create_query = sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
    with psycopg.connect(DEFAULT_DATABASE_URL, autocommit=True) as connection:
        connection.execute(create_query)

    # Register cleanup immediately so it also runs if migration setup fails.
    unittest.addModuleCleanup(drop_test_database, database_name)

    server_url = DEFAULT_DATABASE_URL.rsplit("/", 1)[0]
    test_database_url = server_url + "/" + database_name
    database_url_override = patch("app.database.get_database_url", return_value=test_database_url)
    database_url_override.start()
    unittest.addModuleCleanup(database_url_override.stop)

    migrations_file = Path(__file__).resolve().parents[1] / "alembic.ini"
    migration_config = Config(str(migrations_file))
    command.upgrade(migration_config, "head")


def drop_test_database(database_name):
    drop_query = sql.SQL("DROP DATABASE {}").format(sql.Identifier(database_name))
    with psycopg.connect(DEFAULT_DATABASE_URL, autocommit=True) as connection:
        connection.execute(drop_query)
