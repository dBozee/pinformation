import logging
from asyncio import sleep

import discord
from discord.ext import commands

from .bot_config import BotConfig
from .pins import Pin
from .db_funcs import Database

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
discord.utils.setup_logging()
discord.utils.setup_logging(level=logging.DEBUG, root=False)


class PinformationBot(commands.Bot):
    def __init__(self, config: BotConfig):
        INTENTS = discord.Intents.default()
        INTENTS.message_content = True
        INTENTS.members = True

        super().__init__(
            intents=INTENTS,
            command_prefix=commands.when_mentioned_or(config.prefix),
            activity=discord.Activity(type=discord.ActivityType.playing, name="keep up with chat."),
            allowed_mentions=discord.AllowedMentions(everyone=False),
        )

        self.config: BotConfig = config
        self.database: Database = Database()
        self.pins: dict[int, Pin] = {}

    async def setup_hook(self):
        # add cogs
        for cog in self.config.cogs:
            await self.load_extension(cog)

        # sync all commands
        synced = await self.tree.sync()
        log.info(f"Added main cog commands... Synced {len(synced)} commands")

    async def reload_extensions(self) -> list[str]:
        ext_count: int = len(self.extensions)
        log.info(f"Attempting to reload {ext_count} extensions...")
        pre_reload_exts = list(self.extensions)

        for ext in pre_reload_exts:
            await self.reload_extension(ext)
        await sleep(1)
        return list(self.extensions)

    @staticmethod
    def log_action(ctx: commands.Context, message: str):
        log.info(f"{ctx.author.name}({ctx.author.id}): {message}")
