import logging
import re
from collections.abc import Callable, Coroutine
from typing import Any, Generic, TypeVar, cast, override

import discord
from discord.client import Client
from discord.emoji import Emoji
from discord.ui import Modal, TextInput

BotT = TypeVar('BotT', bound=Client, covariant=True, default=Client)

_emoji_cache: dict[str, str] = {}
log = logging.getLogger(__name__)


def update_emoji_cache(emojis: list[Emoji] | tuple[Emoji, ...]):
    """Helper to update and return the cached emoji map."""
    global _emoji_cache
    _emoji_cache |= {emoji.name: str(emoji) for emoji in emojis}


class MultilineModal(Modal, Generic[BotT]):
    def __init__(
        self,
        title: str,
        label: str,
        style: discord.TextStyle,
        default_value: str | None,
        callback_func: Callable[[discord.Interaction[BotT], str | None], Coroutine[Any, Any, None]],
        required: bool = True,
        text_only: bool = False,
    ):
        super().__init__(title=title)
        self.callback_func: Callable[[discord.Interaction[BotT], str | None], Coroutine[Any, Any, None]] = callback_func
        self.text_only: bool = text_only

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
            guild = interaction.guild

            global _emoji_cache
            if not _emoji_cache:
                all_emojis = getattr(bot, "emojis", guild.emojis if guild else ())
                update_emoji_cache(all_emojis)

            resolved_val = self.resolve_custom_emojis(raw_val, _emoji_cache)
            if guild:
                resolved_val = self.resolve_channel_mentions(resolved_val, guild)
                if not self.text_only:  # don't allow user/role mentions in textpins
                    resolved_val = await self.resolve_mentions(resolved_val, guild)

        typed_interaction = cast(discord.Interaction[BotT], interaction)
        await self.callback_func(typed_interaction, resolved_val)

    @staticmethod
    def resolve_custom_emojis(text: str, emoji_map: dict[str, str]) -> str:
        """Replaces :shortcode: text with matching custom emoji formatted string."""
        if not text or not emoji_map:
            return text

        def replace_shortcode(match: re.Match[str]) -> str:
            emoji_name = match.group(1)
            return emoji_map.get(emoji_name, match.group(0))

        return re.sub(r"(?<!<):([a-zA-Z0-9_]+):(?!\d+>)", replace_shortcode, text)

    @staticmethod
    async def resolve_mentions(text: str, guild: discord.Guild) -> str:
        """
        Resolves @role or @user mentions without greedy pattern overlap.
        Uses async guild member queries for uncached usernames without loading 180k members into RAM.
        """
        if not text or "@" not in text:
            return text

        text = re.sub(r"<@#?([a-zA-Z0-9_.\-]+)>", r"@\1", text)

        target_map: dict[str, str] = {}
        for role in guild.roles:
            target_map[role.name.lower()] = role.mention
            target_map[str(role.id)] = role.mention

        for key in sorted(target_map.keys(), key=len, reverse=True):
            mention = target_map[key]
            pattern = rf"(?<!<@&)(?<!<@)@{re.escape(key)}(?!\d+>)"
            text = re.sub(pattern, mention, text, flags=re.IGNORECASE)

        matches: list[str] = re.findall(r"(?<!<@)(?<!<@!)(?<!<@&)@([a-zA-Z0-9_.\-]+)(?!\d+>)", text)
        for identifier in matches:
            if identifier.isdigit():
                text = text.replace(f"@{identifier}", f"<@{identifier}>")
                continue

            if not (member := guild.get_member_named(identifier)):
                try:
                    results = await guild.query_members(query=identifier, limit=1)
                    if results:
                        member = results[0]
                except Exception as e:
                    log.debug(f"Failed to query member {identifier}: {e}")

            if member:
                pattern = rf"(?<!<@)(?<!<@!)(?<!<@&)@{re.escape(identifier)}(?!\d+>)"
                text = re.sub(pattern, member.mention, text, flags=re.IGNORECASE)

        return text

    @staticmethod
    def resolve_channel_mentions(text: str, guild: discord.Guild) -> str:
        """Replaces #channel-name or #channel_id with channel mentions (<#channel_id>)."""
        if not text or not guild.channels:
            return text

        channel_map: dict[str, str] = {}
        for ch in guild.channels:
            channel_map[ch.name.lower()] = ch.mention
            channel_map[str(ch.id)] = ch.mention

        def replace_channel(match: re.Match[str]) -> str:
            ch_identifier = match.group(1).lower()
            return channel_map.get(ch_identifier, match.group(0))

        return re.sub(r"(?<!<)#([a-zA-Z0-9_\-]+)(?!\d+>)", replace_channel, text)
