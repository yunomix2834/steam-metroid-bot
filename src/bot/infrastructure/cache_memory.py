from __future__ import annotations
import time
from typing import Optional

class MemoryCache:
    def __init__(self):
        self._store: dict[str, tuple[float, object]] = {}

    async def get(self, key: str) -> Optional[object]:
        item = self._store.get(key)
        if not item:
            return None
        expires_at, value = item
        if time.time() > expires_at:
            self._store.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: object, ttl_seconds: int) -> None:
        self._store[key] = (time.time() + ttl_seconds, value)