from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Status = Literal["open", "in_progress", "resolved"]
HandlingMode = Literal["ai", "human", "awaiting_human"]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class MessageInput(InputModel):
    kind: Literal["reply", "note"]
    text: str = Field(min_length=1, max_length=5000)


class StatusInput(InputModel):
    status: Status


class SettingsInput(InputModel):
    company: str = Field(min_length=1, max_length=80)
    email: str = Field(max_length=120, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    timezone: Literal["America/New_York", "America/Los_Angeles", "Europe/London", "Asia/Karachi", "UTC"]
    days: list[Literal["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]] = Field(min_length=1, max_length=7)
    start: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    end: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    tone: Literal["Warm and professional", "Concise and direct", "Friendly and casual"]
    escalateDamage: bool = Field(strict=True)
    escalateDelivery: bool = Field(strict=True)
    escalateOnRequest: bool = Field(strict=True)

    @field_validator("days")
    @classmethod
    def unique_days(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Support days must be unique.")
        return value

    @model_validator(mode="after")
    def valid_hours(self):
        if self.start >= self.end:
            raise ValueError("Closing time must be after opening time (same-day shifts).")
        return self


class SourceOut(BaseModel):
    source_id: str | None = None
    document_id: str | None = None
    page: int | None = None
    quote: str | None = None
    title: str
    section: str
    excerpt: str


class CustomerOut(BaseModel):
    id: str
    name: str
    email: str
    initials: str
    location: str
    since: str
    tier: str


class OrderItemOut(BaseModel):
    name: str
    variant: str
    amount: float


class OrderStepOut(BaseModel):
    label: str
    detail: str


class OrderOut(BaseModel):
    id: str
    placed: str
    items: list[OrderItemOut]
    delivery: str
    tracking: str
    timeline: list[OrderStepOut]


class MessageOut(BaseModel):
    origin: str = "sample"
    id: str
    kind: Literal["customer", "ai", "reply", "note"]
    text: str
    created_at: str
    sources: list[SourceOut]


class ActivityOut(BaseModel):
    id: str
    conversation_id: str
    title: str
    created_at: str
    input: dict[str, str] | None
    result: str


class ConversationOut(BaseModel):
    id: str
    subject: str
    preview: str
    channel: Literal["Email", "Web chat"]
    priority: Literal["Urgent", "Normal", "Low", "High"]
    status: Status
    handling_mode: HandlingMode
    created_at: str
    updated_at: str
    customer: CustomerOut
    order: OrderOut
    messages: list[MessageOut]
    activity: list[ActivityOut]


class OverviewOut(BaseModel):
    total: int
    active: int
    ai: int
    awaiting_human: int
    resolved: int
    handover_ids: list[str]
    historical_volume_available: Literal[False] = False
