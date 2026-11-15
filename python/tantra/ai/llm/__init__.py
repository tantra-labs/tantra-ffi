# wheel surface (ex 0002 closure)

from __future__ import annotations

from typing import Any, Protocol

__all__ = ["LlmPort", "ScriptedFakeLlm"]


class LlmPort(Protocol):
    """Protocol for LLM providers."""

    def complete(self, prompt: str, **kwargs: Any) -> str:
        """Return LLM completion for the prompt."""
        ...

    def ask(self, prompt: str) -> str:
        """Convenience: complete a single user message."""
        ...


class ScriptedFakeLlm:
    """Deterministic test double for LLM — returns scripted responses."""

    def __init__(self, fake_response: str | None = None):
        self.fake_response = fake_response
        self.call_history: list[dict] = []

    def complete(self, prompt: str, **kwargs: Any) -> str:
        self.call_history.append({"prompt": prompt, "kwargs": kwargs})
        if self.fake_response is not None:
            return self.fake_response
        return prompt  # Echo by default

    def ask(self, prompt: str) -> str:
        """Convenience: complete a single user message."""
        return self.complete([{"role": "user", "content": prompt}])

    def reset(self) -> None:
        self.call_history.clear()
