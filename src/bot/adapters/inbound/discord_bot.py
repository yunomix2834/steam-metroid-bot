from __future__ import annotations

import os
import discord
from discord import app_commands

from src.bot.infrastructure.logger import get_logger

log = get_logger(__name__)

class DiscordBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.deals_scheduler = None  # gán từ main.py

    async def setup_hook(self):
        guild_id = os.getenv("DISCORD_GUILD_ID", "").strip()

        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            log.info("Synced %d commands to guild_id=%s", len(synced), guild_id)
        else:
            synced = await self.tree.sync()
            log.info("Synced %d global commands", len(synced))

        # Start scheduler (nếu có)
        if self.deals_scheduler is not None:
            self.deals_scheduler.start(self)

    async def close(self):
        # close http session if exists
        http = getattr(self, "http_client", None)
        if http is not None:
            try:
                await http.close()
            except Exception:
                pass
        await super().close()

    async def on_ready(self):
        log.info("Bot logged in as %s (id=%s)", self.user, getattr(self.user, "id", None))
