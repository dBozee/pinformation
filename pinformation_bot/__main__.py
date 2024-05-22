from json import loads
from os import environ
from typing import Any

import discord
from dotenv import load_dotenv

from pinformation_bot.bot_config import JSON_FILE, BotConfig
from pinformation_bot.pinformation import PinformationBot

INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True


def get_config() -> BotConfig:
    config_file = JSON_FILE.open("r")

    config_dict: dict[str, Any] = loads(config_file.read())
    config_file.close()

    return BotConfig(**config_dict)


def main() -> None:
    loaded_config: BotConfig = get_config()

    bot = PinformationBot(config=loaded_config)
    bot.run(environ.get("DISCORD_TOKEN", ""))


if __name__ == "__main__":
    load_dotenv()
    main()
