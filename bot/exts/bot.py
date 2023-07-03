"""Implementação customizada de `discord.ext.commands.Bot`."""
from __future__ import annotations

import logging
import pkgutil
from typing import Optional

import discord
from discord.ext.commands import Bot as BotBase


class Bot(BotBase):
    """Classe-base de `Utopiafy`, herda de `discord.ext.commands.Bot`.

    Parâmetros:
    ----------
        bot_token : str (Token da aplicação, obrigatório)
        *args : list (Argumentos posicionais de `discord.ext.commands.Bot`)
        bot_prefix : str (Prefixo do bot, padrão: '==')
        guild_id : int (ID do servidor, padrão: None)
        httpx_client : httpx.AsyncClient (Cliente HTTPX, padrão: None)

    """

    def __init__(
        self,
        bot_token: str,
        *,
        bot_prefix: str = "==",
        guild_id: Optional[int] = None,
    ) -> None:
        self.bot_token = bot_token
        self.bot_prefix = bot_prefix
        self.guild_id = guild_id
        self.logger = logging.getLogger(name=__name__)

        super().__init__(command_prefix=self.bot_prefix, intents=discord.Intents.all())

    async def setup_hook(self) -> None:
        """Inicializar extensões"""
        packages = pkgutil.iter_modules(path=["./cogs"])
        for package in packages:
            if package.ispkg:
                await self.load_extension(name=f"cogs.{package.name}")

        return await super().setup_hook()
