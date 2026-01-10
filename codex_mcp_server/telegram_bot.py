# codex_mcp_server/telegram_bot.py
import asyncio
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters
from .telegram_store import TelegramStore
from .config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TELEGRAM_ALLOWED_USER_IDS,
)

class TelegramBot:
    def __init__(self, store: TelegramStore):
        self.store = store
        self.app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        self.app.add_handler(MessageHandler(filters.TEXT, self.on_message))

    async def start(self):
        await self.app.initialize()
        await self.app.start()
        await self.app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text="✅ Codex MCP Telegram bot online",
        )

    async def on_message(self, update: Update, context):
        if update.effective_user.id not in TELEGRAM_ALLOWED_USER_IDS:
            return

        text = update.message.text.strip()
        m = re.match(r"#([a-f0-9]{8})\s+(.+)", text)
        if not m:
            return

        req_id, answer = m.groups()
        ok = self.store.answer(req_id, answer)
        if ok:
            await update.message.reply_text(f"✔️ Response recorded for #{req_id}")
        else:
            await update.message.reply_text("❌ Unknown or expired request")

    async def send_prompt(self, req):
        msg = (
            "❓ *MCP Escalation*\n\n"
            f"{req.question}\n\n"
            f"*Context:* {req.context}\n\n"
            f"Reply with:\n`#{req.id} <answer>`"
        )
        await self.app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=msg,
            parse_mode="Markdown",
        )