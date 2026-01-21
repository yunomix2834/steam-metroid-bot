from __future__ import annotations
from src.bot.infrastructure.config import Settings
from src.bot.infrastructure.cache_memory import MemoryCache
from src.bot.adapters.outbound.http_client import HttpClient
from src.bot.adapters.outbound.steam_store_provider import SteamStoreDealsProvider
from src.bot.application.use_cases import GetDealsUseCase


def build_container(settings: Settings):
    cache = MemoryCache()
    http = HttpClient(user_agent="DiscordSteamDealsBot/1.0")
    provider = SteamStoreDealsProvider(http=http, concurrency=8)
    uc = GetDealsUseCase(provider=provider, cache=cache, cache_ttl_seconds=settings.cache_ttl_seconds)
    return {
        "cache": cache,
        "http": http,
        "provider": provider,
        "get_deals_uc": uc,
    }
