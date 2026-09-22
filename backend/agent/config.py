from dataclasses import dataclass, field
import os
import re


@dataclass(frozen=True)
class AIConfig:
    provider: str = "mock"
    model: str = "mock-support-v1"
    key: str = field(default="", repr=False)
    free_tier_confirmed: bool = False
    request_timeout: float = 20
    turn_timeout: float = 60
    max_output_tokens: int = 1024
    max_requests: int = 4
    max_tool_calls: int = 6
    max_context_chars: int = 24000
    max_history_messages: int = 16
    max_attempts: int = 3
    error: str | None = None

    @classmethod
    def from_env(cls):
        provider = os.getenv("AI_PROVIDER", "mock").strip().lower()
        model = os.getenv("AI_MODEL", "gemini-2.5-flash" if provider == "gemini" else "mock-support-v1").strip()
        values = {"provider": provider, "model": model, "key": os.getenv("GEMINI_API_KEY", ""), "free_tier_confirmed": os.getenv("GEMINI_FREE_TIER_CONFIRMED", "").lower() == "true"}
        if provider not in ("mock", "gemini"):
            values.update(provider="invalid", error="Set AI_PROVIDER to mock or gemini. No fallback provider was used.")
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._/-]{0,99}", model) or model.startswith("AIza"):
            values.update(model="invalid", error="AI_MODEL is not a valid model identifier.")
        limits = {"request_timeout": ("AI_REQUEST_TIMEOUT", 20, 1, 60), "turn_timeout": ("AI_TURN_TIMEOUT", 60, 5, 180), "max_output_tokens": ("AI_MAX_OUTPUT_TOKENS", 1024, 128, 4096), "max_requests": ("AI_MAX_REQUESTS", 4, 1, 8), "max_tool_calls": ("AI_MAX_TOOL_CALLS", 6, 1, 12), "max_context_chars": ("AI_MAX_CONTEXT_CHARS", 24000, 8000, 48000), "max_history_messages": ("AI_MAX_HISTORY_MESSAGES", 16, 1, 30), "max_attempts": ("AI_MAX_ATTEMPTS", 3, 1, 5)}
        for attr, (name, default, minimum, maximum) in limits.items():
            try:
                value = int(os.getenv(name, str(default)))
                if not minimum <= value <= maximum:
                    raise ValueError()
                values[attr] = value
            except ValueError:
                values["error"] = f"{name} must be an integer from {minimum} to {maximum}."
        return cls(**values)

    def problem(self):
        if self.error:
            return self.error
        if self.provider == "gemini" and not self.key:
            return "GEMINI_API_KEY is missing. Configure it privately on the backend and restart."
        if self.provider == "gemini" and not self.free_tier_confirmed:
            return "Verify the project is on the unpaid free tier in AI Studio, then set GEMINI_FREE_TIER_CONFIRMED=true. Do not enable billing."
        return None

    def sanitize(self, value):
        if isinstance(value, str):
            if self.key:
                value = value.replace(self.key, "[redacted]")
            return re.sub(r"AIza[0-9A-Za-z_-]{20,}", "[redacted]", value)
        if isinstance(value, dict):
            return {key: self.sanitize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.sanitize(item) for item in value]
        return value
