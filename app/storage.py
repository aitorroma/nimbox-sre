from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .config import settings


class StateStore:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or settings.state_db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                "create table if not exists chat_state (chat_id text primary key, data text not null)"
            )

    def get(self, chat_id: int | str) -> dict[str, Any]:
        with self._conn() as conn:
            row = conn.execute("select data from chat_state where chat_id = ?", (str(chat_id),)).fetchone()
        return json.loads(row[0]) if row else {}

    def set(self, chat_id: int | str, data: dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                "insert into chat_state(chat_id, data) values(?, ?) on conflict(chat_id) do update set data=excluded.data",
                (str(chat_id), json.dumps(data, ensure_ascii=False)),
            )

    def clear(self, chat_id: int | str) -> None:
        with self._conn() as conn:
            conn.execute("delete from chat_state where chat_id = ?", (str(chat_id),))
