from json import loads
from os import environ
from typing import Any

from dotenv import dotenv_values, load_dotenv

from .bot_config import BotConfig
from .pinformation import PinformationBot


def get_config() -> BotConfig:
    config_file = open('config.json', 'r')

    config_dict: dict[str, Any] = loads(config_file.read())
    config_file.close()

    return BotConfig(**config_dict)

def main() -> None:
    loaded_config: BotConfig = get_config()

    bot = PinformationBot(config=loaded_config)
    bot.run(environ.get('DISCORD_TOKEN', ''))


if __name__ == '__main__':
    load_dotenv()
    main()