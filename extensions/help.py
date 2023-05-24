from __future__ import annotations
import typing as t

from discord.ext import commands
from discord.ext import menus
from discord import ui
import discord

from .utils.paginator import UtopiafyPages
from difflib import get_close_matches

if t.TYPE_CHECKING:
    from core import Utopify


VIEW_TIMEOUT: t.Final[int] = (1 * 60) * 5


class CogHelpPageSource(menus.ListPageSource):
    def __init__(self, cog: commands.Cog, entries: t.List[commands.Command]) -> None:
        super().__init__(entries=entries, per_page=6)
        self.cog = cog
        self.title = f"Comandos de {cog.qualified_name}"
        self.description = cog.description

    async def format_page(
        self, menu: UtopiafyPages, commands: t.List[commands.Command]
    ):
        embed = discord.Embed(
            title=self.title,
            description=self.description,
            color=self.cog.bot.profile_color,  # type: ignore
        )

        for command in commands:
            sig = f"{command.qualified_name} {command.signature}"
            embed.add_field(
                name=sig, value=command.help or "Comando não documentado", inline=False
            )

        maximum = self.get_max_pages()
        if maximum > 1:
            embed.set_author(
                name=f"Página {menu.current_page + 1}/{maximum} ({len(self.entries)} comandos)"
            )

        return embed


class FrontPageSource(menus.PageSource):
    def is_paginating(self) -> t.Literal[True]:
        return True

    def get_max_pages(self) -> t.Literal[2]:
        return 2

    async def get_page(self, page_number: int) -> t.Self:
        self.index = page_number
        return self

    def format_page(self, menu: HelpMenu, page: t.Any):
        embed_desc: t.Tuple[str, ...] = (
            "E aí! Bem-vindo à página de ajuda\n",
            f"Use `{menu.ctx.clean_prefix}help [comando]` para mais informações sobre um comando.",
            f"Use `{menu.ctx.clean_prefix}help [categoria]` para mais informações sobre uma categoria.",
            "Use o menu abaixo para selecionar uma categoria.",
        )

        embed = discord.Embed(
            title="Ajuda",
            description="\n".join(embed_desc),
            color=menu.ctx.bot.profile_color,
        )

        if self.index == 0:
            aboutme: str = (
                "Eu sou um bot criado por *teilo#3809* especialmente para a comunidade do Cazum8. "
                "Meu objetivo é proporcionar diversão para todos vocês, utopiers :-)"
            )
            embed.add_field(name="Quem é você?", value=aboutme)

        elif self.index == 1:
            entries = (
                (
                    "<argumento>",
                    "Isso quer dizer que o argumento é __**obrigatório**__",
                ),
                ("[argumento]", "Isso quer dizer que o argumento é __**opcional**__"),
                ("[A|B]", "Isso quer dizer que o argumento pode ser __**A ou B**__"),
                (
                    "[argumento...]",
                    "Isso quer dizer que você pode ter vários argumentos.\n"
                    "Agora que você sabe do básico, note que...\n"
                    "__**Você não precisa digitar as chaves! e.g [], <> etc...**__",
                ),
            )
            embed.add_field(
                name="Como eu uso o bot?",
                value='Entender a "signature" do bot é bem simples',
            )
            for name, value in entries:
                embed.add_field(name=name, value=value, inline=False)

        return embed


class SelectCategory(ui.Select["HelpMenu"]):
    def __init__(
        self,
        help: "PaginatedHelp",
        cogs: t.Iterable[t.Optional[commands.Cog]],
    ) -> None:
        super().__init__(
            placeholder="Selecione uma categoria...",
            min_values=1,
            max_values=1,
            row=0,
        )
        self.help: "PaginatedHelp" = help
        self.cogs: t.Iterable[t.Optional[commands.Cog]] = cogs
        self._fill_options()

    def _fill_options(self) -> None:
        self.add_option(
            label="Home",
            emoji="\U0001f3e0",
            value="_index",
            description="O Index da página de help",
        )
        for cog in self.cogs:
            if not cog:
                continue

            if hasattr(cog, "hidden"):
                continue

            desc = cog.description.split("\n", 1)[0] or None
            emoji = getattr(cog, "display_emoji", None)
            self.add_option(
                label=cog.qualified_name,
                description=desc,
                emoji=emoji,
            )

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        selected = self.values[0]
        if selected == "_index":
            await self.view.rebind(FrontPageSource(), interaction)
            return

        cog: t.Optional[commands.Cog] = self.view.ctx.bot.get_cog(selected)
        if cog is None:
            await interaction.response.send_message(
                "De alguma forma essa categoria não existe?", ephemeral=True
            )
            return

        cmds = cog.get_commands()
        entries = await self.help.filter_commands(cmds)

        if not entries:
            await interaction.response.send_message(
                "Você não pode usar nenhum comando dessa categoria", ephemeral=True
            )
            return

        source = CogHelpPageSource(cog, entries)
        await self.view.rebind(source, interaction)


class HelpMenu(UtopiafyPages):
    def add_categories(
        self, help: "PaginatedHelp", cogs: t.Iterable[t.Optional[commands.Cog]]
    ) -> None:
        self.clear_items()
        self.add_item(SelectCategory(help, cogs))
        self.fill_items()

    async def rebind(
        self, source: menus.PageSource, interaction: discord.Interaction
    ) -> None:
        self.source = source
        self.current_page = 0

        await self.source._prepare_once()
        page = await self.source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        self._update_labels(0)
        await interaction.response.edit_message(**kwargs, view=self)


class PaginatedHelp(commands.HelpCommand):
    if t.TYPE_CHECKING:
        context: commands.Context[Utopify]

    def command_not_found(self, string: str) -> str:
        cmds = (cmd.name for cmd in self.context.bot.commands)
        matches = get_close_matches(string, cmds)

        if not matches:
            return f"Nenhum comando chamado `{string}` foi encontrado"

        closest = ""
        for match in matches:
            closest += f"- `{self.context.clean_prefix}{match}`\n"

        return f"Nenhum comando chamado `{string}` foi encontrado, talvez você queria dizer:\n {closest}"

    async def send_bot_help(
        self,
        mapping: t.Mapping[
            t.Optional[commands.Cog], t.List[commands.Command[t.Any, ..., t.Any]]
        ],
    ) -> None:
        menu = HelpMenu(FrontPageSource(), ctx=self.context)
        menu.add_categories(self, mapping.keys())
        await menu.start()

    async def send_command_help(self, command: commands.Command, /) -> None:
        embed = discord.Embed(
            title=self.get_command_signature(command),
            color=self.context.bot.profile_color,
            description=command.help or "Comando não documentado",
        )
        await self.context.send(embed=embed)

    async def send_cog_help(self, cog: commands.Cog) -> None:
        cmds = cog.get_commands()
        entries = await self.filter_commands(cmds)

        source = CogHelpPageSource(cog, entries)
        menu = UtopiafyPages(source, ctx=self.context)
        await menu.start()
