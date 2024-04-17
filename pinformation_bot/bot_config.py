from dataclasses import dataclass, asdict
from typing import Optional
from json import dump
from pathlib import Path

JSON_FILE = Path(Path(__file__).parent / "config.json")


@dataclass
class BotConfig:
    """
    Dataclass for the configuration of the bot. Should be originally instantiated
    by the config.json file.
    """

    prefix: Optional[str]
    permitted_users: Optional[list[str]]
    permitted_roles: Optional[list[str]]
    embed_color: Optional[int]
    cogs: Optional[list[str]]

    def write_config_to_json(self):
        outfile = JSON_FILE.open("w")
        dump(asdict(self), outfile, indent=4)
        outfile.close()
