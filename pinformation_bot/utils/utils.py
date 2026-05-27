import logging

import discord
from discord.ext import commands

from pinformation_bot.pinformation import PinformationBot
from pinformation_bot.pins import Pin

log = logging.getLogger(__name__)


async def handle_reply(ctx: commands.Context, msg: str, success: bool = True, reply: bool = True):
    if ctx.author.bot:
        return
    if ctx.interaction is None or not reply:
        react = "✅" if success else "❌"
        await ctx.message.add_reaction(react)
        return
    await ctx.reply(msg, ephemeral=reply)


async def delete_old_message(channel: discord.TextChannel, message_id: int | None):
    try:
        if not message_id:
            return
        await channel.delete_messages([discord.Object(id=message_id)])  # noqa
    except discord.NotFound:
        log.warning(f"Failed to find & delete last message in channel {channel.name}")
    except discord.HTTPException as e:
        log.warning(f"Failed to delete last message in channel {channel.name} with HTTP exception: {e}")


async def get_pin(ctx: commands.Context, bot: PinformationBot, channel_id: int) -> Pin | None:
    if pin := bot.pins.get(channel_id):
        return pin
    await ctx.reply("No active pin in this channel!", ephemeral=True)
    return None


async def _check_admin(ctx: commands.Context) -> bool:
    if (str(ctx.author.id)) in ctx.bot.config.admin_users:
        return True
    user_role_ids = [str(role.id) for role in ctx.author.roles]
    return bool(any(admin_role in user_role_ids for admin_role in ctx.bot.config.admin_roles))


async def check_admin(ctx: commands.Context) -> bool:
    if await _check_admin(ctx):
        return True

    await ctx.reply("You are not authorized to use this command!", ephemeral=True)
    log.warning(f"{ctx.author.name}({ctx.author.id}): attempted to use the {ctx.command} command.")
    return False


async def check_permitted(ctx: commands.Context) -> bool:
    """
    checks if ctx author is allowlisted either by their user_id or a role_id.
    If false, the user is given an ephemeral message that they don't have permission
    and logs that the user tried to use a role outside their permissions.
    """
    if await _check_admin(ctx):
        return True

    user_role_ids = [str(role.id) for role in ctx.author.roles]
    permitted_roles = ctx.bot.config.permitted_roles

    for role_id in user_role_ids:
        if role_id in permitted_roles and str(ctx.channel.id) in permitted_roles[role_id]:
            return True

    await ctx.reply("You are not authorized to use this command!", ephemeral=True)
    log.warning(f"{ctx.author.name}({ctx.author.id}): attempted to use the {ctx.command} command.")
    return False
