# ai_interface

Dependency-free Python client + CLI for any OpenAI-style chat API
(OpenAI, OpenRouter, Ollama, LM Studio, llama.cpp server, vLLM, ...).
Uses only the Python standard library — no third-party packages.
Managed with [uv](https://docs.astral.sh/uv/).

> This project was generated with **GLM-5.3**, an AI coding
> assistant, on 2026-10-12.

## Setup

```bash
uv sync
```

## Configure

```bash
export AI_BASE_URL="https://api.openai.com/v1"   # or http://localhost:11434/v1 for Ollama
export AI_API_KEY="sk-..."                        # optional for local servers
export AI_MODEL="gpt-4o-mini"
```

## CLI

```bash
# one-shot prompt (streams by default)
uv run ai-interface "say hello"

# options
uv run ai-interface --model gpt-4o-mini --system "You are terse." "what is 2+2?"
uv run ai-interface --no-stream "write a haiku"

# interactive multi-turn chat
uv run ai-interface
```

Flags `--base-url`, `--api-key`, `--model`, `--system`, `--no-stream`
override the environment.

## Library

```python
from ai_interface import Client, system, user

client = Client("https://api.openai.com/v1", api_key="sk-...")

# one-shot
print(client.ask("what is 2+2?", model="gpt-4o-mini"))

# full control
resp = client.complete(
    [system("You are terse."), user("hello")],
    model="gpt-4o-mini",
    temperature=0.2,
    max_tokens=100,
)
print(resp.text, resp.usage)

# streaming
for piece in client.stream([user("tell me a story")], model="gpt-4o-mini"):
    print(piece, end="", flush=True)
```

## API reference

### `Client(base_url, api_key="", timeout=120.0)`

| Method | Returns | Description |
|---|---|---|
| `complete(messages, *, model, temperature=None, max_tokens=None, extra=None)` | `Response` | Full completion. `extra` merges arbitrary provider params into the JSON body. |
| `stream(messages, *, model, ...)` | `Iterator[str]` | Yields content deltas from the SSE stream. |
| `ask(prompt, *, model, system_prompt="")` | `str` | One-shot helper: single prompt → assistant text. |

`messages` is a list of `Message(role, content)`; use the `system()`,
`user()`, and `assistant()` helpers to build them. If `api_key` is empty,
it falls back to `$AI_API_KEY`.

### `Response`

| Field | Type | Description |
|---|---|---|
| `text` | `str` | Assistant message content. |
| `model` | `str` | Model name reported by the server. |
| `finish_reason` | `str` | e.g. `"stop"`, `"length"`. |
| `usage` | `dict` | Token counts, when provided. |
| `raw` | `dict` | Full JSON response. |

### Errors

All transport and non-2xx failures raise `ai_interface.APIError`, a
`RuntimeError` subclass with `.status` (HTTP code or `None`) and `.body`
(error response text).

### `client_from_env()`

Builds a `Client` from `AI_BASE_URL` (required) and `AI_API_KEY` (optional).
Raises `APIError` if `AI_BASE_URL` is unset.

## Project layout

```
ai_interface/
├── ai_interface/
│   ├── __init__.py   # public API re-exports
│   ├── client.py     # Client, Message, Response, APIError
│   └── cli.py        # ai-interface entry point (REPL + one-shot)
├── pyproject.toml    # zero dependencies, uv_build backend
├── uv.lock
└── README.md
```

## Requirements

- Python ≥ 3.12
- [uv](https://docs.astral.sh/uv/) for environment/lock management
- Any OpenAI-compatible chat completions endpoint
