"""Implementação customizada de `discord.ext.commands.Bot`."""
from __future__ import annotations

import pkgutil

import discord
from discord.ext.commands import Bot as BotBase
from httpx import AsyncClient, HTTPError

from bot.ext.utils.logger import logger


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
        guild_id: int | str | None = None,
        httpx_client: AsyncClient | None = None,
    ) -> None:
        self.bot_token = bot_token
        self.bot_prefix = bot_prefix
        self.guild_id = guild_id
        self.httpx_client = httpx_client
        self.logger = logger

        super().__init__(command_prefix=self.bot_prefix, intents=discord.Intents.all())

    async def _set(self) -> None:
        """Validar atributos de `Bot`"""

        if not isinstance((self.httpx_client), AsyncClient) or self.httpx_client is None:
            self.logger.warning(msg="O cliente HTTPX não foi definido, usando um cliente padrão.")
            setattr(self, "httpx_client", AsyncClient())

            try:
                client: AsyncClient = getattr(self, "httpx_client")
                res = await client.post(
                    url="https://api.mathjs.org/v4/",
                    json={"expr": "5+5"},
                )
                res.raise_for_status()
                self.logger.info(msg="O cliente HTTPX definido, credenciais são padrões.")

            except HTTPError as error:
                self.logger.error(msg=error)
                raise AttributeError("O cliente HTTPX não foi definido corretamente.") from error

        if not isinstance(self.bot_token, str):
            raise TypeError("O token do bot deve ser uma string.")

        if not isinstance(self.bot_prefix, str):
            setattr(self, "bot_prefix", "==")

    async def setup_hook(self) -> None:
        """Inicializar extensões"""
        await self._set()
        packages = pkgutil.iter_modules(path=["./bot/cogs"])
        for package in packages:
            await self.load_extension(name=f"bot.cogs.{package.name}")
            self.logger.info(msg=f"Extensão {package.name} carregada com sucesso.")

        return await super().setup_hook()

    def run(self) -> None:
        """Iniciar o bot"""
        return super().run(token=self.bot_token)
