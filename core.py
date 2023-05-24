from __future__ import annotations
import typing as t

from discord.ext import commands
from discord.ext import tasks
import discord

import logging

from extensions.utils.image import predominant_color_on
from extensions.utils.context import Context
from extensions.help import PaginatedHelp

log = logging.getLogger("discord.utopiafy")

inital_extensions = (
    "extensions.fun",
    "extensions.dev",
    "extensions.error_h",
    "extensions.mod",
)


def dotenv_get(var: str, *, dotenv_path: str = ".env") -> t.Any:
    with open(dotenv_path, "r", encoding="UTF-8") as f:
        for line in f.readlines():
            line: str = line.replace("\n", "").strip()
            if not line or line.startswith("#"):
                continue

            key, value = line.split("=", maxsplit=1)
            if key.strip() == var.strip():
                return value
        return None


class LoggedBot(commands.Bot):
    async def close(self) -> None:
        usr_id = self.user.id if self.user is not None else -1

        log.info("%s (Client ID: %s) is logging-out", self.user, usr_id)
        return await super().close()

    async def on_ready(self) -> None:
        usr_id = self.user.id if self.user is not None else -1

        log.info("Bot has started as %s (Client ID: %s)", self.user, usr_id)

    async def load_extension(
        self,
        name: str,
        *,
        package: t.Optional[str] = None,
    ) -> None:
        log.debug("Loading '%s' extension", name)
        try:
            await super().load_extension(name, package=package)
        except Exception as e:
            log.exception("Failed to load the '%s' extension", name)

    async def on_command(self, ctx: commands.Context[t.Self]) -> None:
        log.debug(
            "Command '%s' by '%s' was found, preparing to invoke...",
            ctx.command,
            ctx.author,
        )

    async def on_command_completion(self, ctx: commands.Context[t.Self]) -> None:
        log.debug(
            "Command '%s' called by '%s' was successfully executed",
            ctx.command,
            ctx.author,
        )


class Utopify(LoggedBot):
    bot_app_info: discord.AppInfo
    profile_color: discord.Color
    _painel_channel: discord.TextChannel

    def __init__(self) -> None:
        super().__init__(
            command_prefix="==",
            case_insensitive=True,
            strip_after_prefix=True,
            intents=discord.Intents.all(),
            help_command=PaginatedHelp(),
            activity=discord.Game(name="Em busca do utopia automático"),
            allowed_mentions=discord.AllowedMentions(
                everyone=False, roles=False, users=True
            ),
        )

    @discord.utils.cached_property
    def owner(self) -> t.Optional[discord.TeamMember]:
        if self.bot_app_info.team is None:
            return None

        members = self.bot_app_info.team.members
        return discord.utils.get(members, id=self.owner_id)

    async def setup_hook(self) -> None:
        PAINEL_ID = 794456288306266122

        self._painel_channel = await self.fetch_channel(PAINEL_ID)  # type: ignore
        self.profile_color = await self.fetch_profile_color()
        self.bot_app_info = await self.application_info()
        self.owner_id = 848662859176607764

        for extension in inital_extensions:
            await self.load_extension(extension)

        self.reminder.start()

    def get_context(
        self,
        message: discord.Message,
        cls: t.Optional[t.Type[commands.Context]] = None,
    ):
        return super().get_context(message, cls=cls or Context)

    async def fetch_profile_color(self) -> discord.Color:
        if self.user is None or self.user.avatar is None:
            raise RuntimeError("function called before loggin-in to discord")

        avatar = await self.user.avatar.read()
        r, g, b, a = predominant_color_on(avatar)
        return discord.Color.from_rgb(r, g, b)

    async def fetch_or_get_member(
        self, guild: discord.Guild, member_id: int
    ) -> discord.Member:
        member = guild.get_member(member_id)
        if member is not None:
            return member

        return await guild.fetch_member(member_id)

    def is_staff(self, member: discord.Member) -> bool:
        if member.guild_permissions.manage_channels:
            return True

        STAFF_ROLEID = 794460618283417613
        if STAFF_ROLEID in map(lambda r: r.id, member.roles):
            return True
        return False

    @tasks.loop(hours=16)
    async def reminder(self) -> None:
        assert self.user is not None
        assert self.owner is not None

        async with getattr(self.http, "_HTTPClient__session").request(
            method="GET",
            url=f"https://api.discloud.app/v2/app/{self.user.id}/backup",
            headers={"api-token": dotenv_get("DISCLOUD_TOKEN")},
        ) as res:
            json = await res.json()
            backup_url = json["backups"]["url"]

        embed = discord.Embed(
            title=":warning:Reminder ",
            color=discord.Color.orange(),
            description=f"Seu reminder diário de baixar o backup das databases. [Aperte aqui]({backup_url}) para baixar",
        )

        await self._painel_channel.send(self.owner.mention, embed=embed)


bot = Utopify()
bot.run(
    token=dotenv_get("TOKEN"),
    log_level=logging.INFO,
)
