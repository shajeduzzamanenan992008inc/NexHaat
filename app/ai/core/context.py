"""Small, bounded request context for provider prompts."""

from dataclasses import dataclass, field
import json


@dataclass
class AIContext:
    scope: str
    locale: str = "en_US"
    channel: str = "web"
    request_id: str | None = None
    facts: dict = field(default_factory=dict)
    history: list = field(default_factory=list)

    def as_dict(self, *, max_chars=12000):
        safe = {
            "scope": self.scope,
            "locale": self.locale,
            "channel": self.channel,
            "facts": self.facts,
            "history": self.history[-8:],
        }
        encoded = json.dumps(safe, ensure_ascii=False, default=str)
        if len(encoded) > max_chars:
            safe["history"] = []
            encoded = json.dumps(safe, ensure_ascii=False, default=str)
        if len(encoded) > max_chars:
            safe["facts"] = {}
        return safe
