import logging
from asyncio import create_task
from datetime import UTC, datetime

import discord
from discord import app_commands
from discord.ext import commands

from pinformation_bot.modals.multiline_modal import MultilineModal

from ..pinformation import PinformationBot
from ..pins import EmbedPin, PinUnion
from ..utils.channel_lock import ChannelLock
from ..utils.utils import check_permitted, delete_old_message, get_pin, handle_reply

log = logging.getLogger(__name__)


class UpdateCog(commands.Cog):
    def __init__(self, pin_bot: PinformationBot) -> None:
        self.bot: PinformationBot = pin_bot

    @app_commands.command(name="updatetext", description="Update this channel's existing pin's text/description")
    @app_commands.check(check_permitted)
    async def update_pin(self, interaction: discord.Interaction[PinformationBot]):
        """Opens a multi-line modal pop-up to edit the pin text."""
        pin: PinUnion | None = self.bot.pins.get(interaction.channel_id)  # pyright: ignore[reportArgumentType]
        if pin is None:
            _ = await interaction.response.send_message(f"Failed to find pin in {interaction.channel.mention}.")  # pyright: ignore[reportUnknownMemberType, reportOptionalMemberAccess, reportAttributeAccessIssue]
            return
        current_text = pin.text if pin else None

        async def modal_callback(inter: discord.Interaction[PinformationBot], text: str | None):
            if not text and pin and pin.pin_type == "text":
                _ = await inter.response.send_message("Cannot remove text from a text pin...", ephemeral=True)
                return

            _ = await inter.response.defer(ephemeral=True)

            await self._update_pin_attribute(inter, "text", text, require_embed=False)
            await self.bot.log_pin_change(inter, f"Updated pin text in {inter.channel.mention} to: {text}")  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue, reportOptionalMemberAccess]

        modal = MultilineModal(
            title="Update Pin Text",
            label="Pin Description / Text",
            style=discord.TextStyle.paragraph,
            default_value=current_text,
            callback_func=modal_callback,
            required=False,
            text_only=pin.pin_type == "text",
        )
        _ = await interaction.response.send_modal(modal)

    @app_commands.command(name="updatetitle", description="Update this channel's existing pin's title (embed only)")
    @app_commands.check(check_permitted)
    async def update_title(self, interaction: discord.Interaction[PinformationBot]):
        """Opens a modal pop-up to edit the pin title."""
        pin: PinUnion | None = self.bot.pins.get(interaction.channel_id)  # pyright: ignore[reportArgumentType]
        if pin is None:
            _ = await interaction.response.send_message(f"Failed to find pin in {interaction.channel.mention}.")  # pyright: ignore[reportUnknownMemberType, reportOptionalMemberAccess, reportAttributeAccessIssue]
            return
        current_title = getattr(pin, "title", None) if pin else None

        async def modal_callback(inter: discord.Interaction[PinformationBot], title: str | None):
            _ = await inter.response.defer(ephemeral=True)
            await self._update_pin_attribute(inter, "title", title)
            await self.bot.log_pin_change(inter, f"Updated pin title in {inter.channel.mention} to: {title}")  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue, reportOptionalMemberAccess]

        modal = MultilineModal(
            title="Update Pin Title",
            label="Title",
            style=discord.TextStyle.short,
            default_value=current_title,
            callback_func=modal_callback,
            required=False,
        )
        _ = await interaction.response.send_modal(modal)

    @app_commands.command(name="updateurl", description="Update this channel's existing pin's url (embed only)")
    @app_commands.check(check_permitted)
    async def update_url(self, interaction: discord.Interaction[PinformationBot], url: str):
        _ = await interaction.response.defer(ephemeral=True)
        await self._update_pin_attribute(interaction, "url", url)
        await self.bot.log_pin_change(interaction, f"Updated pin url in {interaction.channel.mention} to: {url}")  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue, reportUnknownMemberType]

    @app_commands.command(
        name="updateimage", description="Update this channel's existing pin's image url or attachment"
    )
    @app_commands.check(check_permitted)
    async def update_img(
        self,
        interaction: discord.Interaction[PinformationBot],
        url: str | None = None,
        attachment: discord.Attachment | None = None,
    ):
        """Allows either supplying a string URL or attaching an image file directly in the slash command."""
        _ = await interaction.response.defer(ephemeral=True)

        final_url = url
        if not final_url and attachment:
            final_url = attachment.url

        await self._update_pin_attribute(interaction, "image", final_url)
        await self.bot.log_pin_change(
            interaction,
            f"Updated pin image url in {interaction.channel.mention} to: {final_url or 'none'}",  # pyright: ignore[reportUnknownMemberType, reportOptionalMemberAccess, reportAttributeAccessIssue]
        )

    @app_commands.command(name="updatecolor", description="Update this channel's existing pin's color (embed only)")
    @app_commands.check(check_permitted)
    async def update_color(self, interaction: discord.Interaction[PinformationBot], color: int):
        _ = await interaction.response.defer(ephemeral=True)
        await self._update_pin_attribute(interaction, "color", color)
        await self.bot.log_pin_change(interaction, f"Updated pin color in {interaction.channel.mention} to: {color}")  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue, reportUnknownMemberType]

    async def _update_pin_attribute(
        self,
        interaction: discord.Interaction[PinformationBot],
        attribute_name: str,
        value: str | int | None,
        require_embed: bool = True,
    ):
        """Generic method to update a pin attribute using Interaction"""
        channel = interaction.channel
        if channel is None:
            return

        async with ChannelLock(channel.id):
            pin = await get_pin(interaction, self.bot, channel.id)
            if not pin:
                return

            if require_embed and not await self._is_embed(interaction, pin):
                return

            if pin.last_message:
                _ = create_task(delete_old_message(channel, pin.last_message))

            setattr(pin, attribute_name, value)
            if isinstance(pin, EmbedPin):
                pin.rebuild_embed()

            message = await pin.send_to(channel)

            pin.last_message = message.id
            pin.last_message_dt = datetime.now(UTC)
            self.bot.database.add_or_update_pin(pin)
            await handle_reply(interaction, f"Updated pin {attribute_name}!")

    @staticmethod
    async def _is_embed(interaction: discord.Interaction[PinformationBot], pin: PinUnion) -> bool:
        if isinstance(pin, EmbedPin):
            return True
        await handle_reply(interaction, "Pin is not an embed!", ephemeral=True)
        return False


async def setup(bot: PinformationBot):
    await bot.add_cog(UpdateCog(bot))
