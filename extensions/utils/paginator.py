from __future__ import annotations
import typing as t

from discord.ext import commands
from discord.ext import menus
from discord import ui
import discord


class UtopiafyPages(ui.View):
    def __init__(self, source: menus.PageSource, *, ctx: commands.Context) -> None:
        super().__init__()
        self.source: menus.PageSource = source
        self.ctx: commands.Context = ctx
        self.current_page: int = 0

    def fill_items(self):
        if not self.source.is_paginating():
            return

        self.add_item(self.go_to_first_page)
        self.add_item(self.go_to_previous_page)
        self.add_item(self.go_to_next_page)
        self.add_item(self.go_to_last_page)
        self.add_item(self.stop_pages)

    async def _get_kwargs_from_page(self, page: menus.PageSource) -> t.Dict[str, t.Any]:
        value = await discord.utils.maybe_coroutine(self.source.format_page, self, page)
        if isinstance(value, dict):
            return value
        elif isinstance(value, str):
            return {"content": value, "embed": None}
        elif isinstance(value, discord.Embed):
            return {"content": None, "embed": value}
        else:
            return {}

    async def show_page(
        self, interaction: discord.Interaction, page_number: int
    ) -> None:
        page: menus.PageSource = await self.source.get_page(page_number)
        self.current_page = page_number
        kwargs = await self._get_kwargs_from_page(page)
        self._update_labels(page_number)
        if kwargs:
            await interaction.response.edit_message(**kwargs, view=self)

    async def show_checked_page(
        self, interaction: discord.Interaction, page: int
    ) -> None:
        max_pages = self.source.get_max_pages()
        try:
            if max_pages is None:
                await self.show_page(interaction, page)
            elif max_pages > page >= 0:
                await self.show_page(interaction, page)
        except IndexError:
            pass

    async def start(
        self, *, content: t.Optional[str] = None, ephemeral: bool = False
    ) -> None:
        await self.source._prepare_once()
        page = await self.source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        if content:
            kwargs.setdefault("content", content)

        self._update_labels(0)
        await self.ctx.send(**kwargs, view=self, ephemeral=ephemeral)

    def _update_labels(self, page: int) -> None:
        max_pages = self.source.get_max_pages()
        self.go_to_first_page.disabled = page == 0
        self.go_to_last_page.disabled = max_pages is None or (page + 1) >= max_pages
        self.go_to_next_page.disabled = (
            max_pages is not None and (page + 1) >= max_pages
        )
        self.go_to_previous_page.disabled = page == 0

    @ui.button(label="≪", style=discord.ButtonStyle.grey)
    async def go_to_first_page(
        self,
        interaction: discord.Interaction,
        button: ui.Button,
    ):
        await self.show_page(interaction, 0)

    @ui.button(label="Back", style=discord.ButtonStyle.blurple)
    async def go_to_previous_page(
        self,
        interaction: discord.Interaction,
        button: ui.Button,
    ):
        await self.show_checked_page(interaction, self.current_page - 1)

    @ui.button(label="Next", style=discord.ButtonStyle.blurple)
    async def go_to_next_page(
        self,
        interaction: discord.Interaction,
        button: ui.Button,
    ):
        await self.show_checked_page(interaction, self.current_page + 1)

    @ui.button(label="≫", style=discord.ButtonStyle.grey)
    async def go_to_last_page(
        self,
        interaction: discord.Interaction,
        button: ui.Button,
    ):
        await self.show_page(interaction, self.source.get_max_pages() - 1)  # type: ignore

    @ui.button(label="Quit", style=discord.ButtonStyle.red)
    async def stop_pages(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # fmt: off
        if interaction.user and interaction.user.id in (self.ctx.bot.owner_id, self.ctx.author.id):
            return True
        await interaction.response.send_message("Você não pode controlar isso", ephemeral=True)
        return False
        # fmt: on
