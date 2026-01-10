# codex_mcp_server/server.py
import asyncio
import sys
import json
from .telegram_store import TelegramStore
from .telegram_bot import TelegramBot
from .telegram_tools import TelegramTools

class MCPServer:
    def __init__(self):
        self.store = TelegramStore()
        self.bot = TelegramBot(self.store)
        self.tools = TelegramTools(self.store, self.bot)

    async def start(self):
        await self.bot.start()
        while True:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            req = json.loads(line)
            method = req["method"]
            params = req.get("params", {})

            if method == "telegram_prompt":
                result = await self.tools.telegram_prompt(**params)
            elif method == "telegram_poll":
                result = await self.tools.telegram_poll(**params)
            else:
                result = {"error": "unknown method"}

            sys.stdout.write(json.dumps({"result": result}) + "\n")
            sys.stdout.flush()

async def main():
    server = MCPServer()
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())