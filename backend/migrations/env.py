from pathlib import Path
import sys

from alembic import context

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.database import Base, database_url, make_engine
from backend import models  # noqa: F401

# FTS5 and its shadow tables are managed explicitly by the migration.
def include_object(obj, name, type_, reflected, compare_to):
    return not (type_ == "table" and name.startswith("document_fts"))

config = context.config
url = config.attributes.get("database_url") or database_url()

if context.is_offline_mode():
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True, render_as_batch=True, include_object=include_object)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = make_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True, include_object=include_object)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
