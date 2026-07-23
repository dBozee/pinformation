from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, override

import discord
from discord.embeds import Embed


class SpeedTypes(StrEnum):
    messages = "messages"
    seconds = "seconds"


class Pin:
    """Base Pin class"""

    def __init__(self, channel_id: int, speed: int, speed_type: SpeedTypes = SpeedTypes.messages):
        self.channel_id: int = channel_id
        self.pin_type: str = "base"
        self.speed: int = speed
        self.msg_count: int = 0
        self.speed_type: SpeedTypes = speed_type
        self.message_obj: Any = None
        self.last_message: int | None = None
        self.last_message_dt: datetime | None = None
        self.started: float = datetime.now(UTC).timestamp()
        self.active: bool = True

    def get_self_data(self):
        typ = "seconds" if self.speed_type == SpeedTypes.seconds else "messages"
        return f"Message speed: {self.speed} {typ}\nPinned: <t:{int(self.started)}:f>"

    def increment_msg_count(self):
        self.msg_count += 1

    def rebuild_msg(self) -> dict[str, Any]:
        raise NotImplementedError("This method should be overridden in subclass.")


class TextPin(Pin):
    def __init__(self, channel_id: int, text: str, speed: int, speed_type: SpeedTypes = SpeedTypes.messages):
        super().__init__(channel_id, speed, speed_type=speed_type)
        self.pin_type: str = "text"
        self.text: str = text

    @override
    def rebuild_msg(self) -> dict[str, str]:
        return {"content": self.text}


class EmbedPin(Pin):
    def __init__(
        self,
        channel_id: int,
        title: str | None,
        text: str,
        url: str | None,
        image: str | None,
        color: int | None,
        speed: int,
        speed_type: SpeedTypes = SpeedTypes.messages,
    ):
        super().__init__(channel_id, speed, speed_type)
        self.pin_type: str = "embed"
        self.title: str | None = title
        self.text: str | None = text
        self.url: str | None = url
        self.image: str | None = image
        self.color: int | None = color
        self.embed: discord.Embed = self.create_embed()

    def create_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=self.title,
            type="rich",
            url=self.url,
            color=self.color,
            description=self.text,
        )
        if self.image:
            image = self.image
            _ = embed.set_image(url=image)

        return embed

    def get_embed_info(self) -> dict[str, Any]:
        # noinspection PyTypeChecker
        return self.embed.to_dict()  # pyright: ignore[reportReturnType] bad typehint from the library

    @override
    def rebuild_msg(self) -> dict[str, Embed]:
        return {"embed": self.embed}
