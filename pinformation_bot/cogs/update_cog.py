from asyncio import create_task
from datetime import UTC, datetime

from discord.ext import commands

from ..pinformation import PinformationBot
from ..pins import EmbedPin, Pin, TextPin
from ..utils import check_permitted, delete_old_message, handle_reply
from ..utils.channel_lock import ChannelLock
from ..utils.utils import get_pin


class UpdateCog(commands.Cog):
    def __init__(self, pin_bot: PinformationBot) -> None:
        self.bot: PinformationBot = pin_bot

    @commands.hybrid_command(name="updatetext")
    @commands.check(check_permitted)
    async def update_pin(self, ctx: commands.Context, *, text: str):
        """Update this channel's existing pin's text/description"""
        await self._update_pin_attribute(ctx, "text", text, require_embed=False)
        await self.bot.log_pin_change(ctx, f"Updated pin text in {ctx.channel.mention} to: {text}")

    @commands.hybrid_command(name="updatetitle")
    @commands.check(check_permitted)
    async def update_title(self, ctx: commands.Context, title: str):
        """Update this channel's existing pin's title. (embed only)"""
        await self._update_pin_attribute(ctx, "title", title)
        await self.bot.log_pin_change(ctx, f"Updated pin title in {ctx.channel.mention} to: {title}")

    @commands.hybrid_command(name="updateurl")
    @commands.check(check_permitted)
    async def update_url(self, ctx: commands.Context, url: str):
        """Update this channel's existing pin's url. (embed only)"""
        await self._update_pin_attribute(ctx, "url", url)
        await self.bot.log_pin_change(ctx, f"Updated pin url in {ctx.channel.mention} to: {url}")

    @commands.hybrid_command(name="updateimage")
    @commands.check(check_permitted)
    async def update_img(self, ctx: commands.Context, url: str):
        """Update this channel's existing pin's image url. (embed only)"""
        await self._update_pin_attribute(ctx, "image", url)
        await self.bot.log_pin_change(ctx, f"Updated pin image url in {ctx.channel.mention} to: {url}")

    @commands.hybrid_command(name="updatecolor")
    @commands.check(check_permitted)
    async def update_color(self, ctx: commands.Context, color: int):
        """Update this channel's existing pin's color. (embed only)"""
        await self._update_pin_attribute(ctx, "color", color)
        await self.bot.log_pin_change(ctx, f"Updated pin color in {ctx.channel.mention} to: {color}")

    async def _update_pin_attribute(
        self, ctx: commands.Context, attribute_name: str, value, require_embed: bool = True
    ):
        """Generic method to update a pin attribute"""
        channel = ctx.channel
        async with ChannelLock(channel.id):
            if not (pin := await get_pin(ctx, self.bot, channel.id)):
                return
            pin: TextPin | EmbedPin

            if require_embed and not await self._is_embed(ctx, pin):
                return
            create_task(delete_old_message(ctx.message.channel, pin.last_message))
            setattr(pin, attribute_name, value)
            if isinstance(pin, EmbedPin):
                pin.embed = pin.create_embed()
                message = await channel.send(embed=pin.embed)
            else:
                message = await channel.send(pin.text, suppress_embeds=True)

            pin.last_message = message.id
            pin.last_message_dt = datetime.now(UTC)
            self.bot.database.add_or_update_pin(pin.__dict__)
            await handle_reply(ctx, f"Updated pin {attribute_name}!")

    @staticmethod
    async def _is_embed(ctx: commands.Context, pin: Pin) -> bool:
        if isinstance(pin, EmbedPin):
            return True
        await handle_reply(ctx, "Pin is not an embed!", False)
        return False


async def setup(bot: PinformationBot):
    await bot.add_cog(UpdateCog(bot))
