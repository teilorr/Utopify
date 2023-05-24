from __future__ import annotations
import typing as t

from discord.ext import commands
from discord import ui
import discord

import datetime as dt
import re

from .utils.markov import MarkovModel
import functools
import random


_T = t.TypeVar("_T")
if t.TYPE_CHECKING:
    from core import Utopify
    from collections.abc import Callable
    from .utils.context import GuildContext

    FuncT = t.TypeVar("FuncT", bound=Callable[["Fun", discord.Message], t.Any])


SILENCE_VOTING_LIMIT: t.Final[int] = 5
SILENCE_VOTING_TIME: t.Final[int] = (1 * 60) * 5
SILENCE_TIMEOUT_TIME: t.Final[int] = (1 * 60) * 5
SILENCE_COOLDOWN_TIME: t.Final[int] = (1 * 60) * 5


def markov_cooldown(
    rate: int,
    per: int,
    type: commands.BucketType = commands.BucketType.guild,
) -> Callable[[FuncT], FuncT]:
    def decorator(func: FuncT) -> FuncT:
        if not hasattr(func, "__cd_mapping__"):
            func.__cd_mapping__ = commands.CooldownMapping.from_cooldown(  # type: ignore
                rate, per, type
            )

        @functools.wraps(func)
        async def wrapper(self: "Fun", message: discord.Message) -> t.Any:
            assert self.bot.user is not None

            bucket: t.Optional[commands.Cooldown] = func.__cd_mapping__.get_bucket(message)  # type: ignore
            if not bucket:
                return

            retry_after = bucket.update_rate_limit()
            if retry_after:
                await message.delete(delay=1.5)
                await message.reply(
                    content=f"> Calma aí, camarada! Estou no cooldown... Tente novamente em `{retry_after:.1f}s`",
                    delete_after=2,
                )
                return

            await func(self, message)

        return wrapper  # type: ignore # lie to get better UX

    return decorator


class SilenceView(ui.View):
    response: t.Optional[discord.Message]
    to_timeout: discord.Member
    voting: t.Set[int]

    def __init__(self, to_timeout: discord.Member) -> None:
        super().__init__(timeout=SILENCE_VOTING_TIME)
        self.to_timeout = to_timeout
        self.voting: t.Set[int] = set()

    @ui.button(
        label="Votar | 0",
        style=discord.ButtonStyle.blurple,
        emoji="\U0001f5f3",
    )
    async def vote(self, interaction: discord.Interaction, button: ui.Button) -> None:
        if button.label is None:
            return

        if not hasattr(self, "response") or self.response is None:
            raise ValueError(
                f"please set `response` to this view ({self}) before someone votes"
            )

        if interaction.user.id in self.voting:
            return await interaction.response.send_message(
                content="> Você já votou",
                ephemeral=True,
            )

        self.voting.add(interaction.user.id)

        count_match = re.search(r"\d+", button.label)
        if count_match is None:
            return

        current_count = int(count_match.group())

        new_label = re.sub(r"\d+", str(current_count + 1), button.label)
        button.label = new_label

        await interaction.response.send_message(
            content="> Computei seu voto com sucesso",
            ephemeral=True,
        )

        if len(self.voting) == SILENCE_VOTING_LIMIT:
            try:
                await self.to_timeout.timeout(
                    dt.timedelta(seconds=SILENCE_TIMEOUT_TIME)
                )
            except discord.Forbidden:
                await interaction.followup.send(
                    content=f"> Não consigo silenciar {self.to_timeout.mention} <:9nerd:1063921036871086121>",
                    allowed_mentions=discord.AllowedMentions(
                        users=False, everyone=False, roles=False, replied_user=False
                    ),
                )
                button.style = discord.ButtonStyle.red
                button.disabled = True
            else:
                button.style = discord.ButtonStyle.green
                button.disabled = True

                await interaction.followup.send(
                    f"> {self.to_timeout.mention} foi silenciado com sucesso <:9nerd:1063921036871086121>"
                )

        await self.response.edit(view=self)

    async def on_timeout(self) -> None:
        if not hasattr(self, "response") or self.response is None:
            raise ValueError(
                f"please set `response` before this view ({self}) timeouts."
            )

        for child in self.children:
            if not isinstance(child, discord.Button):
                continue

            child.style = discord.ButtonStyle.red
            child.disabled = True

        await self.response.edit(view=self)


