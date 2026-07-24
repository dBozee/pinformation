from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any, ClassVar, Literal, Self, override

import discord
from discord.embeds import Embed
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator


class SpeedTypes(StrEnum):
    messages = "messages"
    seconds = "seconds"


type PinType = Literal["text", "embed", "base"]
PinUnion = Annotated['TextPin | EmbedPin', Field(discriminator="pin_type")]
PinAdapter: TypeAdapter[PinUnion] = TypeAdapter(PinUnion)


class PinModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra='forbid', arbitrary_types_allowed=True)

    channel_id: int
    pin_type: PinType = "base"
    speed: int = 1
    speed_type: SpeedTypes = SpeedTypes.messages
    msg_count: int = 0
    last_message: int | None = None
    last_message_dt: datetime | None = None
    started: float = Field(default_factory=lambda: datetime.now(UTC).timestamp())
    active: bool = True
    message_obj: Any = None  # Not used in DB. Runtime only

    def increment_msg_count(self) -> None:
        self.msg_count += 1

    def get_self_data(self) -> str:
        typ = "seconds" if self.speed_type == SpeedTypes.seconds else "messages"
        return f"Message speed: {self.speed} {typ}\nPinned: <t:{int(self.started)}:f>"

    def to_db_tuple(self) -> tuple[Any, ...]:
        """Return a tuple matching the order used in db_funcs to create or update a pin in the database."""
        raise NotImplementedError("This method should be overridden in subclass.")

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> PinUnion:
        """Factory method to parse a database row into the appropriate Pin model subclass."""
        return PinAdapter.validate_python(row)

    async def send_to(self, channel: discord.abc.Messageable) -> discord.Message:
        raise NotImplementedError


class TextPin(PinModel):
    pin_type: PinType = "text"
    text: str = ""

    @override
    def to_db_tuple(self) -> tuple[Any, ...]:
        return (
            self.channel_id,
            self.pin_type,
            self.speed,
            self.speed_type.value,
            self.last_message,
            int(self.active),
            self.text,
            *(None, None, None, None),  # title, url, image, color
        )

    @override
    async def send_to(self, channel: discord.abc.Messageable) -> discord.Message:
        return await channel.send(content=self.text)


class EmbedPin(PinModel):
    pin_type: PinType = "embed"
    title: str | None = None
    text: str = ""
    url: str | None = None
    image: str | None = None
    color: int | None = None

    embed: Embed = Field(default_factory=lambda: Embed(), exclude=True)

    @model_validator(mode='after')
    def build_embed(self) -> Self:
        if not self.embed or not self.embed.description:
            embed = discord.Embed(
                title=self.title,
                type="rich",
                url=self.url,
                color=self.color,
                description=self.text,
            )
            if self.image:
                _ = embed.set_image(url=self.image)
            self.embed = embed
        return self

    def get_embed_info(self) -> dict[str, Any]:
        return dict(self.embed.to_dict())

    @override
    def to_db_tuple(self) -> tuple[Any, ...]:
        return (
            self.channel_id,
            self.pin_type,
            self.speed,
            self.speed_type.value,
            self.last_message,
            int(self.active),
            self.text,
            self.title,
            self.url,
            self.image,
            self.color,
        )

    @override
    async def send_to(self, channel: discord.abc.Messageable) -> discord.Message:
        return await channel.send(embed=self.embed)
