from datetime import datetime, timezone
from typing import Any, Optional

import discord


class Pin:
    """Base Pin class"""

    def __init__(self, channel_id: int):
        self.channel_id = channel_id
        self.speed_msgs: int = 1
        self.msg_count = 0
        self.message_obj: Any = None
        self.last_message: Optional[discord.Message.id] = None
        self.started = datetime.now(timezone.utc).timestamp()
        self.active: bool = True

    def get_self_data(self):
        return f"Message speed: {self.speed_msgs}\nPinned: <t:{int(self.started)}:f>"

    def increment_msg_count(self):
        self.msg_count += 1

    def _rebuild_msg(self):
        raise NotImplementedError("This method should be overriden in sublass.")


class TextPin(Pin):
    def __init__(self, channel_id: int, text: str):
        super().__init__(channel_id)
        self.text = text

    def _rebuild_msg(self):
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
    ):
        super().__init__(channel_id)
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
        return self.embed.to_dict()

    def _rebuild_msg(self):
        return {"embed": self.embed}
