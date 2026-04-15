from dataclasses import asdict, dataclass
from json import dump
from logging import getLogger
from pathlib import Path

log = getLogger(__name__)
CONFIG_FOLDER = Path(__file__).parent / "config"
JSON_FILE = Path(CONFIG_FOLDER / "config.json")


@dataclass
class BotConfig:
    """
    Dataclass for the configuration of the bot. Should be originally instantiated
    by the config.json file.
    """

    prefix: str
    permitted_users: list[str]
    permitted_roles: list[str]
    log_channel: str
    embed_color: int
    cogs: list[str]
    debug: bool

    def write_config_to_json(self):
        log.debug(f"Opening config file at: {str(JSON_FILE)}")
        with JSON_FILE.open(mode="w") as outfile:
            dump(asdict(self), outfile, indent=4)
        log.debug("Finished writing to config file")
