# codex_mcp_server/telegram_tools.py
from .telegram_store import TelegramStore
from .telegram_bot import TelegramBot
from .config import COMMAND_TIMEOUT

class TelegramTools:
    def __init__(self, store: TelegramStore, bot: TelegramBot):
        self.store = store
        self.bot = bot

    async def telegram_prompt(self, question: str, context: str = ""):
        req = self.store.create(question, context, COMMAND_TIMEOUT)
        await self.bot.send_prompt(req)
        return {"correlation_id": req.id}

    async def telegram_poll(self, correlation_id: str):
        req = self.store.get(correlation_id)
        if not req:
            return {"status": "unknown"}
        if req.answer:
            return {"status": "answered", "answer": req.answer}
        if req.expired:
            return {"status": "expired"}
        return {"status": "pending"}