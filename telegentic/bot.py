"""Minimal telegram bot with automatic command discovery."""

import asyncio
import logging
import os
import re
from abc import ABCMeta
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, ClassVar, Protocol

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.methods import send_chat_action
from aiogram.types import BotCommand, Message, Update
from dotenv import load_dotenv

from .admin import AdminChannelManager

load_dotenv()
try:
    import uvicorn
    from fastapi import FastAPI, Request

    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False

logger = logging.getLogger(__name__)


def no_typing(func):
    """Decorator to disable typing indicator for a handler."""
    func._no_typing = True
    return func


class TypedEvent:
    """Typed event wrapper that provides access to aiogram Message properties."""

    def __init__(self, msg: Message) -> None:
        self.message = msg
        self.text = msg.text
        self.from_user = msg.from_user
        self.chat = msg.chat
        self.date = msg.date
        self.message_id = msg.message_id

    async def reply(self, text: str, **kwargs: Any) -> Message:
        """Reply to the message with type-safe parameters."""
        return await self.message.reply(text, **kwargs)


class HandlerProtocol(Protocol):
    """Protocol for bot handler methods."""

    def __call__(self, bot: Any, event: TypedEvent, args: str) -> Awaitable[None]:
        """Handler method signature."""
        ...


class HandlerMeta(ABCMeta):
    """Metaclass that automatically discovers handler methods and creates command mappings."""

    _commands: dict[str, HandlerProtocol]

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
    ) -> type:
        # 1) create the class
        cls = super().__new__(mcs, name, bases, namespace)

        # 2) start with any inherited commands
        commands: dict[str, HandlerProtocol] = {}
        for base in bases:
            base_cmds = getattr(base, "_commands", None)
            if isinstance(base_cmds, dict):
                commands.update(base_cmds)

        # 3) discover new handlers in this class’s namespace
        for attr_name, method in namespace.items():
            if not callable(method):
                continue

            cmd: str | None = None

            # snake_case: handle_foo -> foo
            if attr_name.startswith("handle_"):
                cmd = attr_name[len("handle_") :]

            # camelCase: handleFooBar -> foo_bar
            elif attr_name.startswith("handle") and len(attr_name) > len("handle"):
                tail = attr_name[len("handle") :]
                if tail and tail[0].isupper():
                    # insert underscore before each capital, lowercase everything
                    snake = re.sub(
                        r"([A-Z])", lambda m: "_" + str(m.group(1)).lower(), tail
                    )
                    cmd = snake.lstrip("_")

            if cmd:
                commands[cmd] = method  # override any inherited

        # 4) attach the final map
        cls._commands = commands
        return cls


