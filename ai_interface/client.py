"""Minimal dependency-free client for OpenAI-style chat completion APIs.

Works with any server that implements POST /chat/completions with the
OpenAI request/response shape (OpenAI, OpenRouter, Ollama, LM Studio,
llama.cpp server, vLLM, ...).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Iterator

__all__ = ["Client", "Message", "Response", "APIError"]


class APIError(RuntimeError):
    """Raised for transport errors and non-2xx API responses."""

    def __init__(self, message: str, status: int | None = None, body: str = ""):
        super().__init__(message)
        self.status = status
        self.body = body


@dataclass
class Message:
    """One chat message. `content` may be a string or a content-parts list."""

    role: str  # "system" | "user" | "assistant"
    content: str

    def to_dict(self) -> dict[str, Any]:
        return {"role": self.role, "content": self.content}


def system(text: str) -> Message:
    return Message("system", text)


def user(text: str) -> Message:
    return Message("user", text)


def assistant(text: str) -> Message:
    return Message("assistant", text)


@dataclass
class Response:
    """A completed chat response."""

    text: str
    model: str = ""
    finish_reason: str = ""
    usage: dict[str, int] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Client:
    """OpenAI-style chat client.

    base_url: e.g. "https://api.openai.com/v1" (no trailing slash needed).
    api_key: sent as Bearer token. Omit for local servers that need none.
    """

    base_url: str
    api_key: str = ""
    timeout: float = 120.0

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        if not self.api_key:
            self.api_key = os.environ.get("AI_API_KEY", "")

    # -- core -----------------------------------------------------------

    def _request(
        self, payload: dict[str, Any], *, stream: bool
    ) -> urllib.request.Request:
        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if stream:
            payload = {**payload, "stream": True}
        data = json.dumps(payload).encode()
        return urllib.request.Request(url, data=data, headers=headers, method="POST")

    def _open(self, req: urllib.request.Request) -> Any:
        try:
            return urllib.request.urlopen(req, timeout=self.timeout)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            raise APIError(f"HTTP {e.code}: {body}", status=e.code, body=body) from e
        except urllib.error.URLError as e:
            raise APIError(f"connection failed: {e.reason}") from e

    @staticmethod
    def _messages(messages: list[Message]) -> list[dict[str, Any]]:
        return [m.to_dict() if isinstance(m, Message) else m for m in messages]

    # -- public API -------------------------------------------------------

    def complete(
        self,
        messages: list[Message],
        *,
        model: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> Response:
        """Send messages, return the full completion."""
        payload: dict[str, Any] = {"model": model, "messages": self._messages(messages)}
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if extra:
            payload.update(extra)
        with self._open(self._request(payload, stream=False)) as resp:
            data = json.loads(resp.read())
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        return Response(
            text=msg.get("content") or "",
            model=data.get("model", ""),
            finish_reason=choice.get("finish_reason", ""),
            usage=data.get("usage") or {},
            raw=data,
        )

    def stream(
        self,
        messages: list[Message],
        *,
        model: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> Iterator[str]:
        """Yield content deltas as they arrive (server-sent events)."""
        payload: dict[str, Any] = {"model": model, "messages": self._messages(messages)}
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if extra:
            payload.update(extra)
        with self._open(self._request(payload, stream=True)) as resp:
            for line in resp:
                line = line.decode("utf-8", "replace").rstrip("\n\r")
                if not line.startswith("data:"):
                    continue
                data = line[len("data:") :].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                delta = (chunk.get("choices") or [{}])[0].get("delta") or {}
                piece = delta.get("content")
                if piece:
                    yield piece

    # -- convenience ------------------------------------------------------

    def ask(self, prompt: str, *, model: str, system_prompt: str = "") -> str:
        """One-shot helper: single user prompt -> assistant text."""
        msgs = [system(system_prompt)] if system_prompt else []
        msgs.append(user(prompt))
        return self.complete(msgs, model=model).text


def client_from_env() -> Client:
    """Build a Client from AI_BASE_URL (required) and AI_API_KEY (optional)."""
    base = os.environ.get("AI_BASE_URL")
    if not base:
        raise APIError("set AI_BASE_URL (e.g. https://api.openai.com/v1)")
    return Client(base_url=base)
