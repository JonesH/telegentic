# Telegentic

Minimal and elegant Telegram bot framework for Python that automatically discovers handler methods and registers slash commands.

## Features

- **Automatic command discovery** - Just implement the handler method, slash command registration is automatic
- **Metaclass-based** - Uses Python metaclass to discover `handle_*` methods
- **aiogram integration** - Built on top of the modern aiogram Bot API framework
- **Optional webhook support** - FastAPI integration available as optional dependency
- **Auto-sync with BotFather** - Commands are automatically synced with Telegram's BotFather
- **Simple and focused** - Minimal boilerplate, maximum developer experience

## Installation

```bash
# Core functionality
uv add telegentic

# With webhook support
uv add telegentic[fastapi]
```

## Quick Start

```python
from telegentic import SimpleBot

class MyBot(SimpleBot):
    async def handle_start(self, event, args: str) -> None:
        """Welcome message for new users."""
        await event.reply("Hello! I'm your bot.")

    async def handle_echo(self, event, args: str) -> None:
        """Echo the user's message."""
        await event.reply(f"You said: {args}")

# Run with polling
bot = MyBot("YOUR_BOT_TOKEN")
await bot.run_polling()
```

## Command Discovery

Handler methods automatically become slash commands:
- `handle_start` - `/start` command
- `handle_help` - `/help` command
- `handle_echo` - `/echo` command
- `handle_ping` - `/ping` command

The framework uses a metaclass to automatically discover methods with `handle_` prefix and register them as bot commands with aiogram.

## Environment Variables

Required for bot operation:
- `TELEGRAM_BOT_TOKEN` - Your bot token from @BotFather

## Example

See `example_bot.py` for a complete working example with multiple commands.

## Development

```bash
# Install dependencies
uv sync

# Run example bot
uv run python example_bot.py

# Run tests
uv run pytest
```

## Dependencies

- **aiogram** v3.20.0 - Modern Bot API framework
- **python-dotenv** v1.0.0 - Environment variable management
- **fastapi** v0.115.0 - Optional webhook support
- **uvicorn** v0.30.0 - Optional ASGI server

## License

MIT
