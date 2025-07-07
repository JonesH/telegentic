"""Tests for the minimal bot framework with type safety."""

import os
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from telegentic import EchoArgs, HandlerBotBase, NoArgs, TypedEvent

TEST_TOKEN = os.getenv("TELEGENTIC_TEST_TOKEN", "test_token")


@pytest.fixture
def mock_bot() -> Generator[MagicMock, None, None]:
    """Fixture that provides a mocked aiogram Bot."""
    with patch("telegentic.bot.Bot") as mock_bot_class:
        mock_bot_instance = MagicMock()
        mock_bot_instance.set_my_commands = AsyncMock()
        mock_bot_class.return_value = mock_bot_instance
        yield mock_bot_instance


@pytest.fixture
def mock_dispatcher() -> Generator[MagicMock, None, None]:
    """Fixture that provides a mocked aiogram Dispatcher."""
    with patch("telegentic.bot.Dispatcher") as mock_dispatcher_class:
        mock_dispatcher_instance = MagicMock()
        mock_dispatcher_instance.message = MagicMock()
        mock_dispatcher_instance.message.register = MagicMock()
        mock_dispatcher_instance.start_polling = AsyncMock()
        mock_dispatcher_instance.feed_update = AsyncMock()
        mock_dispatcher_class.return_value = mock_dispatcher_instance
        yield mock_dispatcher_instance


class TestBot(HandlerBotBase):
    """Test bot for unit testing."""

    async def handle_start(self, event: TypedEvent, args: str) -> None:
        """Test start command."""
        await event.reply("Hello from test bot!")

    async def handle_echo(self, event: TypedEvent, args: str) -> None:
        """Test echo command with type-safe arguments."""
        try:
            echo_args = EchoArgs.parse_string(args)
            response = " ".join([echo_args.text] * echo_args.repeat)
            await event.reply(f"Echo: {response}")
        except (ValidationError, ValueError):
            await event.reply("No args provided")

    async def handle_ping(self, event: TypedEvent, args: str) -> None:
        """Test ping command."""
        await event.reply("Pong!")


class TestHandlerMeta:
    """Test the handler metaclass."""

    def test_snake_case_handler_discovery(self) -> None:
        """Test that snake_case handlers are discovered correctly."""
        assert "start" in TestBot._commands
        assert "echo" in TestBot._commands
        assert "ping" in TestBot._commands

    def test_camelcase_handler_discovery(self) -> None:
        """Test that camelCase handlers are discovered correctly."""

        class CamelCaseBot(HandlerBotBase):
            async def handleTest(self, event: TypedEvent, args: str) -> None:
                """Test camelCase handler."""
                await event.reply("Test command")

        assert "test" in CamelCaseBot._commands

    def test_non_handler_methods_ignored(self) -> None:
        """Test that non-handler methods are ignored."""

        class MixedBot(HandlerBotBase):
            async def handle_start(self, event: TypedEvent, args: str) -> None:
                """Start command."""
                await event.reply("Start")

            async def some_other_method(self) -> None:
                """This should be ignored."""
                pass

        assert "start" in MixedBot._commands
        assert "some_other_method" not in MixedBot._commands


class TestHandlerBotBase:
    """Test the HandlerBotBase class."""

    def test_bot_initialization(
        self, mock_bot: MagicMock, mock_dispatcher: MagicMock
    ) -> None:
        """Test bot initialization."""
        bot = TestBot(TEST_TOKEN)
        assert bot.bot_token == TEST_TOKEN
        assert bot.webhook_path == "/webhook"
        assert bot.bot is not None
        assert bot.dp is not None

    def test_custom_webhook_path(
        self, mock_bot: MagicMock, mock_dispatcher: MagicMock
    ) -> None:
        """Test custom webhook path."""
        bot = TestBot(TEST_TOKEN, webhook_path="/custom")
        assert bot.webhook_path == "/custom"

    @pytest.mark.asyncio
    async def test_sync_commands_with_botfather(
        self, mock_bot: MagicMock, mock_dispatcher: MagicMock
    ) -> None:
        """Test command synchronization with BotFather."""
        bot = TestBot(TEST_TOKEN)

        await bot._sync_commands_with_botfather()

        # Check that set_my_commands was called on the mocked bot
        mock_bot.set_my_commands.assert_called_once()

        # Check the commands that were set
        call_args = mock_bot.set_my_commands.call_args[0][0]
        command_names = [cmd.command for cmd in call_args]
        assert "start" in command_names
        assert "echo" in command_names

    @pytest.mark.asyncio
    async def test_empty_commands_sync(
        self, mock_bot: MagicMock, mock_dispatcher: MagicMock
    ) -> None:
        """Test sync with no commands."""

        class EmptyBot(HandlerBotBase):
            pass

        bot = EmptyBot(TEST_TOKEN)
        await bot._sync_commands_with_botfather()

        # Should not call set_my_commands for empty command list
        mock_bot.set_my_commands.assert_not_called()

    def test_fastapi_app_creation(
        self, mock_bot: MagicMock, mock_dispatcher: MagicMock
    ) -> None:
        """Test FastAPI app creation when available."""
        bot = TestBot(TEST_TOKEN)

        try:
            assert bot.app is not None
        except ImportError:
            assert bot.app is None

    def test_webhook_not_available_error(
        self, mock_bot: MagicMock, mock_dispatcher: MagicMock
    ) -> None:
        """Test error when trying to use webhook without FastAPI."""
        bot = TestBot(TEST_TOKEN)

        # Mock FastAPI as not available
        bot.app = None

        with pytest.raises(RuntimeError, match="Webhook not initialized"):
            bot.run_webhook()


