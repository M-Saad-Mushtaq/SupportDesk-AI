"""Local documents, passages, and optional FTS5 index."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError

revision = "b7139a42c801"
down_revision = "872fd5de88cd"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("documents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("storage_name", sa.String(), nullable=False, unique=True),
        sa.Column("format", sa.String(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False, unique=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("warning", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("segments", sa.JSON(), nullable=False),
        sa.CheckConstraint("status IN ('processing','ready','needs_ocr','failed','deleting')", name="valid_document_status"))
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_table("document_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.String(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("section", sa.String(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.UniqueConstraint("document_id", "position"))
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    try:
        op.execute("CREATE VIRTUAL TABLE document_fts USING fts5(text, content='document_chunks', content_rowid='id', tokenize='unicode61')")
    except OperationalError as error:
        if "no such module: fts5" not in str(error).lower():
            raise
        return  # Parameterized keyword retrieval remains available.
    op.execute("""CREATE TRIGGER document_chunks_ai AFTER INSERT ON document_chunks BEGIN
        INSERT INTO document_fts(rowid, text) VALUES (new.id, new.text); END""")
    op.execute("""CREATE TRIGGER document_chunks_ad AFTER DELETE ON document_chunks BEGIN
        INSERT INTO document_fts(document_fts, rowid, text) VALUES ('delete', old.id, old.text); END""")
    op.execute("""CREATE TRIGGER document_chunks_au AFTER UPDATE ON document_chunks BEGIN
        INSERT INTO document_fts(document_fts, rowid, text) VALUES ('delete', old.id, old.text);
        INSERT INTO document_fts(rowid, text) VALUES (new.id, new.text); END""")


def downgrade():
    for name in ("document_chunks_ai", "document_chunks_ad", "document_chunks_au"):
        op.execute(f"DROP TRIGGER IF EXISTS {name}")
    op.execute("DROP TABLE IF EXISTS document_fts")
    op.drop_table("document_chunks")
    op.drop_table("documents")
