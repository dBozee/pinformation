import logging
from asyncio import sleep
from datetime import UTC, datetime
from json import dumps
from typing import override

import discord
from discord.ext import commands

from .bot_config import BotConfig
from .db_funcs import Database
from .pins import EmbedPin, PinUnion

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
discord.utils.setup_logging()
discord.utils.setup_logging(level=logging.DEBUG, root=False)

INTENTS = discord.Intents.default()
ACTIVITY = discord.CustomActivity(name="Please stop blocking me")


class PinformationBot(commands.Bot):
    def __init__(self, config: BotConfig):
        super().__init__(
            intents=INTENTS,
            command_prefix=[],
            activity=ACTIVITY,
            allowed_mentions=discord.AllowedMentions(everyone=False),
        )

        self.config: BotConfig = config
        self.database: Database = Database()
        self.pins: dict[int, PinUnion] = {}
        self.log_channel: discord.TextChannel | None = None

    async def set_log_channel(self) -> None:
        if self.config.log_channel:
            self.log_channel = await self.fetch_channel(int(self.config.log_channel))  # pyright: ignore[reportAttributeAccessIssue]
            if isinstance(self.log_channel, discord.TextChannel):
                log.info(f"Logging to #{self.log_channel.name}")
                return
        log.warning(f"Text channel with ID {self.config.log_channel} not found. Logging to console only.")
        self.log_channel = None

    @override
    async def setup_hook(self) -> None:
        self.tree.on_error = self.on_app_command_error

        for cog in self.config.cogs:
            await self.load_extension(cog)
        if self.config.debug:
            log.debug("----- DEBUG MODE ENABLED -----")
            await self.load_extension("pinformation_bot.cogs.debug_cog")

        await self.set_log_channel()

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

    async def log_pin_change(
        self, interaction: discord.Interaction[PinformationBot], command_type: str, pin: PinUnion | None = None
    ) -> None:
        if self.log_channel is None:
            log.info(f"{command_type}: {interaction.user.name}|{interaction.user.id}")
            return

        msg = f"{command_type:.250}..." if len(command_type) > 225 else command_type
        embed = discord.Embed(title=f"{msg}", timestamp=datetime.now(tz=UTC))
        _ = embed.add_field(name="User", value=interaction.user.mention)

        if interaction.channel:
            _ = embed.add_field(name="Channel", value=interaction.channel.mention)  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]

        if pin is not None:
            max_len = 999
            _ = embed.add_field(name="Pin Type", value=pin.pin_type)
            if isinstance(pin, EmbedPin):
                _ = embed.add_field(
                    name="Content",
                    value=f"```json\n{truncate(dumps(pin.get_embed_info(), indent=2), max_len)}```",
                    inline=False,
                )
            else:
                _ = embed.add_field(name="Content", value=f"```\n{truncate(pin.text, max_len)}```", inline=False)
            if pin.text and len(pin.text) > max_len:
                _ = embed.set_footer(text=f"Content truncated to {max_len} characters.")

        _ = await self.log_channel.send(embed=embed)

    @staticmethod
    def log_action(interaction: discord.Interaction, action_msg: str) -> None:
        """Logs bot actions performed via interactions."""
        user = interaction.user
        channel_id = interaction.channel_id or "Unknown Channel"
        log.info(f"[{action_msg}] executed by {user.name} ({user.id}) in channel {channel_id}")

    @staticmethod
    async def on_app_command_error(
        _interaction: discord.Interaction, error: discord.app_commands.AppCommandError
    ) -> None:
        if isinstance(error, discord.app_commands.CheckFailure):
            return

        log.error("Unhandled exception in app command:", exc_info=error)


def truncate(text: str, max_len: int = 1024) -> str:
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text
