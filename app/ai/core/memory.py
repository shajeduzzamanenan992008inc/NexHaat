"""Bounded, request-local AI conversation context; never persists transcripts."""

from collections import deque


class AIMemory:
    def __init__(self, *, max_messages=8, max_chars=4000):
        self.messages = deque(maxlen=max(1, min(int(max_messages), 12)))
        self.max_chars = max(256, min(int(max_chars), 8000))

    def add(self, role, text):
        if role not in {"user", "assistant"} or not isinstance(text, str):
            return
        self.messages.append({"role": role, "content": text[: self.max_chars]})

    def snapshot(self):
        messages = list(self.messages)
        total = 0
        bounded = []
        for message in reversed(messages):
            size = len(message["content"])
            if total + size > self.max_chars:
                break
            bounded.append(message)
            total += size
        return list(reversed(bounded))
