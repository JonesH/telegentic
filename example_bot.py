"""Example bot using the minimal framework with full type safety."""

import asyncio
import os

from dotenv import load_dotenv
from pydantic import ValidationError

from telegentic import EchoArgs, HandlerBotBase, TypedEvent


class ExampleBot(HandlerBotBase):
    """Example bot with type-safe commands."""

    async def handle_start(self, event: TypedEvent, args: str) -> None:
        """Welcome message for new users."""
        user_name = event.from_user.first_name if event.from_user else "Friend"
        await event.reply(f"🤖 Welcome {user_name}! I'm your friendly type-safe bot.")

    async def handle_help(self, event: TypedEvent, args: str) -> None:
        """Show available commands."""
        help_text = """
Available commands:
/start - Welcome message
/help - Show this help
/echo <text> [repeat_count] - Echo your message with optional repeat
/ping - Check if bot is alive
/info - Show chat information
        """
        await event.reply(help_text.strip())

    async def handle_echo(self, event: TypedEvent, args: str) -> None:
        """Echo the user's message with type-safe argument parsing."""
        try:
            echo_args = EchoArgs.parse_string(args)
            response = " ".join([echo_args.text] * echo_args.repeat)
            await event.reply(f"You said: {response}")
        except ValidationError as e:
            await event.reply(f"❌ Invalid arguments: {e}")
        except ValueError as e:
            await event.reply(f"❌ {e}")

    async def handle_ping(self, event: TypedEvent, args: str) -> None:
        """Simple ping command."""
        await event.reply("🏓 Pong!")

    async def handle_info(self, event: TypedEvent, args: str) -> None:
        """Show chat and user information using typed properties."""
        chat_info = f"Chat ID: {event.chat.id}\nChat Type: {event.chat.type}"

        if event.from_user:
            user_info = f"User ID: {event.from_user.id}\nUsername: {event.from_user.username or 'None'}"
            info_text = f"📊 Chat Information:\n{chat_info}\n\n👤 User Information:\n{user_info}"
        else:
            info_text = f"📊 Chat Information:\n{chat_info}"

        await event.reply(info_text)


async def main() -> None:
    """Run the bot."""
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

    bot = ExampleBot(token)

    # Run with polling (no webhook needed)
    await bot.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
