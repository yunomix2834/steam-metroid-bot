from __future__ import annotations
import json
import re
from typing import Optional
from bs4 import BeautifulSoup
from src.bot.domain.models import Deal

STEAM_APP_URL = "https://store.steampowered.com/app/{appid}/"


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _try_parse_discount(text: str) -> int:
    m = re.search(r"-\s*(\d+)%", text)
    return int(m.group(1)) if m else 0


def parse_search_response(raw_text: str) -> str:
    """
    Steam search sometimes returns JSON with "results_html",
    sometimes returns full HTML.
    Return HTML snippet that contains <a class="search_result_row">...
    """
    try:
        data = json.loads(raw_text)
        html = data.get("results_html", "") or ""
        return html if html else raw_text
    except json.JSONDecodeError:
        return raw_text


def parse_deals_from_html(html: str) -> list[Deal]:
    soup = BeautifulSoup(html, "html.parser")
    deals: list[Deal] = []

    for a in soup.select("a.search_result_row"):
        appid_raw = a.get("data-ds-appid") or ""
        appid_str = appid_raw.split(",")[0].strip()
        if not appid_str.isdigit():
            continue
        appid = int(appid_str)

        title_el = a.select_one("span.title")
        if not title_el:
            continue
        name = title_el.get_text(strip=True)

        disc_el = a.select_one("div.search_discount span")
        discount_pct = _try_parse_discount(disc_el.get_text(strip=True)) if disc_el else 0

        price_el = a.select_one("div.search_price")
        price_text = _clean(price_el.get_text(" ", strip=True)) if price_el else ""
        price_original: Optional[str] = None
        price_final = price_text

        # Heuristic for VN prices; you can improve later
        if "Free" in price_text:
            price_final = "Free To Play"
        else:
            chunks = re.findall(r"(₫\s*[\d\.,]+)", price_text)
            if len(chunks) >= 2:
                price_original = chunks[0]
                price_final = chunks[-1]

        deals.append(
            Deal(
                appid=appid,
                name=name,
                discount_pct=discount_pct,
                price_final=price_final,
                price_original=price_original,
                url=STEAM_APP_URL.format(appid=appid),
            )
        )

    deals.sort(key=lambda d: d.discount_pct, reverse=True)
    return deals
