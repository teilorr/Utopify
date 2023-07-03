"""Ponto de entrada de `Utopiafy`"""

from typing import Optional

from dotenv import dotenv_values

from bot.ext.bot import Bot

config = dotenv_values(".env")

BOT_TOKEN: Optional[str] = config.get("TOKEN")
BOT_PREFIX: Optional[str] = config.get("PREFIX")
GUILD_ID: Optional[int | str] = config.get("GUILD_ID")


bot = Bot(
    bot_token=BOT_TOKEN,
    bot_prefix=BOT_PREFIX,
    guild_id=int(GUILD_ID),
)

if __name__ == "__main__":
    bot.run()
