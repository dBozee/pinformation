from logging import getLogger
from pathlib import Path

from pydantic import BaseModel, Field

log = getLogger(__name__)
CONFIG_FOLDER = Path(__file__).parent / "config"
JSON_FILE = Path(CONFIG_FOLDER / "config.json")


class BotConfig(BaseModel):
    """
    BaseModel for the configuration of the bot. Should be originally instantiated
    by the config.json file.
    """
    prefix: str
    admin_users: list[str] = Field(default_factory=list)
    admin_roles: list[str] = Field(default_factory=list)
    permitted_roles: dict[str, list[str]] = Field(default_factory=dict)
    log_channel: str
    embed_color: int
    cogs: list[str] = Field(default_factory=list)
    debug: bool = False

    def write_config_to_json(self) -> None:
        log.debug(f"Opening config file at: {JSON_FILE}")
        _ = JSON_FILE.write_text(self.model_dump_json(indent=4), encoding="utf-8")
        log.debug("Finished writing to config file")

    @classmethod
    def load_from_json(cls, path: Path = JSON_FILE) -> BotConfig:
        """Loads and validates configuration directly from a JSON file path."""
        log.debug(f"Loading config file from: {path}")
        return cls.model_validate_json(path.read_text(encoding="utf-8"))
