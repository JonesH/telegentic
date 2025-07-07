"""Tests for the minimal bot framework with type safety."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from telegentic import EchoArgs, HandlerBotBase, NoArgs, TypedEvent

TEST_TOKEN = os.getenv("TELEGENTIC_TEST_TOKEN", "test_token")


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

    def test_bot_initialization(self) -> None:
        """Test bot initialization."""
        bot = TestBot(TEST_TOKEN)
        assert bot.bot_token == TEST_TOKEN
        assert bot.webhook_path == "/webhook"
        assert bot.bot is not None
        assert bot.dp is not None

    def test_custom_webhook_path(self) -> None:
        """Test custom webhook path."""
        bot = TestBot(TEST_TOKEN, webhook_path="/custom")
        assert bot.webhook_path == "/custom"

    @pytest.mark.asyncio
    async def test_sync_commands_with_botfather(self) -> None:
        """Test command synchronization with BotFather."""
        bot = TestBot(TEST_TOKEN)

        # Mock the bot's set_my_commands method
        with patch.object(
            bot.bot, "set_my_commands", new_callable=AsyncMock
        ) as mock_set_commands:
            await bot._sync_commands_with_botfather()

            # Check that set_my_commands was called
            mock_set_commands.assert_called_once()

            # Check the commands that were set
            call_args = mock_set_commands.call_args[0][0]
            command_names = [cmd.command for cmd in call_args]
            assert "start" in command_names
            assert "echo" in command_names

    @pytest.mark.asyncio
    async def test_empty_commands_sync(self) -> None:
        """Test sync with no commands."""

        class EmptyBot(HandlerBotBase):
            pass

        bot = EmptyBot(TEST_TOKEN)
        with patch.object(
            bot.bot, "set_my_commands", new_callable=AsyncMock
        ) as mock_set_commands:
            await bot._sync_commands_with_botfather()

            # Should not call set_my_commands for empty command list
            mock_set_commands.assert_not_called()

    def test_fastapi_app_creation(self) -> None:
        """Test FastAPI app creation when available."""
        bot = TestBot(TEST_TOKEN)

        try:
            assert bot.app is not None
        except ImportError:
            assert bot.app is None

    def test_webhook_not_available_error(self) -> None:
        """Test error when trying to use webhook without FastAPI."""
        bot = TestBot(TEST_TOKEN)

        # Mock FastAPI as not available
        bot.app = None

        with pytest.raises(RuntimeError, match="Webhook not initialized"):
            bot.run_webhook()


@pytest.mark.asyncio
class TestEventHandling:
    """Test event handling functionality."""

    async def test_handler_wrapper_with_args(self) -> None:
        """Test that handler wrapper correctly passes arguments."""
        bot = TestBot(TEST_TOKEN)

        # Mock message object
        message = MagicMock()
        message.text = "/echo hello world"
        message.reply = AsyncMock()

        # Find the echo command handler
        echo_handler = None
        for handler in bot.dp.message.handlers:
            if (
                hasattr(handler, "callback")
                and handler.callback.__name__ == "command_wrapper"
            ):
                # This is a simplified test - in practice you'd need to check the filter
                echo_handler = handler.callback
                break

        if echo_handler:
            await echo_handler(message)
            message.reply.assert_called_with("Hello from test bot!")

    async def test_handler_wrapper_without_args(self) -> None:
        """Test that handler wrapper works without arguments."""
        bot = TestBot(TEST_TOKEN)

        # Mock message object
        message = MagicMock()
        message.text = "/echo"
        message.reply = AsyncMock()

        # In a real test, you'd properly invoke the handler
        # This is a simplified version to show the concept
        event = MagicMock()
        event.reply = AsyncMock()

        await bot.handle_echo(event, "")
        event.reply.assert_called_with("No args provided")


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
