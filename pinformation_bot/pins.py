from datetime import datetime, timezone
from typing import Any, ClassVar, Optional

import discord


class Pin:
    """Base Pin class"""

    def __init__(self, channel_id: int, speed_msgs: int):
        self.channel_id = channel_id
        self.pin_type: str = "base"
        self.speed_msgs: int = speed_msgs
        self.msg_count = 0
        self.message_obj: Any = None
        self.last_message: Optional[discord.Message.id] = None
        self.started = datetime.now(timezone.utc).timestamp()
        self.active: bool = True

    def get_self_data(self):
        return f"Message speed: {self.speed_msgs}\nPinned: <t:{int(self.started)}:f>"

    def increment_msg_count(self):
        self.msg_count += 1

    def rebuild_msg(self):
        raise NotImplementedError("This method should be overriden in sublass.")


class TextPin(Pin):
    def __init__(self, channel_id: int, text: str, speed_msgs: int):
        super().__init__(channel_id, speed_msgs)
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
        url: Optional[str],
        image: Optional[str],
        color: Optional[int],
        speed_msgs: int,
    ):
        super().__init__(channel_id, speed_msgs)
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
