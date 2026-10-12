"""Command-line chat REPL for any OpenAI-style endpoint.

Usage:
  ai-interface [--base-url URL] [--api-key KEY] [--model NAME]
               [--system PROMPT] [--no-stream] [PROMPT ...]

Configuration (flags > env):
  AI_BASE_URL   e.g. https://api.openai.com/v1
  AI_API_KEY    Bearer token
  AI_MODEL      default model name

With a PROMPT argument it prints one completion and exits.
Without it, starts an interactive multi-turn chat.
"""

from __future__ import annotations

import argparse
import os
import sys

from .client import Client, Message, system, user


def build_client(args: argparse.Namespace) -> Client:
    base = args.base_url or os.environ.get("AI_BASE_URL", "")
    if not base:
        sys.exit("error: no base URL. Pass --base-url or set AI_BASE_URL.")
    return Client(base_url=base, api_key=args.api_key)


def pick_model(args: argparse.Namespace) -> str:
    model = args.model or os.environ.get("AI_MODEL", "")
    if not model:
        sys.exit("error: no model. Pass --model or set AI_MODEL.")
    return model


def run_once(client: Client, model: str, prompt: str, sys_prompt: str, do_stream: bool) -> None:
    msgs = [system(sys_prompt)] if sys_prompt else []
    msgs.append(user(prompt))
    if do_stream:
        for piece in client.stream(msgs, model=model):
            sys.stdout.write(piece)
            sys.stdout.flush()
        sys.stdout.write("\n")
    else:
        print(client.complete(msgs, model=model).text)


def repl(client: Client, model: str, sys_prompt: str, do_stream: bool) -> None:
    history: list[Message] = [system(sys_prompt)] if sys_prompt else []
    print(f"chatting with {model} at {client.base_url} — ctrl-d to exit")
    while True:
        try:
            prompt = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not prompt:
            continue
        if prompt in ("/exit", "/quit"):
            return
        history.append(user(prompt))
        sys.stdout.write("\nassistant> ")
        if do_stream:
            for piece in client.stream(history, model=model):
                sys.stdout.write(piece)
                sys.stdout.flush()
            print()
        else:
            text = client.complete(history, model=model).text
            print(text)
            history.append(Message("assistant", text))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ai-interface", description=__doc__.splitlines()[0])
    p.add_argument("prompt", nargs="*", help="one-shot prompt; omit for interactive chat")
    p.add_argument("--base-url", help="API base, e.g. https://api.openai.com/v1")
    p.add_argument("--api-key", help="Bearer token (default: $AI_API_KEY)")
    p.add_argument("--model", help="model name (default: $AI_MODEL)")
    p.add_argument("--system", default="", help="system prompt")
    p.add_argument("--no-stream", action="store_true", help="wait for full response")
    args = p.parse_args(argv)

    client = build_client(args)
    model = pick_model(args)
    do_stream = not args.no_stream

    if args.prompt:
        run_once(client, model, " ".join(args.prompt), args.system, do_stream)
    else:
        repl(client, model, args.system, do_stream)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
