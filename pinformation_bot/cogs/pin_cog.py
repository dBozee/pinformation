from logging import getLogger
from typing import Optional

import discord
from discord.ext import commands

from ..bot_config import check_permitted
from ..pinformation import PinformationBot
from ..pins import EmbedPin, PollPin, TextPin

log = getLogger(__name__)


class PinCog(commands.Cog, name="Pin"):  # TODO: cache active pins to be reloaded on restart
    def __init__(self, pin_bot: PinformationBot) -> None:
        self.bot: PinformationBot = pin_bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        log.info("Pin cog is ready!")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return
        # TODO: some sort of counter by channel?

    @commands.hybrid_command(name="pintext")
    @commands.check(check_permitted)
    async def pin_text(self, ctx: commands.Context, text: str):
        """
        Pin a text based message to the current channel. Can use emojis.
        """
        pin = TextPin(channel_id=ctx.channel.id, text=text)
        self.bot.pins[ctx.channel.id] = pin
        await ctx.reply("Started text pin!", ephemeral=True)
        ctx.send(pin.text)
        # TODO: add some sort of cache for pins to persist.

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
        await ctx.send(embed=pin.embed)
        # TODO: add some sort of cache

    @commands.hybrid_command(name="pinpoll")
    @commands.check(check_permitted)
    async def pin_poll(
        self,
        ctx: commands.Context,
        title: str,
        options: str,
        color: Optional[int],
    ):
        """
        Pin a poll to the current channel.
        Options should be comma separated values. Ex: Option1,Option2,Option3
        Requires active pin.
        """
        pin = PollPin(
            channel_id=ctx.channel.id,
            title=title,
            options=options.split(","),
            color=color or self.bot.config.embed_color,
        )
        self.bot.pins[ctx.channel.id] = pin
        await ctx.reply("Started embed pin!", ephemeral=True)
        await ctx.send(embed=pin.embed)
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
        self.bot.pins.pop(ctx.channel.id)
        await ctx.reply("Removed pin!", ephemeral=True)

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
        self.bot.pins[ctx.channel.id].speed = speed
        await ctx.reply(f"{ctx.channel.name} set to {speed} messages", ephemeral=True)
        # TODO: adjust speed of pin message. Either in message count or time.

    @commands.hybrid_command(name="allpins")
    @commands.check(check_permitted)
    async def get_all_pins(self, ctx: commands.Context):
        embed = discord.Embed(
            title="All Pins",
            type="rich",
            color=self.bot.config.embed_color or 14517504,
        )
        for channel_id, pin_obj in self.bot.pins:
            # FUTURE: embed max field is 25. What if there are more than 25 pins?
            embed.add_field(name=self.bot.get_channel(channel_id).name, value=pin_obj.get_self_data())
        await ctx.reply(embed=embed, ephemeral=True)


async def setup(bot: PinformationBot):
    await bot.add_cog(PinCog(bot))
