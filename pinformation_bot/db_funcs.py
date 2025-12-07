import sqlite3
from pathlib import Path
from typing import Any

from .bot_config import CONFIG_FOLDER
from .pins import Pin


class Database:
    def __init__(self):
        self.file_path: Path = Path(CONFIG_FOLDER / "pin_cache.db")
        self.db: sqlite3.Connection = sqlite3.connect(self.file_path)
        self.cur = self.db.cursor()
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS pins(\
            channel_id TEXT PRIMARY KEY,\
            pin_type STRING,\
            speed_msgs INTEGER,\
            last_message TEXT,\
            active INTEGER,\
            text TEXT,\
            title TEXT,\
            url TEXT,\
            image TEXT,\
            color INTEGER)"
        )
        self.db.commit()

    def add_or_update_pin(self, pin_data: dict[str, Any]) -> None:
        """
        Takes a dictionary containing info about a pin and adds it to or updates an existing entry in the database.
        """
        values = (
            pin_data["channel_id"],
            pin_data.get("pin_type", "embed"),
            pin_data.get("speed_msgs"),
            pin_data.get("last_message"),
            int(pin_data.get("active")),  # convert bool to int because sqlite doesn't support booleans
            pin_data.get("text"),
            pin_data.get("title"),
            pin_data.get("url"),
            pin_data.get("image"),
            pin_data.get("color"),
        )
        self.cur.execute(
            "INSERT OR REPLACE INTO pins(\
            channel_id,\
            pin_type,\
            speed_msgs,\
            last_message,\
            active,\
            text,\
            title,\
            url,\
            image,\
            color)\
            VALUES(?,?,?,?,?,?,?,?,?,?)",
            values,
        )
        self.db.commit()

    def remove_pin(self, channel_id):
        self.cur.execute(f"DELETE FROM pins WHERE channel_id = {channel_id}")
        self.db.commit()

    def get_cached_pins(self) -> list[dict[str, Any]]:
        self.db.row_factory = sqlite3.Row
        query_res: list[sqlite3.Row] = self.cur.execute("SELECT * FROM pins WHERE active = 1").fetchall()
        results = []
        for result in query_res:
            results.append({
                "channel_id": result[0],
                "pin_type": result[1],
                "speed_msgs": result[2],
                "last_message": result[3],
                "active": bool(result[4]),
                "text": result[5],
                "title": result[6],
                "url": result[7],
                "image": result[8],
                "color": result[9],
            })

        return results
