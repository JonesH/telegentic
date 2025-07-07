"""Command argument models for type-safe parsing."""

from typing import Type, TypeVar

from pydantic import BaseModel, Field, ValidationError

T = TypeVar("T", bound=BaseModel)


class CommandArgs(BaseModel):
    """Base class for command argument validation."""

    class Config:
        extra = "forbid"  # Forbid extra fields for strict validation

    @classmethod
    def parse_string(cls: Type[T], args_string: str) -> T:
        """Parse command arguments from a string.

        Default implementation creates an instance with no arguments.
        Subclasses should override this method for custom parsing logic.
        """
        try:
            # For simple cases, try to parse as JSON-like format
            # This is a basic implementation - subclasses should override
            return cls()
        except ValidationError:
            # If validation fails, return empty instance
            return cls()


class EchoArgs(CommandArgs):
    """Arguments for echo command."""

    text: str = Field(..., description="Text to echo back")
    repeat: int = Field(default=1, ge=1, le=10, description="Number of times to repeat")

    @classmethod
    def parse_string(cls, args_string: str) -> "EchoArgs":
        """Parse echo command arguments."""
        if not args_string.strip():
            raise ValueError("Text is required for echo command")

        # Simple parsing - text followed by optional repeat count
        parts = args_string.strip().split()

        if len(parts) == 1:
            return cls(text=parts[0])
        elif len(parts) >= 2 and parts[-1].isdigit():
            repeat_count = int(parts[-1])
            text = " ".join(parts[:-1])
            return cls(text=text, repeat=repeat_count)
        else:
            return cls(text=args_string.strip())


class NoArgs(CommandArgs):
    """For commands that don't take arguments."""

    @classmethod
    def parse_string(cls, args_string: str) -> "NoArgs":
        """Parse no-argument commands."""
        return cls()
