#!/usr/bin/env python3
"""Minimal script to call telegram_notify_and_wait over MCP stdio."""

import argparse
import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters, stdio_client


async def run(question: str, timeout_sec: int) -> int:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "codex_mcp_server.server"],
        env=os.environ.copy(),
    )
    async with stdio_client(server_params) as (read_stream, write_stream):
        session = ClientSession(read_stream, write_stream)
        await session.initialize()
        result = await session.call_tool(
            "telegram_notify_and_wait",
            {"question": question, "timeout_sec": timeout_sec},
        )
        payload = None
        if result.content:
            payload = result.content[0].text
        output = {"raw": payload, "is_error": result.isError}
        print(json.dumps(output, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Test telegram_notify_and_wait MCP tool.")
    parser.add_argument("question", help="Question to send over Telegram")
    parser.add_argument("--timeout-sec", type=int, default=1800)
    args = parser.parse_args()
    return asyncio.run(run(args.question, args.timeout_sec))


if __name__ == "__main__":
    raise SystemExit(main())
