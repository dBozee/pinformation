import logging
from asyncio import sleep

import discord
from discord import app_commands
from discord.ext import commands

from pinformation_bot.pinformation import PinformationBot

from ..utils.utils import check_permitted, handle_reply

log = logging.getLogger(__name__)


class DebugCog(commands.Cog):
    def __init__(self, pin_bot: PinformationBot) -> None:
        self.bot: PinformationBot = pin_bot

    @app_commands.command(name="shutdown", description="Shut down the bot.")
    @app_commands.check(check_permitted)
    async def shutdown(self, interaction: discord.Interaction[PinformationBot]):
        """Shut down the bot safely."""
        self.bot.log_action(interaction, "Shut down the bot")
        await handle_reply(interaction, "Shutting down...", ephemeral=True)
        await sleep(1)
        self.bot.database.db.close()
        await self.bot.close()
        exit()

    @app_commands.command(name="reload", description="Reload all bot extensions/cogs.")
    @app_commands.check(check_permitted)
    async def reload(self, interaction: discord.Interaction[PinformationBot]):
        """Reload all active bot cogs without restarting the process."""
        reloaded = await self.bot.reload_extensions()
        msg = f"Successfully reloaded {', '.join(reloaded)}" if reloaded else "Failed to reload extensions"

        await handle_reply(interaction, msg, ephemeral=True)
        self.bot.log_action(interaction, "Reloaded the bot")


async def setup(bot: PinformationBot):
    await bot.add_cog(DebugCog(bot))
