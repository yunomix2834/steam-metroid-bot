from __future__ import annotations

from src.bot.application.ports import DealsProvider, DealsQuery
from src.bot.adapters.outbound.http_client import HttpClient
from src.bot.adapters.outbound.steam_parser import parse_search_response, parse_deals_from_html
from src.bot.infrastructure.logger import get_logger

log = get_logger(__name__)

STEAM_SEARCH_URL = "https://store.steampowered.com/search/results/"

class SteamStoreDealsProvider(DealsProvider):
    def __init__(self, http: HttpClient):
        self._http = http

    async def fetch_deals(self, q: DealsQuery):
        params = {
            "query": "",
            "start": 0,
            "count": min(max(q.limit, 10), 50),
            "infinite": 1,
            "specials": 1 if q.only_discounted else 0,
            "tags": ",".join(str(t) for t in q.tag_ids),
            "cc": q.country_code,
            "l": q.language,
        }

        log.info("Steam fetch cc=%s lang=%s tags=%s limit=%s", q.country_code, q.language, q.tag_ids, q.limit)
        raw = await self._http.get_text(STEAM_SEARCH_URL, params=params)
        html = parse_search_response(raw)
        deals = parse_deals_from_html(html)
        log.info("Steam parsed deals=%d", len(deals))
        return deals[: q.limit]
