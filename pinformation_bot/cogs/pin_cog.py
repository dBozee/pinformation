import logging
from asyncio import Task, create_task, gather
from collections.abc import Coroutine
from datetime import UTC, datetime, timedelta
from typing import cast

import discord
from discord.ext import commands
from discord.message import Message, PartialMessage
from discord.state import TextChannel

from ..pinformation import PinformationBot
from ..pins import EmbedPin, PinUnion, SpeedTypes, TextPin
from ..utils.channel_lock import ChannelLock
from ..utils.utils import check_permitted, delete_old_message, get_pin, handle_reply
from . import long_responses

log = logging.getLogger(__name__)


class PinCog(commands.Cog, name="Pin"):
    def __init__(self, pin_bot: PinformationBot) -> None:
        self.bot: PinformationBot = pin_bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        log.info("Pin cog is ready!")
        await self._restart_active_pins(self.bot.database.get_persisted_pins())

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.content.startswith(self.bot.config.prefix):
            return
        channel_id = message.channel.id

        if channel_id in self.bot.pins and (pin_data := self.bot.pins.get(channel_id)) and pin_data.active:
            await self._handle_counter(pin_data, message)

    @commands.hybrid_command(name="pintext")
    @commands.check(check_permitted)
    async def pin_text(
        self,
        ctx: commands.Context[PinformationBot],
        *,
        text: str,
        speed: int = 1,
        speed_type: SpeedTypes = SpeedTypes.messages,
        reply: bool = True,
    ):
        """Pin a text-based message to the current channel. Can use emojis."""
        channel = ctx.channel
        async with ChannelLock(channel.id):
            pin = await self._create_text_pin(channel, channel.id, text, speed, speed_type)
            await handle_reply(ctx, "Added text pin!", reply=reply)
        if not ctx.author.bot:
            await self.bot.log_pin_change(ctx, "Added Text Pin", pin)

    @commands.hybrid_command(name="pinembed")
    @commands.check(check_permitted)
    async def pin_embed(
        self,
        ctx: commands.Context[PinformationBot],
        *,
        text: str | None = None,
        title: str | None = None,
        url: str | None = None,
        image: str | None = None,
        color: int | None = None,
        speed: int = 1,
        speed_type: SpeedTypes = SpeedTypes.messages,
        reply: bool = True,
    ):
        """Pin an embed-based message to the current channel."""
        channel = ctx.channel
        if not any((text, title, image)):
            _ = await ctx.reply("You must provide at least one of text, title, or image!", ephemeral=True)
            return
        async with ChannelLock(channel.id):
            if not image and ctx.message.attachments:
                image = ctx.message.attachments[0].url
            if text is None:
                text = ''
            if not title and url:
                title = url
            pin = await self._create_embed_pin(
                channel, channel.id, title, text, url, image, color or self.bot.config.embed_color, speed, speed_type
            )
            await handle_reply(ctx, "Added embed pin!", reply=reply)
        if not ctx.author.bot:
            await self.bot.log_pin_change(ctx, "Added Embed Pin", pin)

    @commands.hybrid_command(name="pinstop")
    @commands.check(check_permitted)
    async def pin_stop(self, ctx: commands.Context[PinformationBot]):
        """
        Stop active pin in this channel.
        """
        channel_id: int = ctx.channel.id
        if not (pin := await get_pin(ctx, self.bot, channel_id)):
            return
        async with ChannelLock(ctx.channel.id):
            _ = create_task(delete_old_message(ctx.message.channel, pin.last_message))
            pin.active = False
            pin.last_message = None
            _ = await ctx.reply("Removed pin!", ephemeral=ctx.interaction is not None)
            self.bot.database.remove_pin(channel_id)
            ChannelLock.cleanup(channel_id)
            await self.bot.log_pin_change(ctx, "Removed Pin", pin)

    @commands.hybrid_command(name="pinrestart")
    @commands.check(check_permitted)
    async def pin_restart(self, ctx: commands.Context[PinformationBot]):
        """
        Restart the last active pin in this channel.
        """
        channel_id: int = ctx.channel.id
        if not (pin := await get_pin(ctx, self.bot, channel_id)):
            return
        async with ChannelLock(channel_id):
            new_message = await pin.send_to(ctx.channel)
            pin.last_message = new_message.id
            pin.last_message_dt = datetime.now(UTC)
            pin.active = True
            if ctx.interaction is not None:
                _ = await ctx.reply("re-activated pin!", ephemeral=True)
            await self.bot.log_pin_change(ctx, "Restarted Pin", pin)
            _ = create_task(self._db_update(pin))

    @commands.hybrid_command(name="getpintext")
    @commands.check(check_permitted)
    async def get_pin_text(self, ctx: commands.Context[PinformationBot]) -> None:
        """
        Get the text content of this channel's pin.
        Requires active pin.
        """
        channel_id: int = ctx.channel.id
        if not (pin := await get_pin(ctx, self.bot, channel_id)):
            return
        async with ChannelLock(channel_id):
            embed = discord.Embed()
            _ = embed.add_field(name="Pin Type", value=f"`{pin.pin_type}`")
            _ = embed.add_field(name="Pin Speed", value=f"`{pin.speed} {pin.speed_type}`")
            _ = embed.add_field(name="Pin text", value=f"```json\n{pin.text}```", inline=False)
            _ = await ctx.reply(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="pinspeed")
    @commands.check(check_permitted)
    async def pin_speed(self, ctx: commands.Context[PinformationBot], speed: int, speed_type: SpeedTypes | None = None):
        """
        Set the speed for this channel's pin.
        Requires active pin.
        """
        channel_id: int = ctx.channel.id
        if not (pin := await get_pin(ctx, self.bot, channel_id)):
            return
        async with ChannelLock(channel_id):
            pin.speed = speed
            if speed_type is not None:
                pin.speed_type = speed_type
            _ = await ctx.reply(f"Set #{ctx.channel.name} pin to {speed} {pin.speed_type}", ephemeral=True)  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
            await self.bot.log_pin_change(ctx, f"Changed speed to {speed} {pin.speed_type}", pin)

    @commands.hybrid_command(name="allpins")
    @commands.check(check_permitted)
    async def get_all_pins(self, ctx: commands.Context[PinformationBot]):
        """
        Get a listing of all active pins in all channels
        """
        if not self.bot.pins:
            _ = await ctx.reply("No active pins!", ephemeral=True)
            return
        embed = discord.Embed(
            title="All Pins",
            type="rich",
            color=self.bot.config.embed_color or 14517504,
        )
        for channel_id, pin_obj in self.bot.pins.items():
            # FUTURE: embed max field is 25. What if there are more than 25 pins?
            _ = embed.add_field(
                name=f"{self.bot.get_channel(channel_id).mention}",  # pyright: ignore [reportAttributeAccessIssue, reportOptionalMemberAccess, reportUnknownMemberType]
                value=pin_obj.get_self_data(),
                inline=False,
            )
        _ = await ctx.reply(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="pinhelp")
    async def pin_help(self, ctx: commands.Context[PinformationBot]):
        embed = discord.Embed(
            title="Pinformation command reference",
            type="rich",
            color=self.bot.config.embed_color or 14517504,
        )
        for pin_field in long_responses.help_pins:
            _ = embed.add_field(**pin_field, inline=False)
        for mgmt_field in long_responses.help_management:
            _ = embed.add_field(**mgmt_field, inline=False)

        _ = await ctx.reply(embed=embed, ephemeral=True)

    async def _handle_counter(self, pin: PinUnion, message: discord.Message) -> None:
        message_id = message.channel.id
        if ChannelLock.is_locked(message.channel.id):
            log.debug(f"Lock was already acquired in channel with ID: {message_id}. Skipping.")
            return
        async with ChannelLock(message.channel.id):
            match pin.speed_type:
                case SpeedTypes.messages:
                    pin.increment_msg_count()
                    if pin.msg_count >= pin.speed:
                        pin.msg_count = 0
                        await self._update_pin_message(message)
                case SpeedTypes.seconds:
                    last_dt = pin.last_message_dt
                    channel_name = message.channel.name  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue, reportUnknownVariableType]

                    if not last_dt and pin.last_message:
                        try:
                            log.debug(f"Pin in {channel_name} didn't have last_message_dt stored. ")
                            found_msg = await message.channel.fetch_message(pin.last_message)
                            last_dt = found_msg.created_at
                        except discord.NotFound:
                            log.warning("Failed to get last message from server.")
                    if not last_dt:
                        log.warning(f"Time-based pin in {channel_name} missing last_dt")
                        return

                    delta: datetime = last_dt + timedelta(seconds=pin.speed)
                    if delta <= datetime.now(tz=UTC):
                        await self._update_pin_message(message)
                    else:
                        log.debug(f"Time not yet elapsed in ${channel_name}. Next update: {delta.isoformat()}")

    async def _update_pin_message(self, message: discord.Message):
        channel_name = getattr(message.channel, "name", f"Channel {message.channel.id}")
        try:
            pin_data = self.bot.pins[message.channel.id]
            channel = message.channel

            old_message_id = pin_data.last_message

            send_coro: Coroutine[None, None, Message] = pin_data.send_to(channel)
            if (
                old_message_id
                and pin_data.active
                and isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.Thread))
            ):
                old_msg_partial: PartialMessage = channel.get_partial_message(old_message_id)
                delete_coro: Coroutine[None, None, None] = old_msg_partial.delete()

                res_send, res_delete = await gather(send_coro, delete_coro, return_exceptions=True)
                if isinstance(res_delete, BaseException):
                    log.warning(f"Failed to delete old message concurrently: {res_delete}")
            else:
                res_send = await send_coro

            if isinstance(res_send, BaseException):
                raise res_send

            pin_data.last_message = res_send.id
            pin_data.last_message_dt = datetime.now(UTC)

            _ = create_task(self._db_update(pin_data))
        except Exception:
            log.exception(f"Failed to update pin message in channel {channel_name}:")

    async def _db_update(self, pin: PinUnion) -> None:
        self.bot.database.add_or_update_pin(pin)

    async def _restart_single_pin(self, pin: PinUnion) -> None:
        try:
            channel = cast(TextChannel, await self.bot.fetch_channel(pin.channel_id))

            if pin.last_message:
                try:
                    last_bot_msg = await channel.fetch_message(pin.last_message)
                    log.info(
                        f"Last Message found for channel {channel.name} with ID {last_bot_msg.id}. Deleting old pin..."
                    )
                    await last_bot_msg.delete()
                except discord.NotFound:
                    log.warning(f"Old pin message {pin.last_message} not found in {channel.name}.")

            new_msg = await pin.send_to(channel)
            pin.last_message = new_msg.id
            pin.last_message_dt = datetime.now(UTC)

            self.bot.pins[pin.channel_id] = pin
            await self._db_update(pin)

        except Exception:
            log.exception(f"Failed to restart pin in channel {pin.channel_id}:")

    async def _restart_active_pins(self, pin_list: list[PinUnion]) -> None:
        """Restores cached pins from DB models concurrently on bot startup."""
        if not pin_list:
            return

        tasks: list[Task[None]] = [create_task(self._restart_single_pin(pin)) for pin in pin_list]
        _ = await gather(*tasks, return_exceptions=True)

    async def _create_text_pin(
        self,
        channel: discord.abc.Messageable,
        channel_id: int,
        text: str,
        speed: int = 1,
        speed_type: SpeedTypes = SpeedTypes.messages,
    ) -> TextPin:
        if existing_pin := self.bot.pins.get(channel_id):
            _ = create_task(delete_old_message(channel, existing_pin.last_message))

        pin = TextPin(channel_id=channel_id, text=text, speed=speed, speed_type=speed_type)
        self.bot.pins[channel_id] = pin
        message = await channel.send(pin.text)
        pin.last_message = message.id
        pin.last_message_dt = datetime.now(UTC)
        self.bot.database.add_or_update_pin(pin)
        return pin

    async def _create_embed_pin(
        self,
        channel: discord.abc.Messageable,
        channel_id: int,
        title: str | None = None,
        text: str = "",
        url: str | None = None,
        image: str | None = None,
        color: int | None = None,
        speed: int = 1,
        speed_type: SpeedTypes = SpeedTypes.messages,
    ):
        if existing_pin := self.bot.pins.get(channel_id):
            _ = create_task(delete_old_message(channel, existing_pin.last_message))

        pin = EmbedPin(
            channel_id=channel_id,
            title=title,
            text=text,
            url=url,
            image=image,
            color=color or self.bot.config.embed_color,
            speed=speed,
            speed_type=speed_type,
        )
        self.bot.pins[channel_id] = pin
        message = await channel.send(embed=pin.embed)
        pin.last_message = message.id
        pin.last_message_dt = datetime.now(UTC)
        self.bot.database.add_or_update_pin(pin)
        return pin


async def setup(bot: PinformationBot):
    await bot.add_cog(PinCog(bot))
