from __future__ import annotations

from src.bot.adapters.inbound.discord_bot import DiscordBot
from src.bot.adapters.inbound.discord_commands import register_commands
from src.bot.infrastructure.logger import setup_logging, get_logger
from src.bot.infrastructure.config import Settings
from src.bot.infrastructure.di import build_container

log = get_logger(__name__)

def main():
    setup_logging()
    settings = Settings.load()
    log.info("Starting bot steam_cc=%s steam_lang=%s cache_ttl=%ss",
             settings.steam_cc, settings.steam_lang, settings.cache_ttl_seconds)

    container = build_container(settings)

    bot = DiscordBot()
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
