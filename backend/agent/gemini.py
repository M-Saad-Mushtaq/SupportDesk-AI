"""Only this module handles Google SDK objects and continuation metadata."""
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
import logging
import math
import re
from uuid import uuid4
import httpx
from google import genai
from google.genai import types, errors
from backend.agent.types import ModelResult, ProviderError, ToolCall

logger = logging.getLogger(__name__)


def log_api_error(error, model, sanitize):
    """Server-side only: HTTP status, provider status and a sanitized, bounded
    message. Never logs keys, headers, URLs, request bodies or customer text."""
    message = sanitize(str(getattr(error, "message", None) or ""))
    message = re.sub(r"https?://\S+", "[url]", message)
    message = re.sub(r"(?i)(key|token|authorization)\s*[=:]\s*\S+", r"\1=[redacted]", message)
    message = " ".join(message.split())[:300]
    logger.warning("Gemini API error: http_status=%s provider_status=%s model=%s message=%s", getattr(error, "code", None), sanitize(str(getattr(error, "status", None) or "")), model, message)


def retry_delay(error):
    headers = getattr(getattr(error, "response", None), "headers", {}) or {}
    raw = headers.get("retry-after")
    if raw:
        try:
            delay = float(raw)
        except ValueError:
            try:
                delay = (parsedate_to_datetime(raw) - datetime.now(timezone.utc)).total_seconds()
            except (ValueError, TypeError):
                delay = 60
        return min(86400, max(0, delay)) if math.isfinite(delay) else 60
    for item in getattr(error, "details", None) or []:
        if isinstance(item, dict) and str(item.get("retryDelay", "")).endswith("s"):
            try:
                delay = float(item["retryDelay"][:-1])
                if math.isfinite(delay):
                    return min(86400, max(0, delay))
            except ValueError:
                pass
    return 60 if getattr(error, "code", None) == 429 else None


class GeminiProvider:
    supports_tools = True

    def __init__(self, config, client_factory=None):
        self.config = config
        self.client_factory = client_factory or genai.Client

    def start(self, request):
        # Explicit Developer API: no Vertex credentials, paid fallback, built-in
        # web grounding, automatic function execution, or automatic retries.
        client = self.client_factory(api_key=self.config.key, vertexai=False, http_options=types.HttpOptions(timeout=int(self.config.request_timeout * 1000), retry_options=types.HttpRetryOptions(attempts=1)))
        return GeminiSession(client, self.config.model, request, self.config.sanitize)


class GeminiSession:
    def __init__(self, client, model, request, sanitize=lambda value: value):
        self.client, self.model, self.request, self.sanitize = client, model, request, sanitize
        self.contents = [types.Content(role="user" if message["role"] == "user" else "model", parts=[types.Part(text=message["text"])]) for message in request.history]
        self.pending = {}

    async def complete(self, results, timeout):
        if self.pending:
            if len(results) != len(self.pending) or {result.id for result in results} != set(self.pending) or any(result.name != self.pending.get(result.id, (None,))[0] for result in results):
                raise ProviderError("protocol", "Tool results did not match their model calls.")
            parts = [types.Part(function_response=types.FunctionResponse(id=self.pending[result.id][1], name=result.name, response=result.data)) for result in results]
            self.contents.append(types.Content(role="user", parts=parts))
            self.pending = {}
        elif results:
            raise ProviderError("protocol", "Unexpected tool results.")
        declarations = [types.FunctionDeclaration(name=tool["name"], description=tool["description"], parameters_json_schema=tool["parameters"]) for tool in self.request.tools]
        try:
            response = await self.client.aio.models.generate_content(model=self.model, contents=self.contents, config=types.GenerateContentConfig(system_instruction=self.request.system, tools=[types.Tool(function_declarations=declarations)], automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True), max_output_tokens=self.request.max_output_tokens, http_options=types.HttpOptions(timeout=max(1, int(timeout * 1000)), retry_options=types.HttpRetryOptions(attempts=1))))
        except errors.APIError as error:
            code = getattr(error, "code", 0)
            log_api_error(error, self.model, self.sanitize)
            if code == 429:
                raise ProviderError("quota", "Gemini free quota or rate limit reached. Check AI Studio and wait before an explicit retry. No paid fallback was used.", retry_delay(error)) from None
            if code in (401, 403):
                raise ProviderError("credentials", "Gemini rejected access. Check the backend key and project access privately in AI Studio.") from None
            if code in (400, 404):
                raise ProviderError("configuration", "Gemini rejected this model or request. Check AI_MODEL and function-calling support in the official documentation.") from None
            raise ProviderError("provider", "Gemini is temporarily unavailable. Retry manually later.", retry_delay(error)) from None
        except httpx.TimeoutException:
            raise ProviderError("timeout", "Gemini request timed out. No automatic retry was made.") from None
        except Exception:
            raise ProviderError("connection", "Could not connect to Gemini. Check your connection and backend configuration; retry manually.") from None
        candidate = response.candidates[0] if response.candidates else None
        content = candidate.content if candidate else None
        if not content:
            raise ProviderError("blocked", "Gemini returned no usable response. Rephrase the test message or request human help.")
        # Preserve the entire content object unchanged, including opaque thought
        # signatures. Neither thoughts nor signatures leave this adapter/session.
        self.contents.append(content)
        calls, texts = [], []
        for part in content.parts or []:
            if part.function_call:
                call = part.function_call
                identifier = call.id or str(uuid4())
                if identifier in self.pending or not isinstance(call.args, dict):
                    raise ProviderError("malformed_tool", "Gemini returned a malformed function call.")
                self.pending[identifier] = (call.name, call.id)
                calls.append(ToolCall(identifier, call.name or "", dict(call.args)))
            elif part.text and not part.thought:
                texts.append(part.text)
        finish = getattr(candidate.finish_reason, "value", str(candidate.finish_reason or ""))
        normalized = "length" if finish == "MAX_TOKENS" else ("tool_calls" if calls else "stop") if finish == "STOP" else "blocked"
        usage = response.usage_metadata
        return ModelResult("".join(texts), tuple(calls), normalized, {"input_tokens": getattr(usage, "prompt_token_count", None), "output_tokens": getattr(usage, "candidates_token_count", None), "total_tokens": getattr(usage, "total_token_count", None)})

    async def close(self):
        await self.client.aio.aclose()
        self.client.close()
