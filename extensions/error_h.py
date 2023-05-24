from __future__ import annotations
import typing as t

from difflib import get_close_matches
from discord.ext import commands
import discord

import traceback
import logging

from io import BytesIO

from .utils.checks import NotStaff

if t.TYPE_CHECKING:
    from core import Utopify

log = logging.getLogger("discord.utopiafy")


class ErrorHandler(commands.Cog):
    hidden = True

    def __init__(self, bot: Utopify) -> None:
        self.bot = bot

    @commands.Cog.listener(name="on_command_error")
    async def on_command_error(
        self,
        ctx: commands.Context[Utopify],
        error: commands.CommandError,
    ):
        cmd = ctx.command
        if isinstance(error, commands.errors.CommandNotFound):
            invoked_with = ctx.invoked_with
            if invoked_with is None:
                return

            cmds = (cmd.name for cmd in ctx.bot.commands)
            matches = get_close_matches(invoked_with, cmds)

            if not matches:
                return await ctx.send(
                    f"> *[ERRO]* | Nenhum comando chamado {invoked_with} foi encontrado"
                )

            closest = ""
            for match in matches:
                closest += f"- `{ctx.clean_prefix}{match}`\n"

            await ctx.send(
                f"> *[ERRO]* | Comando não encontrado, talvez você queria dizer:\n {closest}"
            )

        elif isinstance(error, NotStaff):
            await ctx.send(
                f"> *[ERRO]* | Você não pode executar esse comando porque não é um moderador!"
            )

        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"> *[ERRO]* | {error!s}")

        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(
                f"> *[ERRO]* | Você não pode usar o comando porque você não tem a(s) seguinte(s) permissões: `\"{', '.join(error.missing_permissions)}\"`. Resumindo o erro, você é da plebe"
            )

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"> *[ERRO]* | Calma aí camarada! O comando está no cooldown, restam `{round(error.retry_after)}s` até o comando poder ser executado novamente"
            )

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f'> *[ERRO]* | "`{error.param.name}`" é um argumento obrigatório, informe-o e tente novamente'
            )

        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(
                f"> *[ERRO]* | Não posso concluir isso porque não tenho as seguintes permissões: `\"{', '.join(error.missing_permissions)}\"`"
            )

        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(
                f"> *[ERRO]* | Não encontrei nenhum membro chamado *{error.argument}*"
            )

        else:
            log.error("An exception occurred while executing '%s'", cmd, exc_info=error)
            await ctx.send(
                "> *[ERRO]* | Algo deu errado ao executar esse comando... O Desenvolvedor já foi alertado!"
            )

            tb = "".join(
                traceback.format_exception(
                    type(error),
                    error,
                    error.__traceback__,
                )
            )

            tb_desc = f"The exception '{error.__class__.__name__}' was raised while executing {cmd.name} (invoked by: {ctx.author!s}). {ctx.message.jump_url}"  # type: ignore

            PAINEL_CHANNELID = 794456288306266122
            painel = ctx.bot.get_channel(PAINEL_CHANNELID)
            if not isinstance(painel, discord.TextChannel):
                return

            if len(tb) > 1024:
                fp = BytesIO(tb.encode())
                return await painel.send(
                    content=tb_desc,
                    file=discord.File(fp, filename="traceback.txt"),
                )

            embed = discord.Embed(
                title="An exception occurred",
                description=tb_desc,
            )
            embed.add_field(name="Traceback", value=f"```{tb}```")
            await painel.send(embed=embed)

        if cmd is None:
            return

        exclude_reset_cooldown: t.List[t.Type[Exception]] = [commands.CommandOnCooldown]
        if type(error) not in exclude_reset_cooldown:
            cmd.reset_cooldown(ctx)


async def setup(bot: Utopify) -> None:
    await bot.add_cog(ErrorHandler(bot))
