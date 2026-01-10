# codex_mcp_server/telegram_store.py
import time
import uuid
from typing import Dict, Optional

class PendingRequest:
    def __init__(self, question: str, context: str, ttl: int):
        self.id = uuid.uuid4().hex[:8]
        self.question = question
        self.context = context
        self.created_at = time.time()
        self.ttl = ttl
        self.answer: Optional[str] = None

    @property
    def expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl


class TelegramStore:
    def __init__(self):
        self._pending: Dict[str, PendingRequest] = {}

    def create(self, question: str, context: str, ttl: int) -> PendingRequest:
        req = PendingRequest(question, context, ttl)
        self._pending[req.id] = req
        return req

    def answer(self, req_id: str, text: str) -> bool:
        req = self._pending.get(req_id)
        if not req or req.expired:
            return False
        req.answer = text
        return True

    def get(self, req_id: str) -> Optional[PendingRequest]:
        return self._pending.get(req_id)

    def cleanup(self):
        for k in list(self._pending.keys()):
            if self._pending[k].expired:
                del self._pending[k]