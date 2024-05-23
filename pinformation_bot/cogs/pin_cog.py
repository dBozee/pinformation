from logging import getLogger
from typing import Any, Optional

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
        await self._restart_active_pins(self.bot.database.get_cached_pins())

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
    async def pin_text(
        self,
        ctx: commands.Context,
        text: str,
        speed_msgs: Optional[int] = 1,
    ):
        """
        Pin a text based message to the current channel. Can use emojis.
        """
        pin = TextPin(channel_id=ctx.channel.id, text=text, speed_msgs=speed_msgs)
        self.bot.pins[ctx.channel.id] = pin
        message = await ctx.channel.send(pin.text, suppress_embeds=True)
        pin.last_message = message.id
        self.bot.database.add_or_update_pin(pin.__dict__)

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
        speed_msgs: Optional[int] = 1,
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
            speed_msgs=speed_msgs,
        )
        self.bot.pins[ctx.channel.id] = pin
        message = await ctx.channel.send(embed=pin.embed)
        pin.last_message = message.id
        self.bot.database.add_or_update_pin(pin.__dict__)

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
        self.bot.database.remove_pin(ctx.channel.id)

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
        # FUTURE: time based pins? Combination of message/time whichever is first?

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

    async def _restart_active_pins(self, pin_list: list[Optional[dict[str, Any]]]):
        for pin_data in pin_list:
            filtered_dict = {k: v for k, v in pin_data.items() if v}

            chann_id = filtered_dict.get("channel_id")
            channel = self.bot.get_channel(int(chann_id))
            last_bot_msg = await channel.fetch_message(filtered_dict.get("last_message"))
            context = await self.bot.get_context(last_bot_msg)

            # remove elements that are no longer needed
            [filtered_dict.pop(key) for key in ["active", "channel_id", "last_message"]]
            if filtered_dict.get("title"):  # check if it's an embed

                await self.pin_embed(context, **filtered_dict)
            else:

                await self.pin_text(context, **filtered_dict)
            await last_bot_msg.delete()


async def setup(bot: PinformationBot):
    await bot.add_cog(PinCog(bot))