class HandlerBotBase(metaclass=HandlerMeta):
    """Base bot class with automatic command discovery and optional webhook support."""

    _commands: ClassVar[dict[str, HandlerProtocol]]

    def __init__(self, bot_token: str, webhook_path: str = "/webhook") -> None:
        self.bot_token = bot_token
        self.webhook_path = webhook_path
        self.bot = Bot(token=bot_token)
        self.dp = Dispatcher()
        self._typing_tasks: dict[int, asyncio.Task] = {}
        self._admin_manager = AdminChannelManager(self.bot)
        self._setup_handlers()

        # Only setup webhook if FastAPI is available
        if _FASTAPI_AVAILABLE:
            self.app: FastAPI | None = FastAPI()
            self._setup_webhook()
        else:
            self.app = None

    def _setup_handlers(self) -> None:
        """Set up aiogram handlers for discovered commands."""
        # Add auto-generated help command if not already defined
        if "help" not in self._commands:
            # Create a proper bound method for the help handler
            async def help_handler(bot_instance, event: TypedEvent, args: str) -> None:
                await bot_instance._auto_help_handler(event, args)
            self._commands["help"] = help_handler

        for command_name, handler in self._commands.items():
            # Create a wrapper that adapts the handler signature
            def create_command_handler(
                cmd_handler: HandlerProtocol,  # [[Any, TypedEvent, str], Awaitable[None]],
                cmd_name: str,
            ) -> Callable[[Message], Awaitable[None]]:
                async def command_wrapper(message: Message) -> None:
                    # Extract arguments from message text
                    text = message.text or ""
                    parts = text.split(" ", 1)
                    args = parts[1] if len(parts) > 1 else ""

                    # Create typed event wrapper
                    event = TypedEvent(message)
                    
                    # Check if handler should have typing indicator
                    if not getattr(cmd_handler, '_no_typing', False):
                        await self._start_typing(message.chat.id)
                        try:
                            await cmd_handler(self, event, args)
                        finally:
                            await self._stop_typing(message.chat.id)
                    else:
                        await cmd_handler(self, event, args)

                return command_wrapper

            # Register the command handler
            command_handler = create_command_handler(handler, command_name)
            self.dp.message.register(command_handler, Command(command_name))

    def _setup_webhook(self) -> None:
        """Set up FastAPI webhook endpoint."""
        if not self.app:
            return

        @self.app.post(self.webhook_path)
        async def webhook_handler(request: Request) -> dict[str, str]:
            data = await request.json()
            update = Update.model_validate(data)
            await self.dp.feed_update(self.bot, update)
            return {"status": "ok"}

    async def _sync_commands_with_botfather(self) -> None:
        """Sync discovered commands with BotFather using Bot API."""
        if not self._commands:
            logger.info("No commands to sync")
            return

        # Generate command descriptions from method docstrings
        bot_commands: list[BotCommand] = []
        for cmd_name, method in self._commands.items():
            # Get description from docstring or use default
            description = "Command"
            if hasattr(method, "__doc__") and method.__doc__:
                # Extract first line of docstring
                doc_lines = method.__doc__.strip().split("\n")
                description = doc_lines[0].strip(".")
                if not description:
                    description = "Command"

            bot_commands.append(
                BotCommand(command=cmd_name, description=description[:256])
            )

        await self.bot.set_my_commands(bot_commands)
        logger.info(
            f"Successfully synced {len(bot_commands)} commands with BotFather: {[cmd.command for cmd in bot_commands]}"
        )

    async def start(self) -> None:
        """Start the bot and sync commands."""
        await self._sync_commands_with_botfather()
        await self._admin_manager.check_admin_channel_setup()
        logger.info("Bot started successfully")

    def run_webhook(self, host: str = "0.0.0.0", port: int = 8000) -> None:
        """Run the bot with webhook support."""
        if not _FASTAPI_AVAILABLE:
            raise RuntimeError(
                "FastAPI is not available. Install with: pip install fastapi uvicorn"
            )

        if not self.app:
            raise RuntimeError("Webhook not initialized")

        # Register startup event handler
        @self.app.on_event("startup")
        async def startup_event() -> None:
            await self.start()

        # Start FastAPI server
        uvicorn.run(self.app, host=host, port=port)

    async def run_polling(self) -> None:
        """Run the bot with polling."""
        await self.start()
        try:
            await self.dp.start_polling(self.bot)
        except KeyboardInterrupt:
            await self._shutdown()
        finally:
            await self._shutdown()

    async def _shutdown(self) -> None:
        """Handle bot shutdown."""
        logger.info("🛑 Bot shutting down...")
        logger.info("✅ Shutdown complete")

    async def _auto_help_handler(self, event: TypedEvent, args: str) -> None:
        """Auto-generated help command that lists all available commands and their descriptions."""
        help_lines = ["Available commands:"]
        
        for cmd_name, handler in sorted(self._commands.items()):
            # Get description from docstring or use default
            description = "Command"
            if hasattr(handler, "__doc__") and handler.__doc__:
                # Extract first line of docstring
                doc_lines = handler.__doc__.strip().split("\n")
                description = doc_lines[0].strip(".")
                if not description:
                    description = "Command"
            
            help_lines.append(f"/{cmd_name} - {description}")
        
        await event.reply("\n".join(help_lines))

    async def _start_typing(self, chat_id: int) -> None:
        """Start continuous typing indicator for a chat."""
        if chat_id in self._typing_tasks:
            return  # Already typing

        async def typing_loop():
            try:
                while True:
                    await self.bot(send_chat_action.SendChatAction(chat_id=chat_id, action="typing"))
                    await asyncio.sleep(4)  # Send typing action every 4 seconds
            except asyncio.CancelledError:
                pass  # Task was cancelled, stop typing

        self._typing_tasks[chat_id] = asyncio.create_task(typing_loop())

    async def _stop_typing(self, chat_id: int) -> None:
        """Stop typing indicator for a chat."""
        if chat_id in self._typing_tasks:
            self._typing_tasks[chat_id].cancel()
            del self._typing_tasks[chat_id]

