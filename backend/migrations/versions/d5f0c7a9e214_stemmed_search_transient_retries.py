"""Porter-stemmed FTS5 index and transient-retry state for agent runs.

The FTS table is external-content: it indexes existing document_chunks rows, so
rebuilding it never changes chunk IDs, documents, citations or conversations.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError

revision = "d5f0c7a9e214"
down_revision = "c901bfe20a13"
branch_labels = None
depends_on = None

TRIGGERS = ("document_chunks_ai", "document_chunks_ad", "document_chunks_au")


def has_fts():
    return op.get_bind().exec_driver_sql("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='document_fts'").scalar() > 0


def rebuild_fts(tokenizer):
    """Recreate the optional FTS5 index with a tokenizer, then rebuild it from
    the existing chunks. Databases created without FTS5 keep keyword search."""
    if not has_fts():
        return
    for name in TRIGGERS:
        op.execute(f"DROP TRIGGER IF EXISTS {name}")
    op.execute("DROP TABLE document_fts")
    try:
        op.execute(f"CREATE VIRTUAL TABLE document_fts USING fts5(text, content='document_chunks', content_rowid='id', tokenize='{tokenizer}')")
    except OperationalError as error:
        if "no such module: fts5" not in str(error).lower():
            raise
        return
    op.execute("""CREATE TRIGGER document_chunks_ai AFTER INSERT ON document_chunks BEGIN
        INSERT INTO document_fts(rowid, text) VALUES (new.id, new.text); END""")
    op.execute("""CREATE TRIGGER document_chunks_ad AFTER DELETE ON document_chunks BEGIN
        INSERT INTO document_fts(document_fts, rowid, text) VALUES ('delete', old.id, old.text); END""")
    op.execute("""CREATE TRIGGER document_chunks_au AFTER UPDATE ON document_chunks BEGIN
        INSERT INTO document_fts(document_fts, rowid, text) VALUES ('delete', old.id, old.text);
        INSERT INTO document_fts(rowid, text) VALUES (new.id, new.text); END""")
    op.execute("INSERT INTO document_fts(document_fts) VALUES ('rebuild')")


def upgrade():
    rebuild_fts("porter unicode61")
    # Plain ALTER TABLE (no batch copy) keeps agent_runs rows, constraints and
    # the partial one-active-run index untouched.
    op.add_column("agent_runs", sa.Column("transient_retries", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("agent_runs", sa.Column("retrying_until", sa.String(), nullable=True))
    op.add_column("agent_runs", sa.Column("error_detail", sa.Text(), nullable=True))


def downgrade():
    for column in ("error_detail", "retrying_until", "transient_retries"):
        op.execute(f"ALTER TABLE agent_runs DROP COLUMN {column}")
    rebuild_fts("unicode61")
