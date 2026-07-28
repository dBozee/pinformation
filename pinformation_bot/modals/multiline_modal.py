import re
from collections.abc import Callable, Coroutine
from typing import Any, Generic, TypeVar, cast, override

import discord
from discord.client import Client
from discord.emoji import Emoji
from discord.ui import Modal, TextInput

BotT = TypeVar('BotT', bound=Client, covariant=True, default=Client)

class MultilineModal(Modal, Generic[BotT]):
    def __init__(
        self,
        title: str,
        label: str,
        style: discord.TextStyle,
        default_value: str | None,
        callback_func: Callable[[discord.Interaction[BotT], str | None], Coroutine[Any, Any, None]],
        required: bool = True,
    ):
        super().__init__(title=title)
        self.callback_func: Callable[[discord.Interaction[BotT], str | None], Coroutine[Any, Any, None]] = callback_func # noqa: E501

        self.input_field: TextInput[Any] = discord.ui.TextInput(
            label=label,
            style=style,
            default=default_value or "",
            required=required,
            max_length=4000 if style == discord.TextStyle.paragraph else 256,
        )
        _ = self.add_item(self.input_field)

    @override
    async def on_submit(self, interaction: discord.Interaction) -> None:
        raw_val: str | None = self.input_field.value.strip() or None

        resolved_val: str | None = None
        if raw_val:
            bot = interaction.client
            guild_emojis: tuple[Emoji, ...] = interaction.guild.emojis if interaction.guild else ()
            all_emojis = getattr(bot, "emojis", guild_emojis)

            resolved_val = self.resolve_custom_emojis(raw_val, list(all_emojis))

        typed_interaction = cast(discord.Interaction[BotT], interaction)
        await self.callback_func(typed_interaction, resolved_val)

    @staticmethod
    def resolve_custom_emojis(text: str, emoji_list: list[discord.Emoji]) -> str:
        """Replaces :shortcode: text with matching custom emoji formatted string."""
        if not text or not emoji_list:
            return text

        emoji_map = {emoji.name: str(emoji) for emoji in emoji_list}

        def replace_shortcode(match: re.Match[str]) -> str:
            emoji_name = match.group(1)
            return emoji_map.get(emoji_name, match.group(0))

        return re.sub(r"(?<!<):([a-zA-Z0-9_]+):(?!\d+>)", replace_shortcode, text)