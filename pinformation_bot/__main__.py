import logging
from os import environ

from dotenv import load_dotenv

from pinformation_bot.bot_config import JSON_FILE, BotConfig
from pinformation_bot.pinformation import PinformationBot

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


def main() -> None:
    loaded_config: BotConfig = BotConfig.load_from_json(JSON_FILE)

    bot = PinformationBot(config=loaded_config)
    bot.run(environ.get("DISCORD_TOKEN", ""))


if __name__ == "__main__":
    _ = load_dotenv()
    try:
        log.info("Starting bot...")
        main()
    except Exception as e:
        log.info(f"Unhandled exception raised: {e}")
        exit(1)  # ensure the script gets restarted by the docker container if running in docker.
