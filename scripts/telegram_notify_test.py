#!/usr/bin/env python3
"""Minimal script to call telegram_prompt/telegram_poll over MCP stdio."""

import argparse
import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters, stdio_client


async def run(question: str, timeout_sec: int, poll_interval_sec: int) -> int:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "codex_mcp_server.server"],
        env=os.environ.copy(),
    )
    async with stdio_client(server_params) as (read_stream, write_stream):
        session = ClientSession(read_stream, write_stream)
        await session.initialize()
        prompt_result = await session.call_tool(
            "telegram_prompt",
            {"question": question},
        )
        payload = None
        if prompt_result.content:
            payload = prompt_result.content[0].text
        if not payload:
            print(json.dumps({"error": "empty prompt response", "is_error": prompt_result.isError}))
            return 1
        try:
            prompt_data = json.loads(payload)
        except json.JSONDecodeError:
            print(json.dumps({"error": "prompt response not JSON", "raw": payload}))
            return 1
        correlation_id = prompt_data.get("correlation_id")
        if not correlation_id:
            print(json.dumps({"error": "missing correlation_id", "raw": prompt_data}))
            return 1

        deadline = asyncio.get_event_loop().time() + timeout_sec
        while True:
            poll_result = await session.call_tool(
                "telegram_poll",
                {"correlation_id": correlation_id},
            )
            poll_payload = None
            if poll_result.content:
                poll_payload = poll_result.content[0].text
            if poll_payload:
                try:
                    poll_data = json.loads(poll_payload)
                except json.JSONDecodeError:
                    print(json.dumps({"error": "poll response not JSON", "raw": poll_payload}))
                    return 1
                status = poll_data.get("status")
                if status in {"answered", "expired", "unknown"}:
                    output = {
                        "correlation_id": correlation_id,
                        "status": status,
                        "answer": poll_data.get("answer"),
                    }
                    print(json.dumps(output, indent=2))
                    return 0

            if asyncio.get_event_loop().time() >= deadline:
                print(
                    json.dumps(
                        {
                            "correlation_id": correlation_id,
                            "status": "timeout",
                            "answer": None,
                        },
                        indent=2,
                    )
                )
                return 1
            await asyncio.sleep(poll_interval_sec)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test telegram_prompt/telegram_poll MCP tools."
    )
    parser.add_argument("question", help="Question to send over Telegram")
    parser.add_argument("--timeout-sec", type=int, default=1800)
    parser.add_argument("--poll-interval-sec", type=int, default=3)
    args = parser.parse_args()
    return asyncio.run(run(args.question, args.timeout_sec, args.poll_interval_sec))


if __name__ == "__main__":
    raise SystemExit(main())
