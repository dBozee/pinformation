from asyncio import create_task
from datetime import UTC, datetime

from discord.ext import commands

from ..pinformation import PinformationBot
from ..pins import EmbedPin, PinUnion
from ..utils.channel_lock import ChannelLock
from ..utils.utils import check_permitted, delete_old_message, get_pin, handle_reply


class UpdateCog(commands.Cog):
    def __init__(self, pin_bot: PinformationBot) -> None:
        self.bot: PinformationBot = pin_bot

    @commands.hybrid_command(name="updatetext")
    @commands.check(check_permitted)
    async def update_pin(self, ctx: commands.Context[PinformationBot], *, text: str | None):
        """Update this channel's existing pin's text/description"""
        if not text and self.bot.pins[ctx.channel.id].pin_type == "text":
            _ = await ctx.reply("Cannot remove text from a text pin...", ephemeral=True)
            return
        await self._update_pin_attribute(ctx, "text", text, require_embed=False)
        await self.bot.log_pin_change(ctx, f"Updated pin text in {ctx.channel.mention} to: {text}")  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]

    @commands.hybrid_command(name="updatetitle")
    @commands.check(check_permitted)
    async def update_title(self, ctx: commands.Context[PinformationBot], title: str | None):
        """Update this channel's existing pin's title. (embed only)"""
        await self._update_pin_attribute(ctx, "title", title)
        await self.bot.log_pin_change(ctx, f"Updated pin title in {ctx.channel.mention} to: {title}")  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]

    @commands.hybrid_command(name="updateurl")
    @commands.check(check_permitted)
    async def update_url(self, ctx: commands.Context[PinformationBot], url: str):
        """Update this channel's existing pin's url. (embed only)"""
        await self._update_pin_attribute(ctx, "url", url)
        await self.bot.log_pin_change(ctx, f"Updated pin url in {ctx.channel.mention} to: {url}")  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]

    @commands.hybrid_command(name="updateimage")
    @commands.check(check_permitted)
    async def update_img(self, ctx: commands.Context[PinformationBot], url: str | None):
        """Update this channel's existing pin's image url. (embed only)"""
        if not url and ctx.message.attachments:
            url = ctx.message.attachments[0].url
        await self._update_pin_attribute(ctx, "image", url)
        await self.bot.log_pin_change(ctx, f"Updated pin image url in {ctx.channel.mention} to: {url or 'none'}")  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]

    @commands.hybrid_command(name="updatecolor")
    @commands.check(check_permitted)
    async def update_color(self, ctx: commands.Context[PinformationBot], color: int):
        """Update this channel's existing pin's color. (embed only)"""
        await self._update_pin_attribute(ctx, "color", color)
        await self.bot.log_pin_change(ctx, f"Updated pin color in {ctx.channel.mention} to: {color}")  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]

    async def _update_pin_attribute(
        self,
        ctx: commands.Context[PinformationBot],
        attribute_name: str,
        value: str | int | None,
        require_embed: bool = True,
    ):
        """Generic method to update a pin attribute"""
        channel = ctx.channel
        async with ChannelLock(channel.id):
            pin = await get_pin(ctx, self.bot, channel.id)
            if not pin:
                return

            if require_embed and not await self._is_embed(ctx, pin):
                return
            _ = create_task(delete_old_message(ctx.message.channel, pin.last_message))
            setattr(pin, attribute_name, value)
            if isinstance(pin, EmbedPin):
                pin.rebuild_embed()

            message = await pin.send_to(channel)

            pin.last_message = message.id
            pin.last_message_dt = datetime.now(UTC)
            self.bot.database.add_or_update_pin(pin)
            await handle_reply(ctx, f"Updated pin {attribute_name}!")

    @staticmethod
    async def _is_embed(ctx: commands.Context[PinformationBot], pin: PinUnion) -> bool:
        if isinstance(pin, EmbedPin):
            return True
        await handle_reply(ctx, "Pin is not an embed!", False)
        return False


async def setup(bot: PinformationBot):
    await bot.add_cog(UpdateCog(bot))
