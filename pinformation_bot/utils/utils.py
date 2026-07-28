import logging

import discord
from discord.app_commands import CheckFailure
from discord.role import Role

from pinformation_bot.pinformation import PinformationBot
from pinformation_bot.pins import PinUnion

log = logging.getLogger(__name__)


class NotPermittedException(CheckFailure):
    pass


async def handle_reply(
    interaction: discord.Interaction[PinformationBot],
    msg: str,
    ephemeral: bool = True,
) -> None:
    """
    Sends a reply to an interaction, handling whether the interaction
    has already been deferred/responded to or not.
    """
    if interaction.user.bot:
        return

    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=ephemeral)
    else:
        _ = await interaction.response.send_message(msg, ephemeral=ephemeral)


async def delete_old_message(
    channel: discord.abc.Messageable | discord.interactions.InteractionChannel, message_id: int | None
) -> None:
    if not message_id:
        return

    try:
        if isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.Thread)):
            await channel.delete_messages([discord.Object(id=message_id)])
        elif isinstance(channel, discord.abc.Messageable):  # fallback for DM channels, PartialMessageable, etc.
            msg = await channel.fetch_message(message_id)
            await msg.delete()

    except discord.NotFound:
        channel_name = getattr(channel, "name", f"Channel {getattr(channel, 'id', 'unknown')}")
        log.warning(f"Failed to find & delete last message in {channel_name}")
    except discord.HTTPException as e:
        channel_name = getattr(channel, "name", f"Channel {getattr(channel, 'id', 'unknown')}")
        log.warning(f"Failed to delete last message in {channel_name} with HTTP exception: {e}")


async def get_pin(
    interaction: discord.Interaction[PinformationBot],
    bot: PinformationBot,
    channel_id: int,
) -> PinUnion | None:
    if pin := bot.pins.get(channel_id):
        return pin
    await handle_reply(interaction, "No active pin in this channel!", ephemeral=True)
    return None


async def _check_admin(interaction: discord.Interaction[PinformationBot]) -> bool:
    bot: PinformationBot = interaction.client

    if str(interaction.user.id) in bot.config.admin_users:
        return True

    user_roles: list[Role] = getattr(interaction.user, "roles", [])
    user_role_ids = [str(role.id) for role in user_roles]
    return any(admin_role in user_role_ids for admin_role in bot.config.admin_roles)


async def check_admin(interaction: discord.Interaction[PinformationBot]) -> bool:
    if await _check_admin(interaction):
        return True

    await handle_reply(interaction, "You are not authorized to use this command!", ephemeral=True)
    cmd_name = interaction.command.name if interaction.command else "unknown"
    log.warning(f"{interaction.user.name}({interaction.user.id}): attempted to use the {cmd_name} command.")
    return False


async def check_permitted(interaction: discord.Interaction[PinformationBot]) -> bool:
    """
    Checks if interaction user is allowlisted either by their user_id or a role_id.
    If false, the user is given an ephemeral message that they don't have permission
    and logs that the user tried to use a role outside their permissions.
    """
    bot: PinformationBot = interaction.client

    if await _check_admin(interaction):
        return True

    user_roles: list[Role] = getattr(interaction.user, "roles", [])
    user_role_ids = [str(role.id) for role in user_roles]
    permitted_roles = bot.config.permitted_roles

    if interaction.channel_id:
        channel_id_str = str(interaction.channel_id)
        for role_id in user_role_ids:
            if role_id in permitted_roles and channel_id_str in permitted_roles[role_id]:
                return True

    await handle_reply(interaction, "You are not authorized to use this command!", ephemeral=True)
    cmd_name = interaction.command.name if interaction.command else "unknown"
    log.warning(f"{interaction.user.name}({interaction.user.id}): attempted to use the {cmd_name} command.")
    raise NotPermittedException
