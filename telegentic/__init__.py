"""Telegentic - Minimal Telegram Bot Framework"""

# Re-export commonly used aiogram types for convenience
from aiogram.types import BotCommand, Chat, Message, User

from .args import CommandArgs, EchoArgs, NoArgs
from .bot import HandlerBotBase, HandlerProtocol, TypedEvent

__all__ = [
    "HandlerBotBase",
    "TypedEvent",
    "HandlerProtocol",
    "CommandArgs",
    "EchoArgs",
    "NoArgs",
    "Message",
    "User",
    "Chat",
    "BotCommand",
]
