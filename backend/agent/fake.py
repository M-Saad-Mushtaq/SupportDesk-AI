"""Offline deterministic mock plus scriptable provider for tests."""
import inspect
import json
import re
from backend.agent.types import ModelResult, ToolCall


def answer(kind, text, citations=None):
    return ModelResult(json.dumps({"kind": kind, "text": text, "citations": citations or []}))


class FakeProvider:
    supports_tools = True

    def __init__(self, script=None):
        self.script = script
        self.requests = []
        self.results = []

    def start(self, request):
        self.requests.append(request)
        return FakeSession(self, request)


class FakeSession:
    def __init__(self, provider, request):
        self.provider, self.request = provider, request
        self.index = 0

    async def complete(self, results, timeout):
        self.provider.results.append(results)
        if self.provider.script is not None:
            item = self.provider.script[self.index]
            self.index += 1
            if isinstance(item, Exception):
                raise item
            if callable(item):
                item = item(self.request, results)
            return await item if inspect.isawaitable(item) else item
        if not results:
            customer = next(message["text"] for message in reversed(self.request.history) if message["role"] == "user")
            if re.search(r"\b(human|person|specialist|damaged|broken)\b", customer, re.I):
                return ModelResult(calls=(ToolCall("handover", "request_human_handover", {"reason": "Customer requests specialist support or reports a damaged item."}),), finish_reason="tool_calls")
            order = re.search(r"ORD-[0-9]+", customer, re.I)
            if order:
                return ModelResult(calls=(ToolCall("order", "get_order_details", {"order_id": order.group().upper()}),), finish_reason="tool_calls")
            words = re.findall(r"[a-z]+", customer.lower())
            keywords = [word for word in words if word in ("return", "returns", "refund", "shipping", "delivery", "warranty", "exchange")]
            return ModelResult(calls=(ToolCall("search", "search_knowledge_base", {"query": " ".join(keywords[:2]) or customer[:150]}),), finish_reason="tool_calls")
        data = results[-1].data
        if results[-1].name == "search_knowledge_base" and data.get("sources"):
            source = data["sources"][0]
            quote = source["excerpt"][:300]
            return answer("policy", "Mock simulation. The uploaded document states: " + quote, [{"source_id": source["source_id"], "quote": quote}])
        if results[-1].name == "get_order_details" and data.get("ok"):
            return answer("order", f"Mock simulation. Stored order {data['order_id']}: {data['delivery']}. This is sample shipping data, not live tracking.")
        return answer("clarification", "I could not find enough supporting information. Please clarify the policy or order you need, or ask for a person.")

    async def close(self):
        pass
