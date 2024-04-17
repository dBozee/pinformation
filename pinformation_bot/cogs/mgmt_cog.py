from asyncio import sleep
from logging import getLogger
from typing import Literal

import discord
from discord.ext import commands
from pkg_resources import get_distribution

from ..pinformation import PinformationBot
from ..bot_config import check_permitted

log = getLogger(__name__)
VERSION = get_distribution("pinformation").version
"""
This cog is for managing the bot and adding/removing users/roles to the bot.
"""


class ManagementCog(commands.Cog, name="Main"):
    def __init__(self, pin_bot: PinformationBot) -> None:
        self.bot: PinformationBot = pin_bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        log.info("Management cog is ready!")

    @commands.hybrid_command(name="botinfo")
    async def info_embed(self, ctx: commands.Context):  # unprived command
        """
        Get information about the bot.
        """
        embed = discord.Embed(
            title="Pinformation Bot Info",
            type="rich",
            url="https://github.com/dBozee/pinformation/tree/main",
            color=self.bot.config.embed_color,
        )
        embed.add_field(name="Written by", value="<@160074289289101313>")
        embed.add_field(name="version", value=VERSION)
        await ctx.reply(embed=embed, mention_author=False, ephemeral=True)

    @commands.hybrid_command(name="shutdown")
    @commands.check(check_permitted)
    async def shutdown(self, ctx: commands.Context):
        """
        Shut down the bot.
        """

        self.bot.log_action(ctx, "Shut down the bot")
        # TODO: cache active pins to be reloaded on restart
        await ctx.reply("Shutting down...", ephemeral=True)
        await sleep(1)
        await self.bot.close()
        exit()

    @commands.hybrid_command(name="manageuser")
    @commands.check(check_permitted)
    async def manage_user(self, ctx: commands.Context, user_id: str, action: Literal["add", "remove"]):
        """
        Add or remove a user from the bot permissions.
        """
        if not self.bot.get_user(int(user_id)):
            await ctx.reply(f"No user with {user_id} found.", ephemeral=True)
            return
        if action == "add":
            if user_id in self.bot.config.permitted_users:
                await ctx.reply("User already in permitted list!", ephemeral=True)
                return
            self.bot.config.permitted_users.append(user_id)
            self.bot.log_action(ctx, f"Added {user_id} to user permissions")
        if action == "remove":
            if user_id not in self.bot.config.permitted_users:
                await ctx.reply("User not in permitted list!", ephemeral=True)
                return
            self.bot.config.permitted_users.remove(user_id)
            self.bot.log_action(ctx, f"Removed {user_id} from user permissions")
        self.bot.config.write_config_to_json()

    @commands.hybrid_command(name="managerole")
    @commands.check(check_permitted)
    async def manage_role(self, ctx: commands.Context, role_id: str, action: Literal["add", "remove"]):
        """
        Add or remove a role from the bot permissions.
        """
        if int(role_id) not in ctx.guild.roles:
            await ctx.reply(f"No role with {role_id} found.", ephemeral=True)
            return
        if action == "add":
            if role_id in self.bot.config.permitted_roles:
                await ctx.reply("Role already in permitted list!", ephemeral=True)
                return
            self.bot.config.permitted_roles.append(role_id)
            self.bot.log_action(ctx, f"Added {role_id} to role permissions")
        if action == "remove":
            if role_id not in self.bot.config.permitted_roles:
                await ctx.reply("Role not in permitted list!", ephemeral=True)
                return
            self.bot.config.permitted_roles.remove(role_id)
            self.bot.log_action(ctx, f"Removed {role_id} from role permissions")
        self.bot.config.write_config_to_json()

    @commands.hybrid_command(name="reload")
    @commands.check(check_permitted)
    async def reload(self, ctx: commands.Context):
        reloaded = await self.bot.reload_extensions()
        if reloaded:
            await ctx.reply(f"Sucessfully reloaded {', '.join(reloaded)}", ephemeral=True)
        else:
            await ctx.reply("Failed to reload extensions", ephemeral=True)
        self.bot.log_action(ctx, "Reloaded the bot")


async def setup(bot: PinformationBot):
    await bot.add_cog(ManagementCog(bot))
