from __future__ import annotations

from src.bot.adapters.inbound.discord_bot import DiscordBot
from src.bot.adapters.inbound.discord_commands import register_commands
from src.bot.infrastructure.logger import setup_logging, get_logger
from src.bot.infrastructure.config import Settings
from src.bot.infrastructure.di import build_container
from src.bot.infrastructure.scheduler import DailyDealsScheduler

log = get_logger(__name__)

def main():
    setup_logging()
    settings = Settings.load()
    log.info("Starting bot steam_cc=%s steam_lang=%s cache_ttl=%ss",
             settings.steam_cc, settings.steam_lang, settings.cache_ttl_seconds)

    container = build_container(settings)

    bot = DiscordBot()

    # Attach scheduler
    bot.deals_scheduler = DailyDealsScheduler(
        container["get_deals_uc"],
        steam_cc=settings.steam_cc,
        steam_lang=settings.steam_lang,
        tag_metroidvania=settings.metroidvania_tag_id,
        channel_id=settings.deals_channel_id,
        tz_name=settings.schedule_tz,
        limit=settings.daily_post_limit,
    )

    # (Optional) attach http for close
    bot.http_client = container["http"]  # type: ignore

    register_commands(
        tree=bot.tree,
        uc=container["get_deals_uc"],
        steam_cc=settings.steam_cc,
        steam_lang=settings.steam_lang,
        tag_metroidvania=settings.metroidvania_tag_id,
        default_limit=settings.default_limit,
    )

    bot.run(settings.discord_token)

if __name__ == "__main__":
    main()
