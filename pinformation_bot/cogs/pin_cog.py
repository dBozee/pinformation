import logging
from asyncio import Task, create_task, gather
from collections.abc import Coroutine
from datetime import UTC, datetime, timedelta
from textwrap import dedent
from typing import cast

import discord
from discord import app_commands
from discord.ext import commands
from discord.message import Message, PartialMessage
from discord.state import TextChannel

from pinformation_bot.modals.multiline_modal import MultilineModal

from ..pinformation import PinformationBot, truncate
from ..pins import EmbedPin, PinChannel, PinUnion, SpeedTypes, TextPin
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

    @app_commands.command(name="pintext", description="Pin a text-based message to the current channel.")
    @app_commands.check(check_permitted)
    async def pin_text(
        self,
        interaction: discord.Interaction[PinformationBot],
        speed: int = 1,
        speed_type: SpeedTypes = SpeedTypes.messages,
    ):
        """Pops up a modal to receive the multiline text pin content."""
        channel = interaction.channel
        if not channel:
            return

        async def modal_callback(inter: discord.Interaction[PinformationBot], text: str | None):
            if not text:
                await handle_reply(inter, "Text content cannot be empty!", ephemeral=True)
                return

            if len(text) > 2000:
                await handle_reply(
                    inter,
                    f"Content exceeds Discord's 2,000 character limit after resolving mentions/emojis ({len(text)} chars).",  # noqa: E501
                    ephemeral=True,
                )
                return

            _ = await inter.response.defer(ephemeral=True)
            async with ChannelLock(channel.id):
                pin = await self._create_text_pin(channel, channel.id, text, speed, speed_type)
                await handle_reply(inter, "Added text pin!")

            if not inter.user.bot:
                await self.bot.log_pin_change(inter, "Added Text Pin", pin)

        modal = MultilineModal(
            title="Create Text Pin",
            label="Pin Content",
            style=discord.TextStyle.paragraph,
            default_value=None,
            callback_func=modal_callback,
            required=True,
            text_only=True,
        )
        _ = await interaction.response.send_modal(modal)

    @app_commands.command(name="pinembed", description="Pin an embed-based message to the current channel.")
    @app_commands.check(check_permitted)
    async def pin_embed(
        self,
        interaction: discord.Interaction[PinformationBot],
        title: str | None = None,
        url: str | None = None,
        image_url: str | None = None,
        image_file: discord.Attachment | None = None,
        color: int | None = None,
        speed: int = 1,
        speed_type: SpeedTypes = SpeedTypes.messages,
    ):
        """Pops up a modal to collect embed body text, with native attachment support."""
        channel = interaction.channel
        if not channel:
            return

        final_image = image_url or (image_file.url if image_file else None)

        async def modal_callback(inter: discord.Interaction[PinformationBot], text: str | None):
            body_text = text or ""
            embed_title = title

            if not any((body_text, embed_title, final_image)):
                await handle_reply(inter, "You must provide at least one of text, title, or image!", ephemeral=True)
                return

            _ = await inter.response.defer(ephemeral=True)

            if not embed_title and url:
                embed_title = url

            async with ChannelLock(channel.id):
                pin = await self._create_embed_pin(
                    channel,
                    channel.id,
                    embed_title,
                    body_text,
                    url,
                    final_image,
                    color or self.bot.config.embed_color,
                    speed,
                    speed_type,
                )
                await handle_reply(inter, "Added embed pin!")

            if not inter.user.bot:
                await self.bot.log_pin_change(inter, "Added Embed Pin", pin)

        modal = MultilineModal(
            title="Create Embed Pin",
            label="Embed Text / Description",
            style=discord.TextStyle.paragraph,
            default_value=None,
            callback_func=modal_callback,
            required=False,
        )
        _ = await interaction.response.send_modal(modal)

    @app_commands.command(name="pinstop", description="Stop active pin in this channel.")
    @app_commands.check(check_permitted)
    async def pin_stop(self, interaction: discord.Interaction[PinformationBot]):
        channel_id: int | None = interaction.channel_id
        if not channel_id or not (pin := await get_pin(interaction, self.bot, channel_id)):
            return

        _ = await interaction.response.defer(ephemeral=True)

        async with ChannelLock(channel_id):
            if interaction.channel:
                _ = create_task(delete_old_message(interaction.channel, pin.last_message))
            pin.active = False
            pin.last_message = None
            await handle_reply(interaction, "Removed pin!")
            self.bot.database.remove_pin(channel_id)
            ChannelLock.cleanup(channel_id)
            await self.bot.log_pin_change(interaction, "Removed Pin", pin)

    @app_commands.command(name="pinrestart", description="Restart the last active pin in this channel.")
    @app_commands.check(check_permitted)
    async def pin_restart(self, interaction: discord.Interaction[PinformationBot]):
        channel_id: int | None = interaction.channel_id
        channel = interaction.channel
        if not channel_id or not channel or not (pin := await get_pin(interaction, self.bot, channel_id)):
            return

        _ = await interaction.response.defer(ephemeral=True)

        async with ChannelLock(channel_id):
            new_message = await pin.send_to(channel)
            pin.last_message = new_message.id
            pin.last_message_dt = datetime.now(UTC)
            pin.active = True
            await handle_reply(interaction, "Re-activated pin!")
            await self.bot.log_pin_change(interaction, "Restarted Pin", pin)
            _ = create_task(self._db_update(pin))

    @app_commands.command(name="getpintext", description="Get the text content of this channel's pin.")
    @app_commands.check(check_permitted)
    async def get_pin_text(self, interaction: discord.Interaction[PinformationBot]) -> None:
        channel_id: int | None = interaction.channel_id
        if not channel_id or not (pin := await get_pin(interaction, self.bot, channel_id)):
            return

        _ = await interaction.response.defer(ephemeral=True)

        async with ChannelLock(channel_id):
            embed = discord.Embed(description=f"```json\n{truncate(pin.text, 4096)}```")
            _ = embed.add_field(name="Pin Type", value=f"`{pin.pin_type}`")
            _ = embed.add_field(name="Pin Speed", value=f"`{pin.speed} {pin.speed_type}`")
            _ = embed.add_field(name="Text Length", value=f"`{len(pin.text)}`")
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="pinspeed", description="Set the speed for this channel's pin.")
    @app_commands.check(check_permitted)
    async def pin_speed(
        self,
        interaction: discord.Interaction[PinformationBot],
        speed: int,
        speed_type: SpeedTypes | None = None,
    ):
        channel_id: int | None = interaction.channel_id
        if not channel_id or not (pin := await get_pin(interaction, self.bot, channel_id)):
            return

        _ = await interaction.response.defer(ephemeral=True)

        async with ChannelLock(channel_id):
            pin.speed = speed
            if speed_type is not None:
                pin.speed_type = speed_type

            channel_name = getattr(interaction.channel, "name", f"Channel {channel_id}")
            await handle_reply(interaction, f"Set #{channel_name} pin to {speed} {pin.speed_type}")
            await self.bot.log_pin_change(interaction, f"Changed speed to {speed} {pin.speed_type}", pin)

    @app_commands.command(name="allpins", description="Get a listing of all active pins in all channels.")
    @app_commands.check(check_permitted)
    async def get_all_pins(self, interaction: discord.Interaction[PinformationBot]):
        if not self.bot.pins:
            await handle_reply(interaction, "No active pins!", ephemeral=True)
            return

        embed = discord.Embed(
            title="All Pins",
            type="rich",
            color=self.bot.config.embed_color or 14517504,
        )
        for channel_id, pin_obj in self.bot.pins.items():
            target_channel = self.bot.get_channel(channel_id)
            mention: str = target_channel.mention if target_channel else f"<#{channel_id}>"  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue, reportUnknownVariableType]
            _ = embed.add_field(
                name=mention,
                value=pin_obj.get_self_data(),
                inline=False,
            )
        _ = await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="pinhelp", description="Pinformation command reference.")
    async def pin_help(self, interaction: discord.Interaction[PinformationBot]):
        embed = discord.Embed(
            title="Pinformation command reference",
            type="rich",
            color=self.bot.config.embed_color or 14517504,
        )
        _ = embed.add_field(
            name="Multiline Inputs:",
            value=dedent("""
            Emojis can be used like :kekw:, mention roles/users by @role/user, mention channels with #channel.
            All of the above can also be used with the ID for a given role/user/channel, or by using the <> syntax
            """),
        )
        for pin_field in long_responses.help_pins:
            _ = embed.add_field(**pin_field, inline=False)
        for mgmt_field in long_responses.help_management:
            _ = embed.add_field(**mgmt_field, inline=False)

        _ = await interaction.response.send_message(embed=embed, ephemeral=True)

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
                    channel_name = getattr(message.channel, "name", f"Channel {message.channel.id}")

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
                        log.debug(f"Time not yet elapsed in {channel_name}. Next update: {delta.isoformat()}")

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
        if not pin_list:
            return

        tasks: list[Task[None]] = [create_task(self._restart_single_pin(pin)) for pin in pin_list]
        _ = await gather(*tasks, return_exceptions=True)

    async def _create_text_pin(
        self,
        channel: PinChannel,
        channel_id: int,
        text: str,
        speed: int = 1,
        speed_type: SpeedTypes = SpeedTypes.messages,
    ) -> TextPin:
        if existing_pin := self.bot.pins.get(channel_id):
            _ = create_task(delete_old_message(channel, existing_pin.last_message))

        pin = TextPin(channel_id=channel_id, text=text, speed=speed, speed_type=speed_type)
        self.bot.pins[channel_id] = pin
        message = await pin.send_to(channel)
        pin.last_message = message.id
        pin.last_message_dt = datetime.now(UTC)
        self.bot.database.add_or_update_pin(pin)
        return pin

    async def _create_embed_pin(
        self,
        channel: PinChannel,
        channel_id: int,
        title: str | None = None,
        text: str = "",
        url: str | None = None,
        image: str | None = None,
        color: int | None = None,
        speed: int = 1,
        speed_type: SpeedTypes = SpeedTypes.messages,
    ) -> EmbedPin:
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
        message = await pin.send_to(channel)
        pin.last_message = message.id
        pin.last_message_dt = datetime.now(UTC)
        self.bot.database.add_or_update_pin(pin)
        return pin


async def setup(bot: PinformationBot):
    await bot.add_cog(PinCog(bot))