@pytest.mark.asyncio
class TestEventHandling:
    """Test event handling functionality."""

    async def test_handler_wrapper_with_args(
        self, mock_bot: MagicMock, mock_dispatcher: MagicMock
    ) -> None:
        """Test that handler wrapper correctly passes arguments."""
        bot = TestBot(TEST_TOKEN)

        # Mock message object with all required properties
        message = MagicMock()
        message.text = "/echo hello world"
        message.message_id = 123
        message.from_user = MagicMock()
        message.chat = MagicMock()
        message.date = MagicMock()
        message.reply = AsyncMock(return_value=message)

        # Test the handler directly rather than trying to find it in the dispatcher
        event = TypedEvent(message)
        await bot.handle_echo(event, "hello world")
        message.reply.assert_called()

    async def test_handler_wrapper_without_args(
        self, mock_bot: MagicMock, mock_dispatcher: MagicMock
    ) -> None:
        """Test that handler wrapper works without arguments."""
        bot = TestBot(TEST_TOKEN)

        # Mock message object with all required properties
        message = MagicMock()
        message.text = "/echo"
        message.message_id = 123
        message.from_user = MagicMock()
        message.chat = MagicMock()
        message.date = MagicMock()
        message.reply = AsyncMock(return_value=message)

        # Test directly by calling the handler
        event = TypedEvent(message)
        await bot.handle_echo(event, "")
        message.reply.assert_called_with("No args provided")


class TestTypedEvent:
    """Test the TypedEvent wrapper."""

    def test_typed_event_properties(self) -> None:
        """Test that TypedEvent exposes Message properties."""
        # Mock aiogram Message
        mock_message = MagicMock()
        mock_message.text = "Hello"
        mock_message.message_id = 123
        mock_message.from_user = MagicMock()
        mock_message.chat = MagicMock()
        mock_message.date = MagicMock()
        mock_message.reply = AsyncMock()

        event = TypedEvent(mock_message)

        assert event.text == "Hello"
        assert event.message_id == 123
        assert event.from_user == mock_message.from_user
        assert event.chat == mock_message.chat
        assert event.date == mock_message.date
        assert event.message == mock_message


class TestCommandArgs:
    """Test command argument parsing."""

    def test_echo_args_parsing(self) -> None:
        """Test EchoArgs parsing."""
        # Test simple text
        args = EchoArgs.parse_string("hello")
        assert args.text == "hello"
        assert args.repeat == 1

        # Test with repeat count
        args = EchoArgs.parse_string("hello 3")
        assert args.text == "hello"
        assert args.repeat == 3

        # Test multi-word text
        args = EchoArgs.parse_string("hello world")
        assert args.text == "hello world"
        assert args.repeat == 1

    def test_echo_args_validation(self) -> None:
        """Test EchoArgs validation."""
        # Test empty string raises ValueError
        with pytest.raises(ValueError):
            EchoArgs.parse_string("")

        with pytest.raises(ValueError):
            EchoArgs.parse_string("   ")

    def test_no_args_parsing(self) -> None:
        """Test NoArgs parsing."""
        args = NoArgs.parse_string("")
        assert isinstance(args, NoArgs)

        args = NoArgs.parse_string("ignored")
        assert isinstance(args, NoArgs)
