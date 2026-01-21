from __future__ import annotations

import asyncio
from typing import Any, Optional
import aiohttp

from src.bot.infrastructure.logger import get_logger
log = get_logger(__name__)

class HttpClient:
    def __init__(self, user_agent: str, timeout_seconds: int = 20):
        self._headers = {
            "User-Agent": user_agent,
            "Accept": "application/json,text/plain,*/*",
        }
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    async def get_text(self, url: str, params: Optional[dict[str, Any]] = None) -> str:
        backoff = 0.5
        last_err: Exception | None = None

        for attempt in range(1, 5):
            try:
                log.debug("HTTP GET attempt=%d url=%s params=%s", attempt, url, params)
                async with aiohttp.ClientSession(headers=self._headers, timeout=self._timeout) as session:
                    async with session.get(url, params=params) as resp:
                        text = await resp.text()
                        log.debug("HTTP %s status=%d bytes=%d", url, resp.status, len(text))
                        resp.raise_for_status()
                        return text
            except Exception as e:
                last_err = e
                log.warning("HTTP GET failed attempt=%d err=%s", attempt, f"{type(e).__name__}: {e}")
                if attempt == 4:
                    break
                await asyncio.sleep(backoff)
                backoff *= 2

        assert last_err is not None
        raise last_err
