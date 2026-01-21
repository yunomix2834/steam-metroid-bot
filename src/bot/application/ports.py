from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Optional, Sequence
from src.bot.domain.models import Deal

@dataclass(frozen=True)
class DealsQuery:
    tag_ids: Sequence[int]
    only_discounted: bool = True
    limit: int = 10
    country_code: str = "vn"
    language: str = "english"

class DealsProvider(Protocol):
    async def fetch_deals(self, q: DealsQuery) -> Sequence[Deal]:
        ...

class Cache(Protocol):
    async def get(self, key: str) -> Optional[object]:
        ...

    async def set(self, key: str, value: object, ttl_seconds: int) -> None:
        ...