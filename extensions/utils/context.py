from __future__ import annotations
import typing as t

from discord.ext.commands._types import BotT

from discord.ext import commands
import discord

if t.TYPE_CHECKING:
    from core import Utopify

class Context(commands.Context["Utopify"]):
    async def send(
        self,
        content: t.Optional[str] = None,
        *,
        embed: t.Optional[discord.Embed] = None,
        **attrs: object,
    ) -> discord.Message:
        if embed is not None and embed.colour is None:
            embed.colour = self.bot.profile_color

        return await super().send(content, embed=embed, **attrs)

class GuildContext(commands.Context, t.Generic[BotT]):
    bot: BotT
    author: discord.Member
    guild: discord.Guild
    channel: t.Union[discord.VoiceChannel, discord.TextChannel, discord.Thread]
    me: discord.Member
    prefix: str
