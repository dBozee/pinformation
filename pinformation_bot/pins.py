from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import discord


class SpeedTypes(StrEnum):
    messages = "messages"
    seconds = "seconds"


class Pin:
    """Base Pin class"""

    def __init__(self, channel_id: int, speed: int, speed_type: SpeedTypes = SpeedTypes.messages):
        self.channel_id = channel_id
        self.pin_type: str = "base"
        self.speed: int = speed
        self.msg_count = 0
        self.speed_type = speed_type
        self.message_obj: Any = None
        self.last_message: int | None = None
        self.last_message_dt: datetime | None = None
        self.started = datetime.now(UTC).timestamp()
        self.active: bool = True

    def get_self_data(self):
        typ = "seconds" if self.speed_type == SpeedTypes.seconds else "messages"
        return f"Message speed: {self.speed} {typ}\nPinned: <t:{int(self.started)}:f>"

    def increment_msg_count(self):
        self.msg_count += 1

    def rebuild_msg(self):
        raise NotImplementedError("This method should be overridden in subclass.")


class TextPin(Pin):
    def __init__(self, channel_id: int, text: str, speed: int, speed_type: SpeedTypes = SpeedTypes.messages):
        super().__init__(channel_id, speed, speed_type=speed_type)
        self.pin_type: str = "text"
        self.text = text

    def rebuild_msg(self):
        return {"content": self.text}


class EmbedPin(Pin):
    def __init__(
        self,
        channel_id: int,
        title: str,
        text: str,
        url: str | None,
        image: str | None,
        color: int | None,
        speed: int,
        speed_type: SpeedTypes = SpeedTypes.messages,
    ):
        super().__init__(channel_id, speed, speed_type)
        self.pin_type: str = "embed"
        self.title = title
        self.text = text
        self.url = url
        self.image = image
        self.color = color
        self.embed: discord.Embed = self._create_embed()

    def _create_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=self.title,
            type="rich",
            url=self.url,
            color=self.color,
            description=self.text,
        )
        if self.image:
            image = self.image
            embed.set_image(url=image)

        return embed

    def _get_embed_info(self) -> dict:
        # noinspection PyTypeChecker
        return self.embed.to_dict()  # bad typehint from the library

    def rebuild_msg(self):
        return {"embed": self.embed}
