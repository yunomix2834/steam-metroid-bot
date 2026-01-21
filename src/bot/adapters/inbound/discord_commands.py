from __future__ import annotations

import discord
from discord import app_commands

from src.bot.application.ports import DealsQuery
from src.bot.application.use_cases import GetDealsUseCase
from src.bot.infrastructure.logger import get_logger

log = get_logger(__name__)

MAX_EMBEDS_PER_MESSAGE = 10

def chunk_list(items, size):
    for i in range(0, len(items), size):
        yield items[i:i+size]

def build_deal_embed(deal) -> discord.Embed:
    embed = discord.Embed(
        title=f"{deal.name} (-{deal.discount_pct}%)",
        url=deal.url,
        color=discord.Color.green(),
    )

    # HIỂN THỊ ẢNH (to rõ)
    if deal.image_url:
        embed.set_image(url=deal.image_url)      # ảnh lớn
        # embed.set_thumbnail(url=deal.image_url) # nếu bạn thích thumbnail thì dùng dòng này thay vì set_image

    if deal.price_original:
        embed.add_field(name="Giá gốc", value=deal.price_original, inline=True)
    embed.add_field(name="Giá giảm", value=deal.price_final or "N/A", inline=True)
    embed.add_field(name="% giảm", value=f"{deal.discount_pct}%", inline=True)

    return embed

async def send_deals_embeds(send_func, deals):
    # Discord giới hạn 10 embeds / message → chia chunk
    for chunk in chunk_list(deals, MAX_EMBEDS_PER_MESSAGE):
        embeds = [build_deal_embed(d) for d in chunk]
        await send_func(embeds=embeds)

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
            deals = list(await uc.execute(q))
        except Exception as e:
            log.exception("Fetch deals failed: %s", e)
            await interaction.followup.send(f"Lỗi fetch: `{type(e).__name__}: {e}`")
            return

        # Đảm bảo: không 0% và sort
        deals = [d for d in deals if d.discount_pct > 0]
        deals.sort(key=lambda d: d.discount_pct, reverse=True)

        if not deals:
            log.warning("No deals returned for query=%s", q)
            await interaction.followup.send("Không thấy deal nào (hoặc Steam đổi format).")
            return

        log.info("Returned %d deals", len(deals))

        await send_deals_embeds(interaction.followup.send, deals)
