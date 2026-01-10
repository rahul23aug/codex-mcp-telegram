# codex_mcp_server/server.py
import asyncio
import sys
import json

from mcp.types import LATEST_PROTOCOL_VERSION

from . import __version__
from .telegram_store import TelegramStore
from .telegram_bot import TelegramBot
from .telegram_tools import TelegramTools

class MCPServer:
    def __init__(self):
        self.store = TelegramStore()
        self.bot = TelegramBot(self.store)
        self.tools = TelegramTools(self.store, self.bot)
        self.bot_task: asyncio.Task | None = None

    async def _handle_initialize(self) -> dict:
        return {
            "protocolVersion": LATEST_PROTOCOL_VERSION,
            "capabilities": {
                "tools": {},
            },
            "serverInfo": {
                "name": "codex-mcp-telegram",
                "version": __version__,
            },
            "instructions": "Use tools/list to discover tools, then tools/call to invoke them.",
        }

    async def _handle_tools_list(self) -> dict:
        return {
            "tools": [
                {
                    "name": "telegram_notify_and_wait",
                    "description": "Send a Telegram message and block until the human replies or the request expires.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string"},
                            "context": {"type": "string"},
                        },
                        "required": ["question"],
                        "additionalProperties": False,
                    },
                },
                # {
                #     "name": "telegram_prompt",
                #     "description": "Send a prompt via Telegram and return a correlation id.",
                #     "inputSchema": {
                #         "type": "object",
                #         "properties": {
                #             "question": {"type": "string"},
                #             "context": {"type": "string"},
                #         },
                #         "required": ["question"],
                #         "additionalProperties": False,
                #     },
                # },
                {
                    "name": "telegram_poll",
                    "description": "Poll for a Telegram response by correlation id.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "correlation_id": {"type": "string"},
                        },
                        "required": ["correlation_id"],
                        "additionalProperties": False,
                    },
                },
            ]
        }
    async def _ensure_bot_started(self) -> tuple[bool, str | None]:
        if self.bot_task is None:
            self.bot_task = asyncio.create_task(self.bot.start())
        try:
            await asyncio.wait_for(self.bot_task, timeout=10)
        except asyncio.TimeoutError:
            return False, "telegram bot startup timed out"
        except Exception as exc:
            return False, f"telegram bot startup failed: {exc}"
        return True, None

    async def _handle_tools_call(self, params: dict) -> dict:
        name = params.get("name")
        arguments = params.get("arguments") or {}

        ok, error = await self._ensure_bot_started()
        if not ok:
            return {
                "content": [{"type": "text", "text": json.dumps({"error": error})}],
                "structuredContent": {"error": error},
                "isError": True,
            }

        if name == "telegram_notify_and_wait":
            result = await self.tools.telegram_notify_and_wait(
                arguments["question"],
                arguments.get("context", "")
            )
        elif name == "telegram_poll":
            result = await self.tools.telegram_poll(**arguments)
        else:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({"error": f"unknown tool: {name}"}),
                    }
                ],
                "structuredContent": {"error": f"unknown tool: {name}"},
                "isError": True,
            }

        return {
            "content": [{"type": "text", "text": json.dumps(result)}],
            "structuredContent": result,
            "isError": False,
        }

    def _write_response(self, response: dict) -> None:
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()

    async def start(self):
        if self.bot_task is None:
            self.bot_task = asyncio.create_task(self.bot.start())
        while True:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            if not line.strip():
                continue
            try:
                req = json.loads(line)
            except json.JSONDecodeError:
                self._write_response(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": "parse error"},
                    }
                )
                continue

            method = req.get("method")
            params = req.get("params", {}) or {}
            req_id = req.get("id")

            if req_id is None:
                if method == "initialized":
                    continue
                continue

            try:
                if method == "initialize":
                    result = await self._handle_initialize()
                elif method == "tools/list":
                    result = await self._handle_tools_list()
                elif method == "tools/call":
                    result = await self._handle_tools_call(params)
                else:
                    self._write_response(
                        {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "error": {"code": -32601, "message": "method not found"},
                        }
                    )
                    continue
                self._write_response({"jsonrpc": "2.0", "id": req_id, "result": result})
            except Exception as exc:
                self._write_response(
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32603, "message": f"internal error: {exc}"},
                    }
                )

async def main():
    server = MCPServer()
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())
