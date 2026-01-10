# codex_mcp_server/telegram_bot.py
import asyncio
import re
import sys
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters
from .telegram_store import TelegramStore
from .config import Config

class TelegramBot:
    def __init__(self, store: TelegramStore):
        self.store = store
        self.config = Config()
        is_valid, error = self.config.validate()
        if not is_valid:
            raise RuntimeError(error)
        self.app = ApplicationBuilder().token(self.config.telegram_bot_token).build()
        self.app.add_handler(MessageHandler(filters.TEXT, self.on_message))

    async def start(self):
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        await self.app.bot.send_message(
            chat_id=self.config.telegram_chat_id,
            text="✅ Codex MCP Telegram bot online",
        )

    async def on_message(self, update: Update, context):
        user_id = update.effective_user.id
        text = update.message.text.strip()
        if user_id not in self.config.telegram_allowed_user_ids:
            print(
                f"Ignored message from unauthorized user_id={user_id}",
                file=sys.stderr,
                flush=True,
            )
            return

        m = re.match(r"#([a-f0-9]{8})\s+(.+)", text)
        if not m:
            print(
                f"Ignored message with unmatched format: {text!r}",
                file=sys.stderr,
                flush=True,
            )
            return

        req_id, answer = m.groups()
        ok = self.store.answer(req_id, answer)
        if ok:
            print(
                f"Recorded answer for req_id={req_id} from user_id={user_id}",
                file=sys.stderr,
                flush=True,
            )
            await update.message.reply_text(f"✔️ Response recorded for #{req_id}")
        else:
            print(
                f"Unknown or expired req_id={req_id} from user_id={user_id}",
                file=sys.stderr,
                flush=True,
            )
            await update.message.reply_text("❌ Unknown or expired request")

    async def send_prompt(self, req):
        msg = (
            "❓ *MCP Escalation*\n\n"
            f"{req.question}\n\n"
            f"*Context:* {req.context}\n\n"
            f"Reply with:\n`#{req.id} <answer>`"
        )
        await self.app.bot.send_message(
            chat_id=self.config.telegram_chat_id,
            text=msg,
            parse_mode="Markdown",
        )
