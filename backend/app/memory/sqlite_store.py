"""SQLite 持久化存储实现（可选，需安装 aiosqlite）"""
from pathlib import Path
from typing import List

from .base import BaseMemoryStore
from .data_model import MemoryItem


class SqliteMemoryStore(BaseMemoryStore):
    def __init__(self, db_path: str = "./memory.db") -> None:
        self.db_path = db_path

    async def init_table(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        import aiosqlite
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS user_memory (
                    user_id TEXT,
                    memory_id TEXT PRIMARY KEY,
                    content TEXT,
                    source TEXT,
                    weight REAL,
                    create_time REAL,
                    last_access_time REAL
                )
                """
            )
            await db.commit()

    async def save(self, user_id: str, item: MemoryItem) -> None:
        await self.init_table()
        import aiosqlite
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO user_memory
                (user_id, memory_id, content, source, weight, create_time, last_access_time)
                VALUES (?,?,?,?,?,?,?)
                """,
                (
                    user_id, item.memory_id, item.content, item.source,
                    item.weight, item.create_time, item.last_access_time,
                ),
            )
            await db.commit()

    async def list_all(self, user_id: str) -> List[MemoryItem]:
        await self.init_table()
        import aiosqlite
        res: List[MemoryItem] = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM user_memory WHERE user_id = ?", (user_id,)
            )
            rows = await cursor.fetchall()
            for r in rows:
                res.append(MemoryItem.from_dict(dict(r)))
        return res

    async def delete(self, user_id: str, memory_id: str) -> bool:
        await self.init_table()
        import aiosqlite
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "DELETE FROM user_memory WHERE user_id=? AND memory_id=?",
                (user_id, memory_id),
            )
            await db.commit()
            return cur.rowcount > 0

    async def clear(self, user_id: str) -> None:
        await self.init_table()
        import aiosqlite
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM user_memory WHERE user_id = ?", (user_id,)
            )
            await db.commit()
