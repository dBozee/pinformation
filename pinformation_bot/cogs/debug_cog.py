from asyncio import sleep

from discord.ext import commands

from pinformation_bot.pinformation import PinformationBot

from ..utils.utils import check_permitted


class DebugCog(commands.Cog):
    def __init__(self, pin_bot: PinformationBot) -> None:
        self.bot: PinformationBot = pin_bot

    @commands.hybrid_command(name="shutdown")
    @commands.check(check_permitted)
    async def shutdown(self, ctx: commands.Context[PinformationBot]):
        """
        Shut down the bot.
        """

        self.bot.log_action(ctx, "Shut down the bot")
        _ = await ctx.reply("Shutting down...", ephemeral=True)
        await sleep(1)
        self.bot.database.db.close()
        await self.bot.close()
        exit()

    @commands.hybrid_command(name="reload")
    @commands.check(check_permitted)
    async def reload(self, ctx: commands.Context[PinformationBot]):
        reloaded = await self.bot.reload_extensions()
        if reloaded:
            _ = await ctx.reply(f"Successfully reloaded {', '.join(reloaded)}", ephemeral=True)
        else:
            _ = await ctx.reply("Failed to reload extensions", ephemeral=True)
        self.bot.log_action(ctx, "Reloaded the bot")


async def setup(bot: PinformationBot):
    await bot.add_cog(DebugCog(bot))
