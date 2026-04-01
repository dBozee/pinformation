import logging
from asyncio import sleep
from datetime import UTC, datetime
from json import dumps

import discord
from discord.ext import commands

from .bot_config import BotConfig
from .db_funcs import Database
from .pins import EmbedPin, Pin, TextPin

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
discord.utils.setup_logging()
discord.utils.setup_logging(level=logging.DEBUG, root=False)

INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True


class PinformationBot(commands.Bot):
    def __init__(self, config: BotConfig):
        super().__init__(
            intents=INTENTS,
            command_prefix=commands.when_mentioned_or(config.prefix),
            activity=discord.Activity(type=discord.ActivityType.playing, name="Keeping up with chat."),
            allowed_mentions=discord.AllowedMentions(everyone=False),
        )

        self.config: BotConfig = config
        self.database: Database = Database()
        self.pins: dict[int, Pin] = {}
        self.log_channel: discord.TextChannel | None = None

    async def set_log_channel(self) -> None:
        if self.config.log_channel:
            self.log_channel = await self.fetch_channel(int(self.config.log_channel))
            if isinstance(self.log_channel, discord.TextChannel):
                log.info(f"Logging to #{self.log_channel.name}")
                return
        log.warning(f"Text channel with ID {self.config.log_channel} not found. Logging to console only.")
        self.log_channel = None

    async def setup_hook(self) -> None:
        # add cogs
        for cog in self.config.cogs:
            await self.load_extension(cog)
        if self.config.debug:
            log.debug("----- DEBUB MODE ENABLED -----")
            await self.load_extension("pinformation_bot.cogs.debug_cog")

        await self.set_log_channel()

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

    async def log_pin_change(self, ctx: commands.Context, command_type: str, pin: Pin | None) -> None:
        if self.log_channel is None:
            log.info(f"{command_type}: {ctx.author.name}|{ctx.author.id}")
            return
        embed = discord.Embed(title=f"{command_type}", timestamp=datetime.now(tz=UTC))
        embed.add_field(name="User", value=ctx.author.mention)
        embed.add_field(name="Channel", value=ctx.channel.mention)
        if pin is not None:
            max_len = 999
            embed.add_field(name="Pin Type", value=pin.pin_type)
            if isinstance(pin, EmbedPin):
                embed.add_field(
                    name="Content",
                    value=f"```json\n{truncate(dumps(pin.get_embed_info(), indent=2), max_len)}```",
                    inline=False,
                )

            elif isinstance(pin, TextPin):
                embed.add_field(name="Content", value=f"```\n{truncate(pin.text, max_len)}```", inline=False)
            if len(pin.text) > max_len:
                embed.set_footer(text=f"Content truncated to {max_len} characters.")

        await self.log_channel.send(embed=embed)

    @staticmethod
    def log_action(ctx: commands.Context, message: str) -> None:
        log.info(f"{ctx.author.name}({ctx.author.id}): {message}")


def truncate(text: str, max_len: int = 1024) -> str:
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text
