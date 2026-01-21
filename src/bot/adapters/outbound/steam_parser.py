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
    m = re.search(r"-\s*(\d+)\s*%", text)
    return int(m.group(1)) if m else 0


def parse_search_response(raw_text: str) -> str:
    try:
        data = json.loads(raw_text)
        html = data.get("results_html", "") or ""
        return html if html else raw_text
    except json.JSONDecodeError:
        return raw_text


def _parse_price(price_div) -> tuple[Optional[str], str]:
    if not price_div:
        return None, ""

    parts = [s.strip() for s in price_div.stripped_strings if s.strip()]
    if not parts:
        return None, ""

    joined = " ".join(parts)
    if "Free" in joined:
        return None, "Free To Play"

    # Thường discounted sẽ có 2 giá: [original, final]
    if len(parts) >= 2:
        return parts[0], parts[-1]

    # Không discounted: chỉ 1 giá
    return None, parts[0]


def _parse_image_url(row) -> Optional[str]:
    img = row.select_one("div.search_capsule img")
    if not img:
        return None
    # Steam đôi lúc dùng data-src
    return img.get("src") or img.get("data-src")


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

        price_div = a.select_one("div.search_price")
        price_original, price_final = _parse_price(price_div)

        image_url = _parse_image_url(a)

        if discount_pct <= 0:
            continue

        deals.append(
            Deal(
                appid=appid,
                name=name,
                discount_pct=discount_pct,
                price_final=_clean(price_final),
                price_original=_clean(price_original) if price_original else None,
                url=STEAM_APP_URL.format(appid=appid),
                image_url=image_url,
            )
        )

    # Sort theo % giảm từ cao xuống thấp
    deals.sort(key=lambda d: d.discount_pct, reverse=True)
    return deals


def extract_appids_from_html(html: str) -> list[int]:
    soup = BeautifulSoup(html, "html.parser")
    appids: list[int] = []

    for a in soup.select("a.search_result_row"):
        appid_raw = a.get("data-ds-appid") or ""
        appid_str = appid_raw.split(",")[0].strip()
        if appid_str.isdigit():
            appids.append(int(appid_str))

    # giữ thứ tự nhưng loại trùng
    seen = set()
    out = []
    for x in appids:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out