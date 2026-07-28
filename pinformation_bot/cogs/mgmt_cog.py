from datetime import UTC, datetime
from importlib.metadata import version
from logging import getLogger
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from ..pinformation import PinformationBot
from ..utils.utils import check_admin, handle_reply

log = getLogger(__name__)
"""
This cog is for managing the bot and adding/removing users/roles to the bot.
"""


class ManagementCog(commands.Cog, name="Main"):
    def __init__(self, pin_bot: PinformationBot) -> None:
        self.bot: PinformationBot = pin_bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        log.info("Management cog is ready!")

    @app_commands.command(name="botinfo", description="Get information about the bot.")
    async def info_embed(self, interaction: discord.Interaction[PinformationBot]):  # unprived command
        """
        Get information about the bot.
        """
        embed = discord.Embed(
            title="Pinformation Bot Info",
            type="rich",
            url="https://github.com/dBozee/pinformation/tree/main",
            color=self.bot.config.embed_color,
        )

        _ = embed.add_field(name="Written by", value="<@160074289289101313>")
        _ = embed.add_field(name="Version", value=version("pinformation_bot"))
        _ = embed.add_field(name="Prefix", value=f"`{self.bot.config.prefix}`")
        _ = embed.add_field(name="Ping", value=f"`{round(self.bot.latency * 1000)}`ms")

        # Send embed directly using interaction response/followup
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            _ = await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="manageadmin", description="Add or remove an admin user from the bot permissions.")
    @app_commands.check(check_admin)
    async def manage_admin(
        self,
        interaction: discord.Interaction[PinformationBot],
        action: Literal["add", "remove"],
        user: discord.User,
    ):
        """
        Add or remove an admin user from the bot permissions.
        """
        user_id = str(user.id)
        if action == "add":
            if user_id in self.bot.config.admin_users:
                await handle_reply(interaction, "User already in admin list!", ephemeral=True)
                return
            self.bot.config.admin_users.append(user_id)
            msg = f"Added {user.name} (`{user_id}`) to admin permissions"
            await self.log_mgmt_change(interaction, msg)
            await handle_reply(interaction, msg, ephemeral=True)
        elif action == "remove":
            if user_id not in self.bot.config.admin_users:
                await handle_reply(interaction, "User not in admin list!", ephemeral=True)
                return
            self.bot.config.admin_users.remove(user_id)
            msg = f"Removed {user.name} (`{user_id}`) from admin permissions"
            await self.log_mgmt_change(interaction, msg)
            await handle_reply(interaction, msg, ephemeral=True)
        self.bot.config.write_config_to_json()

    @app_commands.command(name="manageadminrole", description="Add or remove an admin role from the bot permissions.")
    @app_commands.check(check_admin)
    async def manage_admin_role(
        self,
        interaction: discord.Interaction[PinformationBot],
        action: Literal["add", "remove"],
        role: discord.Role,
    ):
        """
        Add or remove an admin role from the bot permissions.
        """
        role_id = str(role.id)
        if action == "add":
            if role_id in self.bot.config.admin_roles:
                await handle_reply(interaction, "Role already in admin list!", ephemeral=True)
                return
            self.bot.config.admin_roles.append(role_id)
            msg = f"Added {role.name} (`{role.id}`) to admin permissions"
            await self.log_mgmt_change(interaction, msg)
            await handle_reply(interaction, msg, ephemeral=True)
        elif action == "remove":
            if role_id not in self.bot.config.admin_roles:
                await handle_reply(interaction, "Role not in admin list!", ephemeral=True)
                return
            self.bot.config.admin_roles.remove(role_id)
            msg = f"Removed {role.name} (`{role.id}`) from admin permissions"
            await self.log_mgmt_change(interaction, msg)
            await handle_reply(interaction, msg, ephemeral=True)
        self.bot.config.write_config_to_json()

    @app_commands.command(
        name="managerole", description="Add or remove permissions for a given role to a given channel."
    )
    @app_commands.check(check_admin)
    async def manage_role(
        self,
        interaction: discord.Interaction[PinformationBot],
        action: Literal["add", "remove"],
        role: discord.Role,
        channel: discord.TextChannel,
    ):
        """
        Add or remove permissions for a given role to a given channel.
        """
        role_id = str(role.id)
        channel_id = str(channel.id)
        permitted_roles = self.bot.config.permitted_roles
        if action == "add":
            if role_id not in permitted_roles:
                permitted_roles[role_id] = []

            if channel_id in permitted_roles[role_id]:
                await handle_reply(interaction, "Role already has access to this channel!", ephemeral=True)
                return

            permitted_roles[role_id].append(channel_id)

            await self.log_mgmt_change(interaction, f"Added {channel.mention} to {role.name}'s permitted list")
            await handle_reply(interaction, f"Added {channel.mention} to {role.name}'s permitted list", ephemeral=True)
        elif action == "remove":
            if role_id not in permitted_roles or channel_id not in permitted_roles[role_id]:
                await handle_reply(interaction, "Role or channel not in permitted list!", ephemeral=True)
                return
            permitted_roles[role_id].remove(channel_id)
            if not permitted_roles[role_id]:  # Remove empty lists
                _ = permitted_roles.pop(role_id, None)

            msg = f"Removed {channel.mention} from {role.name} permitted list"
            await self.log_mgmt_change(interaction, msg)
            await handle_reply(interaction, msg, ephemeral=True)
        self.bot.config.write_config_to_json()

    @app_commands.command(name="setlogchannel", description="Set the log channel for the bot.")
    @app_commands.check(check_admin)
    async def set_log_channel(
        self,
        interaction: discord.Interaction[PinformationBot],
        channel: discord.TextChannel,
    ):
        """
        Set the log channel for the bot.
        """
        self.bot.config.log_channel = str(channel.id)
        self.bot.config.write_config_to_json()
        await self.bot.set_log_channel()
        msg = f"Set log channel to {channel.mention} ({channel.id})"
        await self.log_mgmt_change(interaction, msg)
        await handle_reply(interaction, msg, ephemeral=True)

    async def log_mgmt_change(self, interaction: discord.Interaction[PinformationBot], cmd_msg: str) -> None:
        self.bot.log_action(interaction, cmd_msg)
        if self.bot.log_channel is None:
            log.info(f"{cmd_msg}: {interaction.user.name}|{interaction.user.id}")
            return
        msg = f"{cmd_msg:.250}..." if len(cmd_msg) > 225 else cmd_msg
        embed = discord.Embed(title=f"{msg}", timestamp=datetime.now(tz=UTC))
        _ = embed.add_field(name="User", value=interaction.user.mention)

        _ = await self.bot.log_channel.send(embed=embed)


async def setup(bot: PinformationBot):
    await bot.add_cog(ManagementCog(bot))
