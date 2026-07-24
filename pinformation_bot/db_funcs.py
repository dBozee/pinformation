import sqlite3
from pathlib import Path
from sqlite3.dbapi2 import Cursor
from types import TracebackType
from typing import Self

from pinformation_bot.pins import PinModel, PinUnion

from .bot_config import CONFIG_FOLDER


class Database:
    def __init__(self):
        self.file_path: Path = Path(CONFIG_FOLDER / "pin_cache.db")
        self.db: sqlite3.Connection = sqlite3.connect(self.file_path)
        self.db.row_factory = sqlite3.Row
        self.cur: Cursor = self.db.cursor()
        self._init_db()

    def _init_db(self) -> None:
        query: str = """
            CREATE TABLE IF NOT EXISTS pins(
            channel_id TEXT PRIMARY KEY,pin_type STRING,speed INTEGER,
            speed_type TEXT,last_message TEXT,active INTEGER,
            text TEXT,title TEXT,url TEXT,image TEXT,color INTEGER)
            """
        with self.db:
            _ = self.cur.execute(query)

    def add_or_update_pin(self, pin: PinUnion) -> None:
        query: str = """
            INSERT OR REPLACE INTO pins (
                channel_id, pin_type, speed, speed_type, last_message, 
                active, text, title, url, image, color
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self.db:
            _ = self.cur.execute(query, pin.to_db_tuple())

    def remove_pin(self, channel_id: int) -> None:
        query = "DELETE FROM pins WHERE channel_id = ?"
        with self.db:
            _ = self.cur.execute(query, (channel_id,))

    def get_persisted_pins(self) -> list[PinUnion]:
        query: str = "SELECT * FROM pins WHERE active = 1"
        rows: list[Cursor] = self.cur.execute(query).fetchall()
        return [PinModel.from_db_row(dict(row)) for row in rows]

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: type[BaseException], exc_value: BaseException, traceback: TracebackType) -> None:
        self.close()