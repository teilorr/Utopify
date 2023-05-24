from __future__ import annotations
import typing as t

from discord.ext import commands
from discord.ext import menus
import discord

import datetime as dt
import re

from dataclasses import dataclass
from uuid import uuid1


from .utils.database import Database, DataType
from .utils.paginator import UtopiafyPages
from .utils.checks import is_staff

if t.TYPE_CHECKING:
    from core import Utopify
    from datetime import datetime
    from sqlite3 import Row

    from .utils.context import GuildContext

WARNINGS_SCHEMA = {
    "user_id": DataType.INTEGER,
    "author_id": DataType.INTEGER,
    "warn_id": DataType.INTEGER,
    "reason": DataType.TEXT,
    "timestamp": DataType.DATETIME_NOW,
}


class WarningsSource(menus.ListPageSource):
    def __init__(
        self,
        entries: list[WarningPayload],
        *,
        per_page: int = 6,
        ctx: GuildContext[Utopify],
    ) -> None:
        self.ctx: GuildContext[Utopify] = ctx
        super().__init__(entries, per_page=per_page)

    async def format_page(
        self,
        menu: UtopiafyPages,
        entries: list[WarningPayload],
    ) -> discord.Embed:
        guild = self.ctx.guild
        embed = discord.Embed(
            title=f"Warns - {menu.current_page + 1}/{self.get_max_pages()}",
            color=discord.Color.orange(),
        )

        embed.add_field(
            name=f"*Mostrando `{len(entries)}` warns*",
            value="\n".join(
                [
                    f"*`ID: {warn.warn_id}`* - "
                    f"*{warn.reason} - "
                    f"{discord.utils.format_dt(warn.timestamp, 'd')}"
                    f"({discord.utils.format_dt(warn.timestamp, 'R')}) "
                    f"Autor: {(await self.ctx.bot.fetch_or_get_member(guild, warn.author_id)).mention}*"
                    for warn in entries
                ]
            ),
        )

        return embed


@dataclass(frozen=True)
class WarningPayload:
    __slots__ = ("user_id", "author_id", "warn_id", "reason", "timestamp")

    user_id: int
    author_id: int
    warn_id: int
    reason: str
    timestamp: datetime

    @classmethod
    def from_row(cls, row: Row) -> t.Self:
        return cls(
            user_id=row[0],
            author_id=row[1],
            warn_id=row[2],
            reason=row[3],
            timestamp=row[4],
        )


class Seconds(commands.Converter):
    _value: int
    _original: str

    @property
    def value(self) -> int:
        """The time in seconds"""
        return self._value

    @property
    def original(self) -> str:
        """The original inputed time, e.g: `5m`"""
        return self._original

    async def convert(self, ctx: commands.Context, argument: str) -> t.Self:
        units = {
            "s": 1,
            "m": 60,
            "h": 60 * 60,
            "d": 60 * 60 * 24,
            "mo": 60 * 60 * 24 * 30,
        }

        match = re.match(r"^(\d+)(s|m(?:o)?|h|d)$", argument)
        if not match:
            raise commands.BadArgument(f"`{argument}` não é um tempo válido")

        value, unit = match.groups()
        value = int(value)

        if unit in units:
            self._value = value * units.get(unit)  # type: ignore
            self._original = argument
            return self

        raise commands.BadArgument(f"`{unit}` não é uma unidade de tempo válida")


class BannedMember(commands.Converter):
    async def convert(self, ctx: GuildContext, argument: str) -> discord.BanEntry:
        argument = re.sub(r"[<>@]", "", argument)

        if argument.isdigit():
            member_id = int(argument, base=10)
            try:
                return await ctx.guild.fetch_ban(discord.Object(id=member_id))
            except discord.NotFound:
                raise commands.BadArgument(
                    "This member has not been banned before"
                ) from None

        entity = await discord.utils.find(
            lambda u: str(u.user) == argument, ctx.guild.bans(limit=None)
        )

        if entity is None:
            raise commands.BadArgument("This member has not been banned before.")
        return entity


