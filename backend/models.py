from sqlalchemy import Index, text, JSON, CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    profile: Mapped[dict] = mapped_column(JSON)


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"))
    details: Mapped[dict] = mapped_column(JSON)


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint("status IN ('open','in_progress','resolved')", name="valid_status"),
        CheckConstraint("handling_mode IN ('ai','human','awaiting_human')", name="valid_handling"),
    )
    id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"))
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"))
    subject: Mapped[str] = mapped_column(String)
    preview: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String)
    priority: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, index=True)
    handling_mode: Mapped[str] = mapped_column(String, index=True)
    handling_revision: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[str] = mapped_column(String)
    updated_at: Mapped[str] = mapped_column(String)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "position"),
        CheckConstraint("kind IN ('customer','ai','reply','note')", name="valid_message_kind"),
    )
    id: Mapped[str] = mapped_column(String, primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String)
    sources: Mapped[list] = mapped_column(JSON)
    origin: Mapped[str] = mapped_column(String, default="local", server_default="sample")


class ActivityEvent(Base):
    __tablename__ = "activity_events"
    __table_args__ = (UniqueConstraint("conversation_id", "position"),)
    id: Mapped[str] = mapped_column(String, primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String)
    input: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result: Mapped[str] = mapped_column(Text)


class SupportSettings(Base):
    __tablename__ = "support_settings"
    __table_args__ = (CheckConstraint("id = 1", name="singleton_settings"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)


class RequestRecord(Base):
    __tablename__ = "request_records"
    key: Mapped[str] = mapped_column(String, primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String)
    response: Mapped[dict] = mapped_column(JSON)


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (CheckConstraint("status IN ('processing','ready','needs_ocr','failed','deleting')", name="valid_document_status"),)
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    filename: Mapped[str] = mapped_column(String)
    storage_name: Mapped[str] = mapped_column(String, unique=True)
    format: Mapped[str] = mapped_column(String)
    size: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String, unique=True)
    status: Mapped[str] = mapped_column(String, index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    warning: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String)
    updated_at: Mapped[str] = mapped_column(String)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    segments: Mapped[list] = mapped_column(JSON, default=list)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (UniqueConstraint("document_id", "position"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section: Mapped[str | None] = mapped_column(String, nullable=True)
    text: Mapped[str] = mapped_column(Text)


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint("status IN ('pending','running','completed','failed','cancelled','interrupted')", name="valid_run_status"),
        Index("one_active_agent_run", "conversation_id", unique=True, sqlite_where=text("status IN ('pending','running')")),
    )
    id: Mapped[str] = mapped_column(String, primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    customer_message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"), unique=True)
    response_message_id: Mapped[str | None] = mapped_column(ForeignKey("messages.id"), unique=True, nullable=True)
    provider: Mapped[str] = mapped_column(String)
    model: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    handling_revision: Mapped[int] = mapped_column(Integer)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str] = mapped_column(String)
    started_at: Mapped[str | None] = mapped_column(String, nullable=True)
    finished_at: Mapped[str | None] = mapped_column(String, nullable=True)
    retry_at: Mapped[str | None] = mapped_column(String, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    tool_count: Mapped[int] = mapped_column(Integer, default=0)
    usage: Mapped[dict] = mapped_column(JSON, default=dict)
    sources: Mapped[list] = mapped_column(JSON, default=list)
    attempts: Mapped[list] = mapped_column(JSON, default=list)


class AgentTool(Base):
    __tablename__ = "agent_tools"
    __table_args__ = (UniqueConstraint("run_id", "fingerprint"),)
    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), index=True)
    fingerprint: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    arguments: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String)
    attempt: Mapped[int] = mapped_column(Integer)
