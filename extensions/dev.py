from __future__ import annotations
import traceback
import typing as t

from discord import app_commands
from discord.ext import commands
from discord import ui
import discord

from contextlib import redirect_stdout
import textwrap
import io

if t.TYPE_CHECKING:
    from core import Utopify


class SelectBugType(ui.Select):
    is_done: bool

    def __init__(self) -> None:
        self.is_done = False
        options = [
            discord.SelectOption(
                label="Comando não está respondendo",
                emoji="\U0000274c",
            ),
            discord.SelectOption(
                label="Feature quebrada",
                emoji="\U0001f6a8",
            ),
            discord.SelectOption(
                label="Outro",
                emoji="\U0001f914",
            ),
        ]
        super().__init__(placeholder="O Tipo do bug", options=options, row=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        self.is_done = True


class ReportBugModal(ui.Modal, title="Reportar um bug"):
    def __init__(self, view: "ReportBugView") -> None:
        self.view: "ReportBugView" = view
        super().__init__()

    bug = ui.TextInput(
        label="Descreva aqui o bug que você encontrou",
        style=discord.TextStyle.long,
        min_length=5,
        max_length=994,
    )

    def _get_selectmenu(self) -> t.Optional[ui.Select]:
        # 1st Select is probably the
        # menu that we are looking for,
        # since the message only contains one
        # of them.
        children = [
            child for child in self.view.children if isinstance(child, ui.Select)
        ]
        if children:
            return children[0]
        return None

    async def _get_my_webhook_on(
        self, channel: discord.TextChannel
    ) -> t.Optional[discord.Webhook]:
        webhooks = await channel.webhooks()
        webhook = discord.utils.get(webhooks, user=self.view.bot.user)

        if webhook:
            return webhook
        return None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.message is None:
            return

        if interaction.guild is None:
            raise ValueError("cannot use this command on a direct message ambient.")

        if interaction.client.user is None:
            return

        if interaction.client.user.avatar is None:
            return

        bugs_channel = interaction.guild.get_channel(1098358538218258532)
        if not isinstance(bugs_channel, discord.TextChannel):
            return

        select = self._get_selectmenu()
        if select is None:
            return

        webhook = await self._get_my_webhook_on(bugs_channel)
        if webhook is None:
            webhook = await bugs_channel.create_webhook(
                name=interaction.client.user.display_name,
                avatar=await interaction.client.user.avatar.read(),
            )

        try:
            selected = select.values[0]
        except IndexError:
            return await interaction.response.send_message(
                content="Por favor, selecione o tipo do bug antes de reporta-lo",
                ephemeral=True,
            )

        embed = discord.Embed(
            title="Novo bug reportado",
            color=self.view.bot.profile_color,
        )
        embed.add_field(name="Categoria", value=selected, inline=False)
        embed.add_field(name="Descrição", value=self.bug.value, inline=False)

        await webhook.send(f"Reportado por {interaction.user.mention}", embed=embed)
        await interaction.response.send_message(
            content="O Seu bug foi reportado com sucesso!",
            ephemeral=True,
        )


class ReportBugView(ui.View):
    def __init__(self, bot: Utopify) -> None:
        super().__init__(timeout=240)
        self.bot = bot

        self.select = SelectBugType()
        self.add_item(self.select)

    @ui.button(
        label="Descrever o bug",
        style=discord.ButtonStyle.blurple,
        emoji="\U0001f41e",
        row=2,
    )
    async def describe_bug(
        self,
        interaction: discord.Interaction,
        button: ui.Button,
    ) -> None:
        if not self.select.is_done:
            return await interaction.response.send_message(
                content="Por favor, selecione o tipo do bug antes de reporta-lo",
                ephemeral=True,
            )
        modal = ReportBugModal(view=self)
        await interaction.response.send_modal(modal)


class Dev(commands.Cog):
    hidden = True

    def __init__(self, bot: Utopify):
        self.bot: Utopify = bot

    @app_commands.command(
        name="report_bug",
        description="Usado para reportar um bug ao desenvolvedor responsável",
    )
    async def report_bug(self, interaction: discord.Interaction) -> None:
        if self.bot.owner is None:
            return

        msg: t.Tuple[str, ...] = (
            f"Olá! Bem-vindo à página de bugs",
            f"Aqui você pode reportar ao desenvolvedor {self.bot.owner.mention} alguns bugs que você encontrar no bot\n",
            f"**Categorias de bugs**",
            f"	***1.*** *Comando não está respondendo*",
            f"	***2.*** *Feature quebrada*",
            f"	***3.*** *Outro*\n",
            (
                f"Você pode usar o menu abaixo para selecionar o "
                f"tipo de bug desejado, então pressione o botão `Descrever o bug` e forneça mais informações sobre o ocorrido"
            ),
        )

        embed = discord.Embed(
            title="Reportar um bug",
            description="\n".join(msg),
            color=0xFD8A37,
        )

        await interaction.response.send_message(
            view=ReportBugView(bot=self.bot),
            ephemeral=True,
            embed=embed,
        )

    def cleanup_code(self, content: str) -> str:
        """Removes code blocks from the code"""
        # remove ```py\n```
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])

        # remove `foo`
        return content.strip("` \n")

    @commands.command(name="eval", hidden=True)
    @commands.is_owner()
    async def _eval(self, ctx: commands.Context, *, body: str) -> None:
        body = self.cleanup_code(body)
        stdout = io.StringIO()

        namespace = {
            "bot": self.bot,
            "ctx": ctx,
            "message": ctx.message,
            "guild": ctx.guild,
            "author": ctx.author,
            "discord": discord,
            "__builtins__": __builtins__,
        }

        to_compile = f"async def fn():\n{textwrap.indent(body, '  ')}"

        try:
            exec(to_compile, namespace)
        except Exception as e:
            await ctx.send(f"```py\n{e.__class__.__name__}: {e}\n```")
            return

        func: t.Callable[[], t.Coroutine[t.Any, t.Any, t.Any]] = namespace["fn"]
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send(f"```\n{value}{traceback.format_exc()}\n```")
            return

        value = stdout.getvalue()
        if (ret is None) and not bool(value):
            await ctx.send(f"```[No Output]```")

        elif (ret is None) and bool(value):
            await ctx.send(f"```py\n{value}\n```")

        elif (ret is not None) and bool(value):
            await ctx.send(f"```py\n{value}{ret}\n```")

    @commands.command(name="sync", help="Sincroniza todos os comandos do bot")
    @commands.is_owner()
    async def sync(self, ctx: commands.Context) -> None:
        synced = await self.bot.tree.sync()
        await ctx.reply(f"> Sincronizei {len(synced)} comandos com sucesso!")


async def setup(bot: Utopify) -> None:
    await bot.add_cog(Dev(bot))
