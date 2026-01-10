"""Telegram bridge for MCP tool-driven human escalation."""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from typing import Optional

from telegram import Bot, Update

logger = logging.getLogger(__name__)


class TelegramBridge:
    """Background polling bridge that waits for human responses."""

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        allowed_user_ids: set[int],
        poll_timeout_sec: int = 30,
    ) -> None:
        self.bot = Bot(token=bot_token)
        self.chat_id = self._parse_chat_id(chat_id)
        self.allowed_user_ids = allowed_user_ids
        self.poll_timeout_sec = poll_timeout_sec
        self._pending: dict[str, asyncio.Future[str]] = {}
        self._pending_lock = asyncio.Lock()
        self._polling_task: Optional[asyncio.Task] = None
        self._last_update_id: Optional[int] = None

    async def start(self) -> None:
        """Start the background polling task."""
        if self._polling_task:
            return
        self._polling_task = asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        """Stop the background polling task."""
        if not self._polling_task:
            return
        self._polling_task.cancel()
        try:
            await self._polling_task
        except asyncio.CancelledError:
            pass
        self._polling_task = None

    async def ask_and_wait(
        self,
        question: str,
        timeout_sec: int = 1800,
        context: str = "",
    ) -> dict[str, Optional[str]]:
        """Send a question to Telegram and wait for a reply."""
        correlation_id = uuid.uuid4().hex
        future = asyncio.get_running_loop().create_future()
        async with self._pending_lock:
            self._pending[correlation_id] = future

        message = self._format_prompt(question, correlation_id, context)
        await self.bot.send_message(chat_id=self.chat_id, text=message)

        try:
            answer = await asyncio.wait_for(future, timeout=timeout_sec)
            return {"answer": answer, "correlation_id": correlation_id}
        except asyncio.TimeoutError:
            await self._cleanup_pending(correlation_id)
            return {
                "answer": None,
                "correlation_id": correlation_id,
                "error": f"Timed out after {timeout_sec} seconds waiting for response",
            }

    async def _poll_loop(self) -> None:
        """Continuously poll Telegram for updates and resolve pending prompts."""
        while True:
            try:
                updates = await self.bot.get_updates(
                    offset=self._last_update_id,
                    timeout=self.poll_timeout_sec,
                )
                for update in updates:
                    await self._handle_update(update)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Telegram polling error: %s", exc, exc_info=True)
                await asyncio.sleep(1)

    async def _handle_update(self, update: Update) -> None:
        """Handle a single Telegram update."""
        self._last_update_id = update.update_id + 1
        if not update.message or not update.message.text:
            return
        if not update.message.from_user:
            return
        if update.message.from_user.id not in self.allowed_user_ids:
            return

        match = re.match(r"^#(?P<correlation_id>\S+)\s+(?P<answer>.+)$", update.message.text, re.DOTALL)
        if not match:
            return

        correlation_id = match.group("correlation_id")
        answer = match.group("answer").strip()
        if not answer:
            return

        async with self._pending_lock:
            future = self._pending.pop(correlation_id, None)
        if future and not future.done():
            future.set_result(answer)

    async def _cleanup_pending(self, correlation_id: str) -> None:
        async with self._pending_lock:
            future = self._pending.pop(correlation_id, None)
        if future and not future.done():
            future.cancel()

    @staticmethod
    def _parse_chat_id(chat_id: str) -> str | int:
        try:
            return int(chat_id)
        except (TypeError, ValueError):
            return chat_id

    @staticmethod
    def _format_prompt(question: str, correlation_id: str, context: str) -> str:
        prompt_lines = [
            "❓ MCP Escalation",
            "",
            question,
            "",
        ]
        if context:
            prompt_lines.extend(["Context:", context, ""])
        prompt_lines.append(f"Reply with #{correlation_id} <answer>")
        return "\n".join(prompt_lines)
