# CLAUDE.md

## Development Practices

- Use context7, always use venv with uv run. Tracebacks must bubble, only catch if necessary
- Adhere to clean code principles, following DRY (Don't Repeat Yourself) paradigm
- Utilize modern generics and comprehensive type hints in all code
- Use builtin types like dict, list etc and avoid typing imports
- never `from typing import Optional, List, Dict` we have `| None`, list and dict etc.
- never catch `Exception`
- never git add .
- never coauthor
- always semantic commit messages
- use httpx for async web

## Project Overview

Minimal and elegant Telegram bot framework for Python that:
- Uses aiogram for Bot API integration
- Automatically discovers handler methods and registers slash commands
- Just implement the handler - slash command registration is automatic
- Optional webhook support via FastAPI (available as optional dependency)
- Focuses on simplicity and developer experience
- Metaclass-based command discovery from method names

## Core Technology

- **aiogram** — Modern Bot API framework (core dependency)
- **python-dotenv** — Environment variable management
- **FastAPI + uvicorn** — Optional webhook support (fastapi extra)
- **pytest + pytest-asyncio** — Testing framework (dev dependency)

## Common Commands

- **Run example bot**: `uv run python example_bot.py`
- **Install dependencies**: `uv sync`
- **Run tests**: `uv run pytest`

## Architecture

### Command Discovery
Handler methods automatically become slash commands:
- `handle_start` → `/start` command
- `handle_help` → `/help` command
- `handle_echo` → `/echo` command
- `handle_ping` → `/ping` command

The framework uses a metaclass to automatically discover methods with `handle_` prefix or camelCase `handle*` methods and register them as bot commands with aiogram.

## Environment Variables

Required for bot operation:
- `TELEGRAM_BOT_TOKEN` - Your bot token from @BotFather

## Code Style Preferences

Follow these Python development practices for this project:

### Modern Python Features
- Use Python 3.11+ features and built-in generics: `list[str]`, `dict[str, int]`, `str | None`
- Avoid imports from typing module where possible (use built-in types)
- Use union syntax `|` instead of `Optional[]` or `Union[]`

### Code Organization
- Write self-documenting code with clear, descriptive names
- Keep functions small and focused on single responsibility
- Use guard clauses and early returns to reduce nesting
- Extract complex logic into well-named helper functions
- Prefer flat code structure over deeply nested blocks

### Type Hints
- Use comprehensive type hints throughout
- Leverage modern Python type syntax (built-in generics, union types)
- Only import from typing when necessary (Protocol, TypeVar, Generic)

### Error Handling
- Avoid over-catching exceptions; let unexpected errors propagate
- Only catch exceptions when meaningful recovery is possible
- Use specific exception types rather than broad catches

### General Practices
- Follow DRY principles - extract common functionality
- Use constants for magic numbers and repeated values
- Favor explicit, readable code over clever implementations
- Maintain consistent code style with existing codebase patterns

## Memories

- never coauthor
- do not add @coauthor to git commit messages
- no Optional, do | None instead