"""Telegentic - Minimal Telegram Bot Framework"""

# Re-export commonly used aiogram types for convenience
from aiogram.types import BotCommand, Chat, Message, User

from .admin import AdminChannelManager
from .args import CommandArgs, EchoArgs, NoArgs
from .bot import HandlerBotBase, HandlerProtocol, TypedEvent, no_typing

__all__ = [
    "HandlerBotBase",
    "TypedEvent",
    "HandlerProtocol",
    "AdminChannelManager",
    "CommandArgs",
    "EchoArgs",
    "NoArgs",
    "Message",
    "User",
    "Chat",
    "BotCommand",
    "no_typing",
]
