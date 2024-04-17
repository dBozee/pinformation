from dataclasses import asdict, dataclass
from typing import Optional

import discord


@dataclass
class Pin:
    """Base Pin class"""

    def __init__(self, channel_id: int):
        self.channel_id = channel_id
        self.speed_msgs: int = 1
        self.msg_count = 0

    def get_self_data(self):
        data_dict = asdict(self)
        return ", ".join(f"{key}:{value}" for key, value in data_dict.items())


@dataclass
class TextPin(Pin):
    def __init__(self, channel_id: int, text: str):
        super().__init__(channel_id)
        self.text = text


@dataclass
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
        embed = discord.Embed(title=self.title, type="rich", url=self.url, color=self.color)
        embed.add_field(name="", value=self.text)
        if self.image:
            image = self.image
            embed.set_image(url=image)

        return embed

    def _get_embed_info(self) -> dict:
        return self.embed.to_dict()


@dataclass
class PollPin(Pin):
    def __init__(self, channel_id: int, title: str, options: list[str], color: Optional[int]):
        super().__init__(channel_id)
        self.title = title
        self.options = options
        self.color = color
        self.embed: discord.Embed = self._create_poll()

    def _create_poll(self) -> discord.Embed:
        embed = discord.Embed(title=self.title, type="rich", color=self.color)
        for i, option in enumerate(self.options):
            embed.add_field(name=i + 1, value=option)

        return embed

    def _get_embed_info(self) -> dict:
        return self.embed.to_dict()
