"""Add nullable embedding fields so existing documents remain readable."""

from alembic import op


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE passages
        ADD COLUMN embedding DOUBLE PRECISION[],
        ADD COLUMN embedding_model TEXT,
        ADD CONSTRAINT passages_embedding_shape CHECK (
            (embedding IS NULL AND embedding_model IS NULL)
            OR (embedding IS NOT NULL AND embedding_model IS NOT NULL
                AND array_ndims(embedding) = 1 AND cardinality(embedding) = 384)
        )
    """)


def downgrade():
    op.execute("""
        ALTER TABLE passages
        DROP CONSTRAINT passages_embedding_shape,
        DROP COLUMN embedding,
        DROP COLUMN embedding_model
    """)