class Fun(commands.Cog, name="Diversão"):
    """Comandos de diversão"""

    def __init__(self, bot: Utopify) -> None:
        self._message_markov_cooldown: int = 0
        self.bot: Utopify = bot

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{ROLLING ON THE FLOOR LAUGHING}")

    @commands.command(
        name="xiu",
        aliases=("silencio", "silêncio"),
        help="Silencia um usuário através da votação popular",
    )
    @commands.cooldown(1, SILENCE_COOLDOWN_TIME, commands.BucketType.guild)
    @commands.guild_only()
    async def xiu(self, ctx: GuildContext, member: discord.Member) -> None:
        if member.is_timed_out():
            await ctx.reply(
                content=f"> calma aí camarada, {member.mention} já tá silenciado <:9Deboche:953085981878280242>",
                allowed_mentions=discord.AllowedMentions(
                    users=False, everyone=False, roles=False, replied_user=False
                ),
            )
            if ctx.command:
                ctx.command.reset_cooldown(ctx)

            return

        embed = discord.Embed(
            title="Para de fazer merda, irmão",
            color=self.bot.profile_color,
        )

        embed_description: str = (
            f"Utópicos, uni-vos! {ctx.author.mention} "
            f"iniciou uma votação para silenciar {member.mention} por 5 minutos. "
            f"Precisamos de 5 votos para que a votação seja concluída. "
            f"Vocês têm 5 minutos para votar"
        )
        embed.add_field(name="Que comece a loucura!", value=embed_description)

        view = SilenceView(to_timeout=member)
        msg = await ctx.send(
            f"> {member.mention} fica frio ae <:9Deboche:953085981878280242>",
            view=view,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(
                users=False,
                roles=False,
                everyone=False,
            ),
        )
        view.response = msg

    @commands.command(name="gay", help="Mostra o quão homosexual você é")
    async def gay(
        self,
        ctx: GuildContext,
        member: t.Optional[discord.Member] = None,
    ) -> None:
        await ctx.send(f"> *{member or ctx.author}* é `{random.randint(0, 100)}%` gay")

    @commands.command(name="8ball", help="O Que a bola mágica tem pra te dizer?")
    async def eight_ball(
        self,
        ctx: GuildContext,
        *,
        question: t.Optional[str] = None,
    ) -> None:
        answers = [
            # Positive
            "Certamente",
            "Com certeza sim",
            "Sem dúvidas!",
            "Definitivamente sim",
            "Pode ter certeza que sim",
            "Da forma que eu vejo a situação, sim",
            "Provavelmente sim",
            "Sim",
            "Sinais me dizem que sim"
            # Neutral
            "O futuro é nebuloso",
            "Me pergunte novamente mais tarde...",
            "Melhor não te falar agora",
            "Não consigo prever isso agora",
            "Se concetre e pergunte novamente"
            # Negative
            "Não conte com isso",
            "Minha resposta é não",
            "Minhas fontes dizem que não",
            "Claro que não!",
            "Eu tenho minhas dúvidas",
        ]
        answer = random.choice(answers)
        await ctx.reply(f"> {answer}")

    @markov_cooldown(1, 5)
    async def markov_by_mention(self, message: discord.Message) -> None:
        model = MarkovModel()
        n_words = random.randint(6, 12)

        msg = await model.generate_text(message.clean_content, n_words)
        await message.reply(
            content=msg,
            allowed_mentions=discord.AllowedMentions(
                users=False,
                roles=False,
                everyone=False,
            ),
        )

    async def markov_by_cooldown(self, message: discord.Message) -> None:
        model = MarkovModel()
        n_words = random.randint(6, 12)

        msg = await model.generate_text(message.clean_content, n_words)
        await message.reply(
            content=msg,
            allowed_mentions=discord.AllowedMentions(
                users=False,
                roles=False,
                everyone=False,
            ),
        )

    async def markov_learn(self, message: discord.Message) -> None:
        assert self.bot.user is not None
        assert message.guild is not None

        if message.is_system():
            return

        if message.author.bot:
            return

        prefix = await self.bot.get_prefix(message)
        prefix = tuple(prefix) if isinstance(prefix, list) else prefix

        if message.content.startswith(prefix):
            return

        content = message.content.replace(f"<@{self.bot.user.id}>", "").lower()

        model = MarkovModel()
        await model.store_message(content)

    @commands.Cog.listener(name="on_message")
    async def _manage_markov(self, message: discord.Message) -> None:
        assert self.bot.user is not None
        if message.author.bot:
            return

        GELADEIRA_ID = 794453931412684820
        if message.channel.id != GELADEIRA_ID:
            return

        await self.markov_learn(message)

        COOLDOWN_LIMIT = 52
        self._message_markov_cooldown += 1
        if self._message_markov_cooldown >= COOLDOWN_LIMIT:
            self._message_markov_cooldown = 0
            return await self.markov_by_cooldown(message)

        if self.bot.user.mentioned_in(message):
            return await self.markov_by_mention(message)


async def setup(bot: Utopify) -> None:
    await bot.add_cog(Fun(bot))
