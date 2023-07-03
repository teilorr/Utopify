"""Cog blank"""
from __future__ import annotations

from discord.ext.commands import Cog, Context, command

from bot.ext.bot import Bot


class BlankTest(Cog):
    """Cog blank"""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        """Hook blank"""
        self.bot.logger.info(msg="Cog blank carregado com sucesso!")
        return None

    @command(name="blank")
    async def blank(self, ctx: Context) -> None:
        """Command blank"""
        await ctx.send(content="Blank!")
        return None


async def setup(bot: Bot) -> None:
    """Setup binding"""
    await bot.add_cog(BlankTest(bot=bot))
