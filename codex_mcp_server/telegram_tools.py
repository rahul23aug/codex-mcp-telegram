# codex_mcp_server/telegram_tools.py
from .telegram_store import TelegramStore
from .telegram_bot import TelegramBot
from .config import Config
import asyncio
class TelegramTools:
    def __init__(self, store: TelegramStore, bot: TelegramBot):
        self.store = store
        self.bot = bot
        self.config = Config()

    async def telegram_notify_and_wait(self, question: str, context: str = ""):
        '''replaces polling which is a pain'''
        req = self.store.create(question, context, self.config.command_timeout)
        await self.bot.send_prompt(req)

        # BLOCK until answered or expired
        while True:
            await asyncio.sleep(1)
            req2 = self.store.get(req.id)
            if not req2:
                return {"status": "expired"}
            if req2.answer:
                return {"answer": req2.answer}
            if req2.expired:
                return {"status": "expired"}

    async def telegram_poll(self, correlation_id: str):
        req = self.store.get(correlation_id)
        #being depricated
        if not req:
            return {"status": "unknown"}
        if req.answer:
            return {"status": "answered", "answer": req.answer}
        if req.expired:
            return {"status": "expired"}
        return {"status": "pending"}


