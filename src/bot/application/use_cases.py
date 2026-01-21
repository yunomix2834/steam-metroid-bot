from __future__ import annotations

import json
from typing import Sequence

from src.bot.application.ports import DealsProvider, DealsQuery, Cache
from src.bot.domain.models import Deal
from src.bot.infrastructure.logger import get_logger

log = get_logger(__name__)

class GetDealsUseCase:
    def __init__(self, provider: DealsProvider, cache: Cache, cache_ttl_seconds: int = 900):
        self._provider = provider
        self._cache = cache
        self._ttl = cache_ttl_seconds

    def _cache_key(self, q: DealsQuery) -> str:
        payload = {
            "tag_ids": list(q.tag_ids),
            "only_discounted": q.only_discounted,
            "limit": q.limit,
            "cc": q.country_code,
            "lang": q.language,
        }
        return "deals:" + json.dumps(payload, sort_keys=True)

    async def execute(self, q: DealsQuery) -> Sequence[Deal]:
        key = self._cache_key(q)
        cached = await self._cache.get(key)
        if isinstance(cached, list) and all(isinstance(x, Deal) for x in cached):
            log.debug("Cache HIT key=%s items=%d", key, len(cached))
            return cached

        log.debug("Cache MISS key=%s", key)
        deals = await self._provider.fetch_deals(q)
        await self._cache.set(key, deals, ttl_seconds=self._ttl)
        log.debug("Cache SET key=%s ttl=%ds items=%d", key, self._ttl, len(deals))
        return deals
