from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    discord_token: str
    steam_cc: str = "vn"
    steam_lang: str = "english"
    cache_ttl_seconds: int = 900
    default_limit: int = 10
    metroidvania_tag_id: int = 1628  # Steam tag id

    @staticmethod
    def load() -> "Settings":
        token = os.getenv("DISCORD_TOKEN", "").strip()
        if not token:
            raise RuntimeError("Missing DISCORD_TOKEN")
        return Settings(
            discord_token=token,
            steam_cc=os.getenv("STEAM_CC", "vn"),
            steam_lang=os.getenv("STEAM_LANG", "english"),
            cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "900")),
            default_limit=int(os.getenv("DEFAULT_LIMIT", "10")),
            metroidvania_tag_id=int(os.getenv("METROIDVANIA_TAG_ID", "1628")),
        )