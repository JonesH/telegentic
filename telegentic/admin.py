"""Admin channel management functionality for telegentic bots."""

import logging
import os

import telegramify_markdown
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramNotFound

logger = logging.getLogger(__name__)


class AdminChannelManager:
    """Manages admin channel setup and verification for telegram bots."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    def get_admin_ids(self) -> list[int]:
        """Parse admin IDs from environment variable."""
        admin_ids_str = os.getenv("ADMIN_TELEGRAM_ID", "")
        if not admin_ids_str:
            return []

        admin_ids = []
        # Remove any brackets and split by comma
        clean_str = admin_ids_str.strip("[]").replace(" ", "")
        for id_str in clean_str.split(","):
            if id_str.strip():  # Skip empty strings
                try:
                    admin_ids.append(int(id_str.strip()))
                except ValueError:
                    logger.warning(f"Invalid admin ID format: {id_str.strip()}")

        return admin_ids

    async def check_admin_channel_setup(self) -> None:
        """Check admin channel setup and notify first admin of any missing requirements."""
        admin_ids = self.get_admin_ids()
        if not admin_ids:
            logger.info("No admin IDs configured")
            return

        first_admin_id = admin_ids[0]
        admin_channel_id = os.getenv("ADMIN_CHANNEL_ID")
        if not admin_channel_id:
            await self._send_channel_setup_instructions(first_admin_id, admin_ids)
            return

        try:
            admin_channel_id = int(admin_channel_id)
        except ValueError:
            logger.error(f"Invalid ADMIN_CHANNEL_ID format: {admin_channel_id}")
            await self._send_channel_setup_instructions(first_admin_id, admin_ids)
            return

        # Check if bot has access to the admin channel
        try:
            chat = await self.bot.get_chat(admin_channel_id)
            logger.info(f"✅ Admin channel found: {chat.title}")

            # Check if bot is admin in the channel
            try:
                bot_member = await self.bot.get_chat_member(
                    admin_channel_id, self.bot.id
                )
                if bot_member.status not in ["administrator", "creator"]:
                    logger.warning(
                        f"⚠️ Bot is not an administrator in admin channel '{chat.title}'"
                    )
                    logger.warning(
                        "   Please make the bot an administrator with permissions to:"
                    )
                    logger.warning("   - Invite users")
                    logger.warning("   - View members")
                else:
                    logger.info("✅ Bot has admin permissions in admin channel")
            except (TelegramForbiddenError, TelegramNotFound):
                logger.warning(
                    f"⚠️ Cannot check bot permissions in admin channel '{chat.title}'"
                )
                logger.warning(
                    "   Please ensure bot is an administrator with appropriate permissions"
                )

            # Check admin membership
            await self._check_admin_membership(admin_channel_id, admin_ids, chat.title)

        except TelegramNotFound:
            logger.error(f"❌ Admin channel not found (ID: {admin_channel_id})")
            error_msg = f"Admin channel not found (ID: {admin_channel_id}). The channel may have been deleted or the bot was removed."
            await self._send_channel_setup_instructions(
                first_admin_id, admin_ids, error_msg
            )
        except TelegramForbiddenError:
            logger.error(f"❌ Bot cannot access admin channel (ID: {admin_channel_id})")
            error_msg = f"Bot cannot access admin channel (ID: {admin_channel_id}). Please add the bot to the channel and make it an administrator."
            await self._send_channel_setup_instructions(
                first_admin_id, admin_ids, error_msg
            )

    async def _send_channel_setup_instructions(
        self, admin_id: int, admin_ids: list[int], error_msg: str = ""
    ) -> None:
        """Send admin channel setup instructions to the first admin."""
        # Get the actual bot information to use real username
        bot_info = await self.bot.get_me()
        bot_username = bot_info.username or "your_bot"

        # Create markdown content that will be safely converted to MarkdownV2
        markdown_content = "# 🔧 ADMIN CHANNEL SETUP REQUIRED\n\n"

        if error_msg:
            markdown_content += f"⚠️ {error_msg}\n\n"

        markdown_content += """Please create an admin channel for bot notifications and monitoring:

## STEP 1: Create a private channel
• Open Telegram and create a new private channel (not a group)
• Give it a descriptive name like 'Bot Admin Channel'

## STEP 2: Add your bot as administrator"""

        # Add real bot username
        markdown_content += f"\n• Add @{bot_username} to the channel\n"

        markdown_content += """• Make it an administrator with permissions to:
  ✓ Invite users
  ✓ View members
  ✓ Post messages

## STEP 3: Add admin users
Add the following admin users to the channel:
"""

        # Add admin IDs safely
        for admin_id_item in admin_ids:
            markdown_content += f"• User ID: `{admin_id_item}`\n"

        markdown_content += """
## STEP 4: Get the channel ID
• Forward any message from the channel to @userinfobot
• Copy the channel ID (will be negative, like `-1001234567890`)

## STEP 5: Configure environment
• Set `ADMIN_CHANNEL_ID` environment variable to the channel ID
• Example: `ADMIN_CHANNEL_ID=-1001234567890`

Once configured, restart the bot to complete setup."""

        # Convert to safe MarkdownV2 format using telegramify-markdown
        safe_message = telegramify_markdown.markdownify(markdown_content)

        await self.bot.send_message(
            chat_id=admin_id, text=safe_message, parse_mode="MarkdownV2"
        )
        logger.info(f"✅ Setup instructions sent to admin {admin_id}")

    async def _check_admin_membership(
        self, channel_id: int, admin_ids: list[int], channel_title: str
    ) -> None:
        """Check if all admins are members of the admin channel."""
        missing_admins = []

        for admin_id in admin_ids:
            try:
                member = await self.bot.get_chat_member(channel_id, admin_id)
                if member.status in ["left", "kicked"]:
                    missing_admins.append(admin_id)
                else:
                    logger.info(f"✅ Admin {admin_id} is a member of '{channel_title}'")
            except (TelegramForbiddenError, TelegramNotFound):
                missing_admins.append(admin_id)
                logger.warning(f"⚠️ Cannot check membership for admin {admin_id}")

        if missing_admins:
            logger.warning(
                f"⚠️ The following admins are not members of '{channel_title}':"
            )
            for admin_id in missing_admins:
                logger.warning(f"   - User ID: {admin_id}")
            logger.warning("")
            logger.warning("To invite missing admins:")
            logger.warning(f"1. Create an invite link for '{channel_title}'")
            logger.warning("2. Send the invite link to the missing admins")
            logger.warning("3. Or manually add them if they're in your contacts")

            # Try to create an invite link if bot has permissions
            try:
                invite_link = await self.bot.create_chat_invite_link(channel_id)
                logger.warning(f"📎 Invite link created: {invite_link.invite_link}")
            except (TelegramForbiddenError, TelegramNotFound):
                logger.warning(
                    "❌ Cannot create invite link - insufficient permissions"
                )
        else:
            logger.info(f"✅ All admins are members of '{channel_title}'")
