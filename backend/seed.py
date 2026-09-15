"""Run explicitly: python -m backend.seed. Existing scenarios are never modified."""
import json
from pathlib import Path

from backend.database import make_engine, write_session
from backend.models import ActivityEvent, Conversation, Customer, Message, Order, SupportSettings
from backend.schemas import SettingsInput


def seed(engine):
    data = json.loads(Path(__file__).with_name("seed_data.json").read_text(encoding="utf-8"))
    inserted = 0
    with write_session(engine) as session:
        for ticket in data["tickets"]:
            if session.get(Conversation, ticket["id"]):
                continue  # Preserve ALL existing history, status, and handling.
            customer_id = f"CUS-{ticket['id'].removeprefix('TKT-')}"
            customer = ticket["customer"]
            if not session.get(Customer, customer_id):
                session.add(Customer(id=customer_id, name=customer["name"], email=customer["email"], profile={key: value for key, value in customer.items() if key not in ("name", "email")}))
                session.flush()
            order = session.get(Order, ticket["order"]["id"])
            if order and order.customer_id != customer_id:
                raise ValueError("Seed order belongs to a different customer; existing data was left unchanged.")
            if not order:
                session.add(Order(id=ticket["order"]["id"], customer_id=customer_id, details={key: value for key, value in ticket["order"].items() if key != "id"}))
                session.flush()
            # These dates describe imported fictional scenarios, not analytics.
            sample_time = lambda time: f"2025-10-27T{time}:00+00:00"
            session.add(Conversation(id=ticket["id"], customer_id=customer_id, order_id=ticket["order"]["id"], subject=ticket["subject"], preview=ticket["preview"], channel=ticket["channel"], priority=ticket["priority"], status={"Open": "open", "Pending": "in_progress", "Resolved": "resolved"}[ticket["status"]], handling_mode={"AI handling": "ai", "You are handling": "human", "Needs handover": "awaiting_human"}[ticket["handling"]], created_at=sample_time(ticket["messages"][0]["time"]), updated_at=sample_time(ticket["updated"])))
            session.flush()
            for index, message in enumerate(ticket["messages"], 1):
                session.add(Message(id=message["id"], conversation_id=ticket["id"], position=index, kind=message["kind"], text=message["text"], created_at=sample_time(message["time"]), sources=message.get("sources", [])))
            for index, event in enumerate(ticket["activity"], 1):
                session.add(ActivityEvent(id=event["id"], conversation_id=ticket["id"], position=index, title=event["title"], created_at=sample_time(event["time"]), input=event.get("input"), result="Imported sample result: " + event["result"]))
            inserted += 1
        if not session.get(SupportSettings, 1):
            session.add(SupportSettings(id=1, data=SettingsInput.model_validate(data["settings"]).model_dump()))
        session.commit()
    return inserted


if __name__ == "__main__":
    engine = make_engine()
    try:
        print(f"Seed complete: {seed(engine)} conversations added. Existing records preserved.")
    finally:
        engine.dispose()
