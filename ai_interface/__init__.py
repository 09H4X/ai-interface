"""ai_interface: dependency-free client for OpenAI-style chat APIs."""

from .cli import main
from .client import (
    APIError,
    Client,
    Message,
    Response,
    assistant,
    client_from_env,
    system,
    user,
)

__all__ = [
    "APIError",
    "Client",
    "Message",
    "Response",
    "assistant",
    "client_from_env",
    "main",
    "system",
    "user",
]
__version__ = "0.1.0"
