from __future__ import annotations

import asyncio
from typing import Optional

from src.bot.application.ports import DealsProvider, DealsQuery
from src.bot.adapters.outbound.http_client import HttpClient
from src.bot.adapters.outbound.steam_parser import parse_search_response, extract_appids_from_html
from src.bot.domain.models import Deal
from src.bot.infrastructure.logger import get_logger

log = get_logger(__name__)

STEAM_SEARCH_URL = "https://store.steampowered.com/search/results/"
STEAM_APP_URL = "https://store.steampowered.com/app/{appid}/"
STEAM_APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"


class SteamStoreDealsProvider(DealsProvider):
    def __init__(self, http: HttpClient, *, concurrency: int = 8):
        self._http = http
        self._concurrency = max(1, min(concurrency, 20))

    async def _fetch_one_appdetails(self, appid: int, cc: str, lang: str) -> Optional[Deal]:
        """
        Fetch appdetails for 1 appid and return Deal if discounted (>0%).
        """
        try:
            resp = await self._http.get_json(
                STEAM_APPDETAILS_URL,
                params={
                    "appids": str(appid),
                    "cc": cc,
                    "l": lang,
                    # IMPORTANT: bỏ filters để tránh thiếu name/header_image
                },
            )
        except Exception as e:
            log.debug("appdetails failed appid=%s err=%s", appid, f"{type(e).__name__}: {e}")
            return None

        if not isinstance(resp, dict):
            return None

        node = resp.get(str(appid))
        if not node or not node.get("success"):
            return None

        data = node.get("data") or {}

        # PRICE
        price = data.get("price_overview")
        if not price:
            return None

        discount = int(price.get("discount_percent") or 0)
        if discount <= 0:
            return None

        # NAME + IMAGE
        name = data.get("name") or f"App {appid}"
        img = data.get("header_image") or f"https://cdn.akamai.steamstatic.com/steam/apps/{appid}/header.jpg"

        initial = price.get("initial_formatted") or ""
        final = price.get("final_formatted") or ""

        return Deal(
            appid=appid,
            name=name,
            discount_pct=discount,
            price_original=initial if initial else None,
            price_final=final,
            url=STEAM_APP_URL.format(appid=appid),
            image_url=img,
        )

    async def fetch_deals(self, q: DealsQuery):
        # 1) Search để lấy appids theo tag + specials
        params = {
            "query": "",
            "start": 0,
            "count": 80,  # lấy nhiều để lọc vẫn đủ
            "infinite": 1,
            "specials": 1 if q.only_discounted else 0,
            "tags": ",".join(str(t) for t in q.tag_ids),
            "cc": q.country_code,
            "l": q.language,
        }

        log.info("Steam search fetch cc=%s lang=%s tags=%s", q.country_code, q.language, q.tag_ids)
        raw = await self._http.get_text(STEAM_SEARCH_URL, params=params)
        html = parse_search_response(raw)
        appids = extract_appids_from_html(html)

        log.info("Steam search extracted appids=%d", len(appids))
        if not appids:
            return []

        # 2) Fetch appdetails theo từng appid, concurrency có kiểm soát
        sem = asyncio.Semaphore(self._concurrency)
        deals: list[Deal] = []

        async def worker(appid: int) -> None:
            nonlocal deals
            async with sem:
                d = await self._fetch_one_appdetails(appid, q.country_code, q.language)
                if d:
                    deals.append(d)

        # Dừng sớm khi đã đủ nhiều (lọc + sort)
        # Ta chạy theo "waves": mỗi wave ~ 25 appids, đủ deals thì stop.
        wave_size = 25
        for i in range(0, len(appids), wave_size):
            wave = appids[i:i + wave_size]
            await asyncio.gather(*(worker(a) for a in wave))

            # nếu đã có đủ > limit một chút thì break (để sort đẹp)
            if len(deals) >= max(q.limit, 10):
                break

        # sort theo % giảm
        deals.sort(key=lambda d: d.discount_pct, reverse=True)
        log.info("Steam final deals(after filter)=%d", len(deals))
        return deals[: q.limit]
