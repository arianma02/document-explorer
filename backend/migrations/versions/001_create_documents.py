"""Create the documents table."""

from alembic import op


revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE documents (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            filename TEXT NOT NULL CHECK (btrim(filename) <> ''),
            text TEXT NOT NULL CHECK (btrim(text) <> ''),
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)


def downgrade():
    op.execute("DROP TABLE documents")
