# src/bot/adapters/inbound/discount_bot.py
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

    async def on_ready(self):
        log.info("Bot logged in as %s (id=%s)", self.user, getattr(self.user, "id", None))
