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


def clean_message(error, sanitize):
    message = sanitize(str(getattr(error, "message", None) or ""))
    message = re.sub(r"https?://\S+", "[url]", message)
    message = re.sub(r"(?i)(key|token|authorization)\s*[=:]\s*\S+", r"\1=[redacted]", message)
    return " ".join(message.split())[:300]


def log_api_error(error, model, sanitize):
    """Server-side only: HTTP status, provider status and a sanitized, bounded
    message. Never logs keys, headers, URLs, request bodies or customer text."""
    logger.warning("Gemini API error: http_status=%s provider_status=%s model=%s message=%s", getattr(error, "code", None), sanitize(str(getattr(error, "status", None) or "")), model, clean_message(error, sanitize))


def error_details(error):
    """google.rpc detail objects (RetryInfo, QuotaFailure, ...) from the response
    JSON. APIError.details holds the whole body: {"error": {"details": [...]}}."""
    body = getattr(error, "details", None)
    items = body.get("error", {}).get("details", []) if isinstance(body, dict) else body if isinstance(body, list) else []
    return [item for item in items if isinstance(item, dict)]


def seconds(value):
    try:
        delay = float(str(value).removesuffix("s"))
    except ValueError:
        return None
    return min(86400, max(0, delay)) if math.isfinite(delay) else None


def retry_delay(error):
    """Retry-After header, else RetryInfo.retryDelay ("12s"); 60 s default for 429."""
    headers = getattr(getattr(error, "response", None), "headers", {}) or {}
    raw = headers.get("retry-after")
    if raw:
        delay = seconds(raw)
        if delay is None:
            try:
                delay = min(86400, max(0, (parsedate_to_datetime(raw) - datetime.now(timezone.utc)).total_seconds()))
            except (ValueError, TypeError):
                delay = 60
        return delay
    for item in error_details(error):
        if "retryDelay" in item and seconds(item["retryDelay"]) is not None:
            return seconds(item["retryDelay"])
    return 60 if getattr(error, "code", None) == 429 else None


def quota_ids(error):
    return [str(violation.get("quotaId", "")) for item in error_details(error) for violation in item.get("violations", []) or [] if isinstance(violation, dict)]


def classify(error, sanitize):
    """Map an SDK APIError to a safe ProviderError. Only temporary overload
    (500/502/503/504) and per-minute rate limits are transient; keys, invalid
    requests, unavailable models and exhausted daily/free-tier quota are never
    retried automatically. Unknown 429s are treated conservatively as quota."""
    code = getattr(error, "code", 0) or 0
    detail = f"HTTP {code} {sanitize(str(getattr(error, 'status', None) or ''))}".strip() + ": " + clean_message(error, sanitize)
    if code == 429:
        ids = quota_ids(error)
        per_minute = bool(ids) and all("PerMinute" in quota for quota in ids) and any("retryDelay" in item for item in error_details(error))
        if per_minute:
            return ProviderError("rate_limit", "Gemini rate limit reached. Waiting briefly before an automatic retry.", retry_delay(error), True, detail)
        return ProviderError("quota", "Gemini free quota or rate limit reached. Check AI Studio and wait before an explicit retry. No paid fallback was used.", retry_delay(error), False, detail)
    if code in (401, 403):
        return ProviderError("credentials", "Gemini rejected access. Check the backend key and project access privately in AI Studio.", None, False, detail)
    if code in (400, 404):
        return ProviderError("configuration", "Gemini rejected this model or request. Check AI_MODEL and function-calling support in the official documentation.", None, False, detail)
    if code in (500, 502, 503, 504):
        return ProviderError("provider", "Gemini is temporarily unavailable. Retry manually later.", retry_delay(error), True, detail)
    return ProviderError("provider", "Gemini returned an unexpected error. Retry manually later.", retry_delay(error), False, detail)


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
        # Build the request without mutating session state: if Gemini fails, the
        # same step (including these tool results) can be retried unchanged.
        contents = list(self.contents)
        if self.pending:
            if len(results) != len(self.pending) or {result.id for result in results} != set(self.pending) or any(result.name != self.pending.get(result.id, (None,))[0] for result in results):
                raise ProviderError("protocol", "Tool results did not match their model calls.")
            parts = [types.Part(function_response=types.FunctionResponse(id=self.pending[result.id][1], name=result.name, response=result.data)) for result in results]
            contents.append(types.Content(role="user", parts=parts))
        elif results:
            raise ProviderError("protocol", "Unexpected tool results.")
        declarations = [types.FunctionDeclaration(name=tool["name"], description=tool["description"], parameters_json_schema=tool["parameters"]) for tool in self.request.tools]
        try:
            response = await self.client.aio.models.generate_content(model=self.model, contents=contents, config=types.GenerateContentConfig(system_instruction=self.request.system, tools=[types.Tool(function_declarations=declarations)], automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True), max_output_tokens=self.request.max_output_tokens, http_options=types.HttpOptions(timeout=max(1, int(timeout * 1000)), retry_options=types.HttpRetryOptions(attempts=1))))
        except errors.APIError as error:
            log_api_error(error, self.model, self.sanitize)
            raise classify(error, self.sanitize) from None
        except httpx.TimeoutException:
            # Not retried automatically: Google may still have processed it.
            raise ProviderError("timeout", "Gemini request timed out. No automatic retry was made.") from None
        except Exception:
            raise ProviderError("connection", "Could not connect to Gemini. Check your connection and backend configuration; retry manually.") from None
        self.contents, self.pending = contents, {}
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
