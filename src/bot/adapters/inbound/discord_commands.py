from __future__ import annotations

import discord
from discord import app_commands

from src.bot.application.ports import DealsQuery
from src.bot.application.use_cases import GetDealsUseCase
from src.bot.infrastructure.logger import get_logger

log = get_logger(__name__)

def build_deals_embed(title: str, deals):
    embed = discord.Embed(title=title, color=discord.Color.green())
    for d in deals:
        price = d.price_final if not d.price_original else f"{d.price_original} → {d.price_final}"
        embed.add_field(
            name=f"-{d.discount_pct}% • {d.name}",
            value=f"{price}\n{d.url}",
            inline=False,
        )
    return embed

def register_commands(tree: app_commands.CommandTree, uc: GetDealsUseCase,
                      steam_cc: str, steam_lang: str, tag_metroidvania: int, default_limit: int):

    @tree.command(name="deals_metroidvania", description="Lấy game Metroidvania đang giảm giá trên Steam")
    @app_commands.describe(limit="Số lượng deal (1-20)")
    async def deals_metroidvania(interaction: discord.Interaction, limit: int = default_limit):
        limit = max(1, min(limit, 20))

        log.info("Command /deals_metroidvania user=%s guild=%s limit=%s",
                 interaction.user, getattr(interaction.guild, "id", None), limit)

        await interaction.response.defer(thinking=True)

        q = DealsQuery(
            tag_ids=[tag_metroidvania],
            only_discounted=True,
            limit=limit,
            country_code=steam_cc,
            language=steam_lang,
        )

        try:
            deals = await uc.execute(q)
        except Exception as e:
            log.exception("Fetch deals failed: %s", e)
            await interaction.followup.send(f"Lỗi fetch: `{type(e).__name__}: {e}`")
            return

        if not deals:
            log.warning("No deals returned for query=%s", q)
            await interaction.followup.send("Không thấy deal nào (hoặc Steam đổi format).")
            return

        log.info("Returned %d deals", len(deals))
        embed = build_deals_embed("Steam Metroidvania Deals", deals)
        await interaction.followup.send(embed=embed)
