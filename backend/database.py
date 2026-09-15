"""One explicit database path, shared by the API, migrations, and seed command."""
import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    pass


def database_url() -> str:
    return os.environ.get("DATABASE_URL", f"sqlite:///{Path(__file__).parent / 'supportdesk.db'}")


def make_engine(url: str | None = None):
    url = url or database_url()
    if make_url(url).get_backend_name() != "sqlite":
        raise ValueError("This local demo supports SQLite only.")
    engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 15})

    @event.listens_for(engine, "connect")
    def configure(dbapi_connection, _record):
        # SQLAlchemy owns BEGIN so reads have snapshots and writes can reserve
        # SQLite's write lock before checking handling rules or retry keys.
        dbapi_connection.isolation_level = None
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    @event.listens_for(engine, "begin")
    def begin(connection):
        mode = "BEGIN IMMEDIATE" if connection.get_execution_options().get("write") else "BEGIN"
        connection.exec_driver_sql(mode)

    return engine


def write_session(engine) -> Session:
    session = Session(engine, expire_on_commit=False)
    try:
        session.connection(execution_options={"write": True})
    except Exception:
        session.close()
        raise
    return session
