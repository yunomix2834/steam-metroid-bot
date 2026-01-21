from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import discord
from discord.ext import tasks

from src.bot.application.ports import DealsQuery
from src.bot.application.use_cases import GetDealsUseCase
from src.bot.infrastructure.logger import get_logger
from src.bot.adapters.inbound.discord_commands import send_deals_embeds  # reuse

log = get_logger(__name__)


class DailyDealsScheduler:
    """
    Run every minute and post once per day at 06:00 (local tz).
    This avoids discord.ext.tasks 'time=' limitations and is restart-safe.
    """

    def __init__(
        self,
        uc: GetDealsUseCase,
        *,
        steam_cc: str,
        steam_lang: str,
        tag_metroidvania: int,
        channel_id: int | None,
        tz_name: str,
        limit: int = 10,
        hour: int = 6,
        minute: int = 0,
    ):
        self._uc = uc
        self._steam_cc = steam_cc
        self._steam_lang = steam_lang
        self._tag = tag_metroidvania
        self._channel_id = channel_id
        try:
            self._tz = ZoneInfo(tz_name)
        except ZoneInfoNotFoundError:
            # Fallback: VN fixed UTC+7 (no DST)
            self._tz = dt.timezone(dt.timedelta(hours=7))
            log.warning("ZoneInfo '%s' not found. Falling back to UTC+07:00 fixed offset. Install 'tzdata' to fix.",
                        tz_name)

        self._limit = max(1, min(limit, 20))
        self._target_hour = hour
        self._target_minute = minute

        self._bot: discord.Client | None = None
        self._last_post_date: dt.date | None = None

    def start(self, bot: discord.Client) -> None:
        self._bot = bot
        if not self._channel_id:
            log.warning("DISCORD_DEALS_CHANNEL_ID not set -> daily scheduler disabled")
            return
        if not self._ticker.is_running():
            self._ticker.start()
            log.info(
                "Daily scheduler started: target=%02d:%02d tz=%s channel_id=%s",
                self._target_hour, self._target_minute, self._tz.key, self._channel_id
            )

    @tasks.loop(minutes=1)
    async def _ticker(self):
        assert self._bot is not None

        now = dt.datetime.now(self._tz)
        today = now.date()

        # Already posted today -> do nothing
        if self._last_post_date == today:
            return

        # Only post at exactly target minute
        if not (now.hour == self._target_hour and now.minute == self._target_minute):
            return

        assert self._channel_id is not None

        q = DealsQuery(
            tag_ids=[self._tag],
            only_discounted=True,
            limit=self._limit,
            country_code=self._steam_cc,
            language=self._steam_lang,
        )

        try:
            deals = list(await self._uc.execute(q))
            deals = [d for d in deals if d.discount_pct > 0]
            deals.sort(key=lambda d: d.discount_pct, reverse=True)
        except Exception as e:
            log.exception("Daily fetch failed: %s", e)
            return

        if not deals:
            log.info("Daily post: no deals today")
            self._last_post_date = today  # still mark to prevent retry spam
            return

        # Resolve channel
        channel = self._bot.get_channel(self._channel_id)
        if channel is None:
            try:
                channel = await self._bot.fetch_channel(self._channel_id)
            except Exception as e:
                log.exception("Cannot fetch channel_id=%s err=%s", self._channel_id, e)
                return

        if not isinstance(channel, (discord.TextChannel, discord.Thread, discord.DMChannel)):
            log.warning("Channel_id=%s is not a text channel", self._channel_id)
            return

        log.info("Daily posting %d deals to channel_id=%s", len(deals), self._channel_id)
        await send_deals_embeds(channel.send, deals)

        # Mark posted for today
        self._last_post_date = today

    @_ticker.before_loop
    async def _before_ticker(self):
        assert self._bot is not None
        await self._bot.wait_until_ready()
