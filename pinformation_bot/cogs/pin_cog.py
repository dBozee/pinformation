from logging import getLogger
from typing import Optional

import discord
from discord.ext import commands

from ..bot_config import check_permitted
from ..pinformation import PinformationBot
from ..pins import EmbedPin, TextPin

log = getLogger(__name__)


class PinCog(commands.Cog, name="Pin"):  # TODO: cache active pins to be reloaded on restart
    def __init__(self, pin_bot: PinformationBot) -> None:
        self.bot: PinformationBot = pin_bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        log.info("Pin cog is ready!")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.id in self.bot.pins:
            chann_id = message.channel.id
            if not message.author.bot and self.bot.pins[chann_id].active:
                self.bot.pins[chann_id].increment_msg_count()
                if self.bot.pins[chann_id].msg_count >= self.bot.pins[chann_id].speed_msgs:
                    await self._update_pin_message(message)

    @commands.hybrid_command(name="pintext")
    @commands.check(check_permitted)
    async def pin_text(self, ctx: commands.Context, text: str):
        """
        Pin a text based message to the current channel. Can use emojis.
        """
        pin = TextPin(channel_id=ctx.channel.id, text=text)
        self.bot.pins[ctx.channel.id] = pin
        await ctx.reply("Started text pin!", ephemeral=True)
        message = await ctx.channel.send(pin.text)
        pin.last_message = message.id
        # TODO: add some sort of cache for pins to persist through crashes/restarts

    @commands.hybrid_command(name="pinembed")
    @commands.check(check_permitted)
    async def pin_embed(
        self,
        ctx: commands.Context,
        title: str,
        text: str,
        url: Optional[str] = None,
        image: Optional[str] = None,
        color: Optional[int] = None,
    ):
        """
        Pin an embed based message to the current channel.
        """
        pin = EmbedPin(
            channel_id=ctx.channel.id,
            title=title,
            text=text,
            url=url,
            image=image,
            color=color or self.bot.config.embed_color,
        )
        self.bot.pins[ctx.channel.id] = pin
        await ctx.reply("Started embed pin!", ephemeral=True)
        message = await ctx.channel.send(embed=pin.embed)
        pin.last_message = message.id
        # TODO: add some sort of cache

    @commands.hybrid_command(name="pinstop")
    @commands.check(check_permitted)
    async def pin_stop(self, ctx: commands.Context):
        """
        Stop active pin in this channel.
        """
        if not self.bot.pins.get(ctx.channel.id):
            await ctx.reply("No pin in channel!", ephemeral=True)
            return
        last_bot_msg = await ctx.message.channel.fetch_message(self.bot.pins[ctx.channel.id].last_message)
        await last_bot_msg.delete()
        self.bot.pins[ctx.channel.id].active = False
        await ctx.reply("Removed pin!", ephemeral=True)

    @commands.hybrid_command(name="pinrestart")
    @commands.check(check_permitted)
    async def pin_restart(self, ctx: commands.Context):
        """
        Restart last active pin in this channel.
        """
        if not self.bot.pins.get(ctx.channel.id):
            await ctx.reply("No previous pin in channel!", ephemeral=True)
            return
        new_message = await ctx.channel.send(**self.bot.pins[ctx.channel.id]._rebuild_msg())
        self.bot.pins[ctx.channel.id].last_message = new_message.id
        self.bot.pins[ctx.channel.id].active = True
        await ctx.reply("re-activated pin!", ephemeral=True)

    @commands.hybrid_command(name="pinspeed")
    @commands.check(check_permitted)
    async def pin_speed(self, ctx: commands.Context, speed: int):
        """
        Set the speed for this channel's pin.
        Requires active pin.
        """
        if not self.bot.pins.get(ctx.channel.id):
            await ctx.reply("No pin in channel!", ephemeral=True)
            return
        self.bot.pins[ctx.channel.id].speed_msgs = speed
        await ctx.reply(f"Set #{ctx.channel.name} pin to {speed} messages", ephemeral=True)
        # TODO: adjust speed of pin message. Either in message count or time.

    @commands.hybrid_command(name="allpins")
    @commands.check(check_permitted)
    async def get_all_pins(self, ctx: commands.Context):
        if not self.bot.pins:
            await ctx.reply("No active pins!", ephemeral=True)
            return
        embed = discord.Embed(
            title="All Pins",
            type="rich",
            color=self.bot.config.embed_color or 14517504,
        )
        for channel_id, pin_obj in self.bot.pins.items():
            # FUTURE: embed max field is 25. What if there are more than 25 pins?
            embed.add_field(name=f"#{self.bot.get_channel(channel_id).name}", value=pin_obj.get_self_data())
        await ctx.reply(embed=embed, ephemeral=True)

    async def _update_pin_message(self, message: discord.Message):
        chann_id = message.channel.id
        last_bot_msg = await message.channel.fetch_message(self.bot.pins[chann_id].last_message)
        await last_bot_msg.delete()
        new_msg = await message.channel.send(**self.bot.pins[chann_id]._rebuild_msg())
        self.bot.pins[chann_id].msg_count = 0
        self.bot.pins[chann_id].last_message = new_msg.id


async def setup(bot: PinformationBot):
    await bot.add_cog(PinCog(bot))
