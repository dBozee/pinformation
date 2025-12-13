from dataclasses import asdict, dataclass
from json import dump
from logging import getLogger
from pathlib import Path

from discord.ext import commands

log = getLogger(__name__)
CONFIG_FOLDER = Path(__file__).parent / "config"
JSON_FILE = Path(CONFIG_FOLDER / "config.json")


@dataclass
class BotConfig:
    """
    Dataclass for the configuration of the bot. Should be originally instantiated
    by the config.json file.
    """

    prefix: str | None
    permitted_users: list[str] | None
    permitted_roles: list[str] | None
    embed_color: int | None
    cogs: list[str] | None

    def write_config_to_json(self):
        log.debug(f"Opening config file at: {str(JSON_FILE)}")
        outfile = JSON_FILE.open("w")
        dump(asdict(self), outfile, indent=4)
        outfile.close()
        log.debug("Finished writing to config file")


async def check_permitted(ctx: commands.Context) -> bool:
    """
    checks if ctx author is allowlisted either by their user_id or a role_id.
    If false, the user is given an ephemeral message that they don't have permission
    and logs that the user tried to use a role outside their permissions.
    """
    if str(ctx.author.id) in ctx.bot.config.permitted_users:
        return True
    if any(role for role in ctx.author.roles if str(role.id) in ctx.bot.config.permitted_roles):
        return True
    await ctx.reply("You are not authorized to use this command!", ephemeral=True)
    log.warning(f"{ctx.author.name}({ctx.author.id}): attempted to use the {ctx.command} command.")
    return False
