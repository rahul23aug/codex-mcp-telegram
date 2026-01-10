"""Telegram bot integration for remote Codex CLI access."""

import asyncio
import logging
import re
from typing import Optional

try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logging.warning("python-telegram-bot not installed. Telegram integration will be disabled.")

from .config import Config
from .codex_executor import CodexExecutor

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot for remote Codex CLI command execution."""
    
    def __init__(self, config: Config, mcp_server):
        """
        Initialize Telegram bot.
        
        Args:
            config: Configuration instance
            mcp_server: MCP server instance for tool execution
        """
        if not TELEGRAM_AVAILABLE:
            raise ImportError("python-telegram-bot is not installed. Install it with: pip install python-telegram-bot")
        
        if not config.telegram_enabled:
            raise ValueError("Telegram is not enabled in configuration")
        
        self.config = config
        self.mcp_server = mcp_server
        self.executor = CodexExecutor()
        
        # Initialize Telegram application
        self.application = Application.builder().token(config.telegram_bot_token).build()
        
        # Register handlers
        self.application.add_handler(CommandHandler("start", self._handle_start))
        self.application.add_handler(CommandHandler("help", self._handle_help))
        self.application.add_handler(CommandHandler("status", self._handle_status))
        self.application.add_handler(CommandHandler("exec", self._handle_exec))
        self.application.add_handler(CommandHandler("review", self._handle_review))
        # Handle plain messages as exec commands for convenience
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self._handle_message
        ))
    
    def _is_authorized(self, user_id: int, message_text: str) -> tuple[bool, Optional[str]]:
        """
        Check if user is authorized to execute commands.
        
        Args:
            user_id: Telegram user ID
            message_text: Message text (may contain auth token)
        
        Returns:
            Tuple of (is_authorized, error_message)
        """
        # Check if user ID is in allowed list (highest priority)
        if self.config.telegram_allowed_user_ids and user_id in self.config.telegram_allowed_user_ids:
            return True, None
        
        # Check if chat_id matches (single user mode)
        if self.config.telegram_chat_id:
            try:
                chat_id_int = int(self.config.telegram_chat_id)
                if user_id == chat_id_int:
                    return True, None
            except (ValueError, TypeError):
                pass
        
        # Check for auth token in message (if auth token is configured)
        if self.config.telegram_auth_token:
            if self.config.telegram_auth_token in message_text:
                return True, None
            else:
                return False, "Unauthorized. Include your auth token in the message or contact admin."
        
        # No authorization method configured
        return False, "Unauthorized. Contact admin for access."
    
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user_id = update.effective_user.id
        
        authorized, error = self._is_authorized(user_id, "")
        if not authorized:
            await update.message.reply_text(
                f"❌ {error}\n\n"
                f"Your User ID: {user_id}\n"
                "Share this with the admin to get access."
            )
            return
        
        welcome_msg = (
            "🤖 *Codex MCP Server*\n\n"
            "Available commands:\n"
            "• `/exec <prompt>` - Execute Codex command\n"
            "• `/review <path>` - Review code\n"
            "• `/status` - Check Codex CLI status\n"
            "• `/help` - Show this help\n\n"
            "You can also send plain messages - they'll be executed as Codex commands."
        )
        await update.message.reply_text(welcome_msg, parse_mode='Markdown')
    
    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        user_id = update.effective_user.id
        authorized, error = self._is_authorized(user_id, "")
        
        if not authorized:
            await update.message.reply_text(f"❌ {error}")
            return
        
        help_text = (
            "📚 *Codex MCP Server Help*\n\n"
            "*Commands:*\n"
            "• `/exec <prompt>` - Execute a Codex CLI command\n"
            "  Example: `/exec write a Python hello world`\n\n"
            "• `/review <file_or_dir>` - Review code\n"
            "  Example: `/review /path/to/file.py`\n\n"
            "• `/status` - Check if Codex CLI is available\n\n"
            "• `/help` - Show this help message\n\n"
            "You can also send plain text messages - they'll be treated as `/exec` commands."
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        user_id = update.effective_user.id
        authorized, error = self._is_authorized(user_id, "")
        
        if not authorized:
            await update.message.reply_text(f"❌ {error}")
            return
        
        await update.message.reply_text("⏳ Checking Codex CLI status...")
        
        status = await self.executor.check_status()
        await update.message.reply_text(f"✅ {status}")
    
    async def _handle_exec(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /exec command."""
        user_id = update.effective_user.id
        message_text = update.message.text or ""
        
        authorized, error = self._is_authorized(user_id, message_text)
        if not authorized:
            await update.message.reply_text(f"❌ {error}")
            return
        
        # Extract prompt from command
        prompt = message_text.replace("/exec", "").strip()
        if not prompt:
            await update.message.reply_text("❌ Please provide a prompt. Usage: `/exec <prompt>`", parse_mode='Markdown')
            return
        
        if len(prompt) > self.config.max_command_length:
            await update.message.reply_text(f"❌ Command too long (max {self.config.max_command_length} chars)")
            return
        
        # Remove auth token if present (remove token and any surrounding whitespace)
        if self.config.telegram_auth_token and self.config.telegram_auth_token in prompt:
            import re
            # Remove token with optional surrounding whitespace
            prompt = re.sub(rf'\s*{re.escape(self.config.telegram_auth_token)}\s*', ' ', prompt).strip()
        
        await update.message.reply_text(f"⏳ Executing: `{prompt[:50]}...`", parse_mode='Markdown')
        
        try:
            model = self.config.codex_default_model if self.config.codex_default_model else None
            result = await self.executor.execute(prompt, model=model, timeout=self.config.command_timeout)
            
            # Telegram has a 4096 character limit per message
            if len(result) > 4000:
                # Send in chunks
                chunks = [result[i:i+4000] for i in range(0, len(result), 4000)]
                for i, chunk in enumerate(chunks):
                    await update.message.reply_text(
                        f"📤 Result (part {i+1}/{len(chunks)}):\n```\n{chunk}\n```",
                        parse_mode='Markdown'
                    )
            else:
                await update.message.reply_text(f"✅ Result:\n```\n{result}\n```", parse_mode='Markdown')
        
        except Exception as e:
            logger.error(f"Error executing command via Telegram: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def _handle_review(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /review command."""
        user_id = update.effective_user.id
        message_text = update.message.text or ""
        
        authorized, error = self._is_authorized(user_id, message_text)
        if not authorized:
            await update.message.reply_text(f"❌ {error}")
            return
        
        # Extract target path from command
        target = message_text.replace("/review", "").strip()
        if not target:
            await update.message.reply_text("❌ Please provide a file/directory path. Usage: `/review <path>`", parse_mode='Markdown')
            return
        
        await update.message.reply_text(f"⏳ Reviewing: `{target}`", parse_mode='Markdown')
        
        try:
            result = await self.executor.review(target, timeout=self.config.command_timeout)
            
            if len(result) > 4000:
                chunks = [result[i:i+4000] for i in range(0, len(result), 4000)]
                for i, chunk in enumerate(chunks):
                    await update.message.reply_text(
                        f"📤 Review (part {i+1}/{len(chunks)}):\n```\n{chunk}\n```",
                        parse_mode='Markdown'
                    )
            else:
                await update.message.reply_text(f"✅ Review:\n```\n{result}\n```", parse_mode='Markdown')
        
        except Exception as e:
            logger.error(f"Error executing review via Telegram: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle plain text messages as exec commands."""
        # Only process if it's not a command
        if update.message.text and update.message.text.startswith('/'):
            return
        
        # Treat as exec command
        await self._handle_exec(update, context)
    
    async def start(self):
        """Start the Telegram bot."""
        logger.info("Starting Telegram bot...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(drop_pending_updates=True)
        logger.info("Telegram bot is running and polling for updates")
    
    async def stop(self):
        """Stop the Telegram bot."""
        logger.info("Stopping Telegram bot...")
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()
