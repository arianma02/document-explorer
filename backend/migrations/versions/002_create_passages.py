"""Store passages and backfill existing text without inventing page references."""

from alembic import op
import sqlalchemy as sa


revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE passages (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            position INTEGER NOT NULL CHECK (position > 0),
            page_number INTEGER CHECK (page_number > 0),
            text TEXT NOT NULL CHECK (btrim(text) <> ''),
            UNIQUE (document_id, position)
        )
    """)
    connection = op.get_bind()
    documents = (
        connection.execute(sa.text("SELECT id, text FROM documents")).mappings().all()
    )
    # This initial backfill has no original PDF files, so page numbers stay unknown.
    for document in documents:
        words = document["text"].split()
        for start in range(0, len(words), 150):
            connection.execute(
                sa.text("""
                INSERT INTO passages (document_id, position, text)
                VALUES (:document_id, :position, :text)
            """),
                {
                    "document_id": document["id"],
                    "position": start // 150 + 1,
                    "text": " ".join(words[start : start + 150]),
                },
            )


def downgrade():
    op.execute("DROP TABLE passages")
