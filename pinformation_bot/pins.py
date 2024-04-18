from dataclasses import asdict, dataclass
from typing import Any, Optional

import discord


@dataclass
class Pin:
    """Base Pin class"""

    def __init__(self, channel_id: int):
        self.channel_id = channel_id
        self.speed_msgs: int = 1
        self.msg_count = 0
        self.message_obj: Any = None
        self.last_message: Optional[discord.Message.id] = None

    def get_self_data(self):
        data_dict = asdict(self)
        return ", ".join(f"{key}:{value}" for key, value in data_dict.items())

    def increment_msg_count(self):
        self.msg_count += 1

    def _rebuild_msg(self):
        raise NotImplementedError("This method should be overriden in sublass.")


@dataclass
class TextPin(Pin):
    def __init__(self, channel_id: int, text: str):
        super().__init__(channel_id)
        self.text = text

    def _rebuild_msg(self):
        return {"content": self.text}


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

    def _rebuild_msg(self):
        return {"embed": self.embed}


@dataclass
class PollPin(Pin):
    def __init__(self, channel_id: int, title: str, options: list[str], color: Optional[int]):
        super().__init__(channel_id)
        self.title = title
        self.options = options
        self.color = color
        self.embed: discord.Embed = self._create_embed()
        self.view: discord.ui.View = self._create_view()

    def _create_embed(self) -> discord.Embed:
        embed = discord.Embed(title=self.title, type="rich", color=self.color)
        embed.description = "\n".join(f"{self.regional_ind(i)}: {option}" for i, option in enumerate(self.options))

        return embed

    def _create_view(self) -> discord.ui.View:
        view = discord.ui.View()
        for i in range(len(self.options)):
            view.add_item(discord.ui.Button(label=self.regional_ind(i), style=discord.ButtonStyle.grey))

        return view

    def _get_embed_info(self) -> dict:
        return self.embed.to_dict()

    def _rebuild_msg(self):
        return {"embed": self.embed, "view": self.view}

    @staticmethod
    def regional_ind(index: int) -> str:
        if 0 <= index <= 26:
            return chr(ord("\U0001F1E6") + index)
        return ""