class Mod(commands.Cog, name="Moderação"):
    """Comandos de moderação"""

    _report_channel: discord.TextChannel
    _logs_channel: discord.TextChannel

    def __init__(self, bot: Utopify) -> None:
        self.bot = bot

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{CROSSED SWORDS}")

    async def cog_load(self) -> None:
        REPORT_CHANNELID = 794456061230841876
        self._report_channel = await self.bot.fetch_channel(REPORT_CHANNELID)  # type: ignore

        LOGS_CHANNELID = 794456444681715713
        self._logs_channel = await self.bot.fetch_channel(LOGS_CHANNELID)  # type: ignore

    @commands.command(
        name="user_info",
        aliases=("userinfo",),
        help="Mostra informações de um usuário",
    )
    @commands.guild_only()
    async def user_info(
        self, ctx: GuildContext, member: t.Optional[discord.Member] = None
    ) -> None:
        member = ctx.author if member is None else member
        if member is None:
            return

        if member.joined_at is None:
            return

        db = Database("warns", columns=WARNINGS_SCHEMA)
        async with db:
            warns_count = await db.count("*").where(user_id=ctx.author.id).execute()

        joined_at_formated = discord.utils.format_dt(member.joined_at)
        created_at_formated = discord.utils.format_dt(member.created_at)
        joined_at_formated_relative = discord.utils.format_dt(member.joined_at, "R")
        created_at_formated_relative = discord.utils.format_dt(member.created_at, "R")

        embed = discord.Embed(
            title=f"Informações sobre {member}",
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name=f"\U0001f530 `Apelido`",
            value=f"***{member.nick or 'Nenhum'}***",
            inline=True,
        )
        embed.add_field(
            name=f"\U0001f4e1 `ID`",
            value=f"***{member.id}***",
            inline=True,
        )
        embed.add_field(
            name=f"\U0001f4c5 `Criação da conta`",
            value=f"{created_at_formated} / {created_at_formated_relative}",
            inline=False,
        )
        embed.add_field(
            name=f"\U00002728 `Entrou no servidor`",
            value=f"{joined_at_formated} / {joined_at_formated_relative}",
            inline=False,
        )
        embed.add_field(
            name=f"\U0001f4f8 `Maior cargo`",
            value=f"{member.top_role.mention}",
            inline=True,
        )
        embed.add_field(
            name=f"\U0001f4e2 `Quantidade de warns`",
            value=f"{warns_count} Avisos",
            inline=True,
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        await ctx.reply(embed=embed)

    @commands.command(name="report", help="Reporta um usuário a staff")
    async def report(
        self,
        ctx: GuildContext,
        member: discord.Member,
        *,
        reason: str,
    ) -> None:
        embed = discord.Embed(
            color=discord.Color(0x00000),
            description=(
                f"***\N{RIGHT-POINTING MAGNIFYING GLASS} Reportado***: {member.mention} *({member.id})*\n"
                f"***\N{SCROLL} Motivo***: [Ver mensagem]({ctx.message.jump_url})\n"
                f"***\\\N{NUMBER SIGN} Canal***: {ctx.channel.mention}\n"
            ),
        )

        embed.add_field(name="Motivo", value=f"```{reason}```")
        embed.set_author(name=f"Autor do report: {ctx.author.name} ({ctx.author.id})")
        msg = await self._report_channel.send(embed=embed)
        async with ctx.typing():
            await msg.add_reaction("\N{LARGE GREEN SQUARE}")
            await msg.add_reaction("\N{LARGE ORANGE SQUARE}")
            await msg.add_reaction("\N{LARGE RED SQUARE}")
            await msg.add_reaction("\N{WHITE MEDIUM SQUARE}")
            await msg.add_reaction("\N{WASTEBASKET}")

        await ctx.send(f"> Reportei *{member.display_name}* com sucesso!")

    @commands.Cog.listener(name="on_raw_reaction_add")
    async def update_report_embed(
        self, payload: discord.RawReactionActionEvent
    ) -> None:
        assert self.bot.user is not None
        if payload.user_id == self.bot.user.id:
            return

        if payload.channel_id != self._report_channel.id:
            return

        msg = await self._report_channel.fetch_message(payload.message_id)
        if len(msg.embeds) != 1:
            return

        if payload.emoji.name == "\N{WASTEBASKET}":
            await msg.delete()
            return

        embed = msg.embeds[0]
        embed.color = {
            "\N{LARGE GREEN SQUARE}": discord.Color.green(),
            "\N{LARGE ORANGE SQUARE}": discord.Color.orange(),
            "\N{LARGE RED SQUARE}": discord.Color.red(),
            "\N{WHITE MEDIUM SQUARE}": discord.Color(0xFFFFF),
        }.get(payload.emoji.name)

        try:
            await msg.edit(embed=embed)
            await msg.clear_reactions()
        except discord.HTTPException:
            pass

    @commands.command(name="mute", help="Silencia um usuário")
    @is_staff()
    async def mute(
        self,
        ctx: GuildContext,
        member: discord.Member,
        time: Seconds,
        *,
        reason: str = "Motivo não informado",
    ) -> None:
        if member.is_timed_out():
            await ctx.send(f"> O membro `{member}` já está silenciado")
            return

        until = dt.timedelta(seconds=time.value)
        await member.timeout(until, reason=f"{reason} | Author: {ctx.author}")
        await ctx.send(f"> Silenciei *{member}* com sucesso! :tada:")

        embed = discord.Embed(
            color=discord.Color.red(),
            description=(
                f"***\N{SPEAKER WITH CANCELLATION STROKE} Silenciado***: {member.mention} *({member.id})*\n"
                f"***\N{CROWN} Admin***: {ctx.author} *({ctx.author.id})*\n"
                f"***\N{ALARM CLOCK} Tempo***: {time.original}\n"
            ),
        )
        embed.add_field(name="Motivo", value=f"```{reason}```")
        embed.set_author(name=f"{member.name} foi silenciado(a) por {ctx.author.name}")
        await self._logs_channel.send(embed=embed)

    @commands.command(name="unmute", help="Desmuta um usuário")
    @is_staff()
    async def unmute(
        self,
        ctx: GuildContext,
        member: discord.Member,
        *,
        reason: str = "Motivo não informado",
    ) -> None:
        if not member.is_timed_out():
            await ctx.send(f"> O membro `{member}` não está silenciado")
            return

        await member.timeout(None, reason=f"{reason} | Author: {ctx.author}")
        await ctx.send(f"> Desmutei *{member}* com sucesso! :tada:")

        embed = discord.Embed(
            color=discord.Color.brand_green(),
            description=(
                f"***\N{SPEAKER WITH CANCELLATION STROKE} Desmutado***: {member} *({member.id})*\n"
                f"***\N{CROWN} Admin***: {ctx.author} *({ctx.author.id})*\n"
            ),
        )
        embed.add_field(name="Motivo", value=f"```{reason}```")
        embed.set_author(name=f"{member.name} foi desmutado por {ctx.author.name}")
        await self._logs_channel.send(embed=embed)

    @commands.command(name="warn", help="Adiciona um warn ao usuário")
    @is_staff()
    async def warn(
        self,
        ctx: GuildContext,
        member: discord.Member,
        *,
        reason: str = "Motivo não informado",
    ) -> None:
        db = Database("warns", columns=WARNINGS_SCHEMA)
        warn_id = hash(str(uuid1())) % 100000000

        async with db:
            await db.insert(
                user_id=member.id,
                author_id=ctx.author.id,
                warn_id=warn_id,
                reason=reason,
            )

        embed = discord.Embed(
            color=discord.Color.orange(),
            description=(
                f"***\N{SPEAKER WITH CANCELLATION STROKE} Avisado***: {member.mention} ({member.id})\n"
                f"***\N{CROWN} Admin***: {ctx.author.mention} *({ctx.author.id})*\n"
                f"***\N{SCROLL} Motivo***: [Ver mensagem]({ctx.message.jump_url})\n"
                f"***\N{INPUT SYMBOL FOR NUMBERS} ID Do warn***: {warn_id}"
            ),
        )
        embed.add_field(name="Motivo", value=f"```{reason}```")
        embed.set_author(
            name=f"{member.display_name} foi avisado por {ctx.author.display_name}"
        )

        await self._logs_channel.send(embed=embed)
        await ctx.reply(f"> *{member}* foi avisado.", embed=embed, delete_after=10)

    @commands.command(
        name="remove_warn",
        aliases=("unwarn",),
        help="Remove o warn de um usuário",
    )
    @is_staff()
    async def remove_warn(self, ctx: GuildContext, warn_id: int) -> None:
        db = Database("warns", columns=WARNINGS_SCHEMA)
        async with db:
            removed_raw = await db.select("*").where(warn_id=warn_id).execute()

            if not removed_raw:
                await ctx.send(f"> Nenhum warn com o id *{warn_id}* foi encontrado")
                return

            if len(removed_raw) > 1:
                await ctx.send(
                    f"> De alguma forma esse warn existe em 2 ou mais usuários... A Remoção foi pausada, por favor informe o desenvolvedor para prosseguir."
                )
                return

            removed = WarningPayload.from_row(removed_raw[0])
            await db.delete_where(warn_id=warn_id).execute()

        author = await ctx.guild.fetch_member(removed.author_id)
        member = await ctx.guild.fetch_member(removed.user_id)

        embed = discord.Embed(
            color=discord.Color.magenta(),
            description=(
                f"***\N{SPEAKER WITH CANCELLATION STROKE} desavisado***: {member.mention} ({member.id})\n"
                f"***\N{CROWN} Admin***: {author.mention} *({author.id})*\n"
                f"***\N{SCROLL} Motivo***: [Ver mensagem]({ctx.message.jump_url})\n"
                f"***\N{INPUT SYMBOL FOR NUMBERS} ID Do warn***: {warn_id}"
            ),
        )
        embed.set_author(name=f"{member.display_name} foi desavisado.")

        await self._logs_channel.send(embed=embed)
        await ctx.reply(f"> *{member}* foi desavisado.", embed=embed, delete_after=10)

    @commands.command(
        name="warns",
        aliases=("warnings",),
        help="Mostra os warns de um usuário",
    )
    async def warns(self, ctx: GuildContext, member: discord.Member) -> None:
        db = Database("warns", columns=WARNINGS_SCHEMA)
        async with db:
            warns_raw = await db.select("*").where(user_id=member.id).execute()
            if not warns_raw:
                await ctx.send(f"> O Usuário *{member}* não tem nenhum warn!")
                return

            warns = [WarningPayload.from_row(row) for row in warns_raw]

        pages = UtopiafyPages(WarningsSource(warns, ctx=ctx), ctx=ctx)
        await pages.start()

    @commands.command(name="ban", help="Bane um usuário permanentemente")
    @is_staff()
    async def ban(
        self,
        ctx: GuildContext,
        member: discord.Member,
        *,
        reason: str = "Motivo não informado",
    ) -> None:
        await member.ban(reason=reason + f" | Author: {ctx.author}")

        embed = discord.Embed(
            description=(
                f"***\N{SKULL} Banido***: {member} *({member.id})*\n"
                f"***\N{CROWN} Admin***: {ctx.author}\n"
                f"***\N{SCROLL} Motivo***: [Ver mensagem]({ctx.message.jump_url})"
            ),
            color=discord.Color.red(),
        )
        embed.add_field(name="Motivo", value=f"```{reason}```")

        await self._logs_channel.send(embed=embed)
        await ctx.reply(
            f"> Bani *{member}* com sucesso :tada:! Lembre-se de reportar atividades esquisitas que quebram as regras usando *==report [member]*"
        )

    @commands.command(name="unban", help="Desbane um usuário do servidor")
    @is_staff()
    async def unban(
        self,
        ctx: GuildContext,
        member: t.Annotated[discord.BanEntry, BannedMember],
        *,
        reason: str = "Motivo não informado",
    ) -> None:
        await ctx.guild.unban(member.user, reason=f"{reason} | Author: {ctx.author}")

        embed = discord.Embed(
            description=(
                f"***\N{SKULL} Desbanido***: {member.user} *({member.user.id})*\n"
                f"***\N{CROWN} Admin***: {ctx.author} *({ctx.author.id})*\n"
                f"***\N{SCROLL} Motivo***: [Ver mensagem]({ctx.message.jump_url})"
            ),
            color=discord.Color.green(),
        )
        embed.add_field(name="Motivo", value=f"```{reason}```")
        await self._logs_channel.send(embed=embed)

        if member.reason:
            await ctx.reply(
                f"Desbani o membro *{member.user}*, banido anteriormante pelo seguinte motivo: `{member.reason}`"
            )
        else:
            await ctx.reply(f"Desbani o membro *{member.user}* com sucesso")

    @commands.command(name="kick", help="Explusa um servidor do servidor")
    @is_staff()
    async def kick(
        self,
        ctx: GuildContext,
        member: discord.Member,
        *,
        reason: str = "Motivo não informado",
    ) -> None:
        await ctx.guild.kick(member, reason=f"{reason} | Author: {ctx.author}")

        embed = discord.Embed(
            description=(
                f"***\N{SKULL} Banido***: {member} *({member.id})*\n"
                f"***\N{CROWN} Admin***: {ctx.author} *({ctx.author.id})*\n"
                f"***\N{SCROLL} Motivo***: [Ver mensagem]({ctx.message.jump_url})"
            ),
            color=discord.Color.red(),
        )
        embed.add_field(name="Motivo", value=f"```{reason}```")

        await self._logs_channel.send(embed=embed)
        await ctx.reply(f"> Explusei o membro *{member}* com sucesso!")


async def setup(bot: Utopify) -> None:
    await bot.add_cog(Mod(bot))
