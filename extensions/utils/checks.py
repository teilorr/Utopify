from __future__ import annotations
import typing as t

from discord.ext import commands
import discord

if t.TYPE_CHECKING:
    from discord.ext.commands._types import Check
    from core import Utopify

class NotStaff(commands.CheckFailure):
    """Exception raised when the user is not a staff member

    This inherits from :exc:`CheckFailure`
    """

    pass


def is_staff() -> Check[t.Any]:
    async def predicate(ctx: commands.Context[Utopify]) -> bool:
        if isinstance(ctx.author, discord.User):
            raise commands.NoPrivateMessage()

        if not ctx.bot.is_staff(ctx.author):
            raise NotStaff("You are not a staff member")
        return True

    return commands.check(predicate)