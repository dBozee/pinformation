from dataclasses import asdict, dataclass
from json import dump
from logging import getLogger
from pathlib import Path
from typing import Optional

from discord.ext import commands

log = getLogger(__name__)
JSON_FILE = Path(Path(__file__).parent / "config" / "config.json")


@dataclass
class BotConfig:
    """
    Dataclass for the configuration of the bot. Should be originally instantiated
    by the config.json file.
    """

    prefix: Optional[str]
    permitted_users: Optional[list[str]]
    permitted_roles: Optional[list[str]]
    embed_color: Optional[int]
    cogs: Optional[list[str]]

    def write_config_to_json(self):
        log.debug(f"Opening config file at: {str(JSON_FILE)}")
        outfile = JSON_FILE.open("w")
        dump(asdict(self), outfile, indent=4)
        outfile.close()
        log.debug("Finished writing to config file")


async def check_permitted(ctx: commands.Context) -> bool:
    """
    checks if ctx author is allow listed either by their user_id or a role_id.
    If false, user is given ephemeral message that they don't have permission
    and logs that user tried to use role otuside their permissions.
    """
    if str(ctx.author.id) in ctx.bot.config.permitted_users:
        return True
    if any(role for role in ctx.author.roles if str(role.id) in ctx.bot.config.permitted_roles):
        return True
    await ctx.reply("You are not authorized to use this command!", ephemeral=True)
    log.warning(f"{ctx.author.name}({ctx.author.id}): attempted to use the {ctx.command} command.")
    return False
