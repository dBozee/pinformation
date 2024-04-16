from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class BotConfig:
    """
    Dataclass for the configuration of the bot. Should be originally instantiated
    by the config.json file.
    """
    prefix: Optional[str]
    permitted_users: Optional[list]
    permitted_roles: Optional[list]
