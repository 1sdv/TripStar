"""Offline regression tests for preference storage and recall.

Run from the repository root:
    python -m unittest discover -s backend/tests -v
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.memory.data_model import MemoryItem
from backend.app.memory.in_memory_store import InMemoryStore
from backend.app.memory.memory_manager import DAY_SECONDS, MemoryManager
from backend.app.memory.sqlite_store import SqliteMemoryStore


START = 1_700_000_000.0


def memory(memory_id="nature", content="偏爱自然景点", weight=8.0):
    return MemoryItem(memory_id, content, "explicit", weight, START, START)


class SqliteMemoryStoreTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = str(Path(self.directory.name) / "nested" / "memory.db")
        self.store = SqliteMemoryStore(self.path)

    async def test_round_trip_survives_new_store_instance(self):
        item = memory()
        await self.store.save("alice", item)

        restored = await SqliteMemoryStore(self.path).list_all("alice")

        self.assertEqual(restored, [item])
        self.assertNotIn("user_id", restored[0].to_dict())

    async def test_update_preserves_single_row(self):
        item = memory()
        await self.store.save("alice", item)
        item.weight = 6.5
        item.last_access_time = START + DAY_SECONDS
        await self.store.save("alice", item)

        self.assertEqual(await self.store.list_all("alice"), [item])

    async def test_user_scoped_read_delete_and_clear(self):
        alice_item = memory("alice-nature")
        bob_item = memory("bob-nature")
        await self.store.save("alice", alice_item)
        await self.store.save("bob", bob_item)

        self.assertEqual(await self.store.list_all("missing"), [])
        self.assertFalse(await self.store.delete("bob", alice_item.memory_id))
        self.assertEqual(await self.store.list_all("alice"), [alice_item])
        await self.store.clear("alice")
        self.assertEqual(await self.store.list_all("alice"), [])
        self.assertEqual(await self.store.list_all("bob"), [bob_item])
        self.assertTrue(await self.store.delete("bob", bob_item.memory_id))
        self.assertEqual(await self.store.list_all("bob"), [])


class RecallContract:
    """The same recall behavior must hold for both storage implementations."""

    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = str(Path(self.directory.name) / "memory.db")
        with patch("backend.app.memory.memory_manager.USE_SQLITE_PERSIST", False):
            self.manager = MemoryManager()
        self.manager.store = self.make_store()
        for name, value in (
            ("DECAY_FACTOR", 0.5),
            ("MEMORY_WEIGHT_THRESHOLD", 2.0),
            ("MAX_RECALL_COUNT", 1),
            ("MAX_SINGLE_CONTENT_LENGTH", 4),
            ("MIN_INIT_WEIGHT", 4.0),
        ):
            patcher = patch("backend.app.memory.memory_manager." + name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def reopen_store(self):
        if isinstance(self.manager.store, SqliteMemoryStore):
            self.manager.store = SqliteMemoryStore(self.path)

    async def test_recall_persists_decay_and_timestamp_before_top_k(self):
        await self.manager.store.save("alice", memory("first", weight=8.0))
        await self.manager.store.save("alice", memory("second", weight=6.0))

        with patch("time.time", return_value=START + DAY_SECONDS):
            recalled = await self.manager.recall_user_memory("alice")

        self.assertEqual([item.memory_id for item in recalled], ["first"])
        self.reopen_store()
        stored = {item.memory_id: item for item in await self.manager.store.list_all("alice")}
        self.assertEqual(stored["first"].weight, 4.0)
        self.assertEqual(stored["second"].weight, 3.0)
        for item in stored.values():
            self.assertEqual(item.last_access_time, START + DAY_SECONDS)
            self.assertEqual(item.create_time, START)

        # A second recall at the same instant must not decay the same interval twice.
        with patch("time.time", return_value=START + DAY_SECONDS):
            again = await self.manager.recall_user_memory("alice")
        self.assertEqual(again[0].weight, 4.0)

    async def test_forgetting_survives_reopen_and_preserves_other_users(self):
        await self.manager.store.save("alice", memory("alice-nature"))
        bob_item = memory("bob-nature")
        await self.manager.store.save("bob", bob_item)

        with patch("time.time", return_value=START + 2 * DAY_SECONDS):
            recalled = await self.manager.recall_user_memory("alice")
        self.assertEqual(recalled[0].weight, 2.0)  # Threshold is inclusive.
        self.reopen_store()
        with patch("time.time", return_value=START + 3 * DAY_SECONDS):
            self.assertEqual(await self.manager.recall_user_memory("alice"), [])

        self.reopen_store()
        self.assertEqual(await self.manager.store.list_all("alice"), [])
        self.assertEqual(await self.manager.store.list_all("bob"), [bob_item])

    async def test_recalled_preferences_reach_prompt_with_existing_limits(self):
        await self.manager.store.save("alice", memory("first", "偏爱自然景点", 8.0))
        await self.manager.store.save("alice", memory("second", "住宿偏好民宿", 6.0))
        self.reopen_store()

        with patch("time.time", return_value=START):
            snippet = await self.manager.build_prompt_snippet("alice")
            empty = await self.manager.build_prompt_snippet("missing")

        self.assertEqual(snippet, "【用户历史旅行偏好】\n- 偏爱自然")
        self.assertEqual(empty, "")

    async def test_duplicate_preference_merges_after_reopen(self):
        with patch("time.time", return_value=START):
            await self.manager.add_memory("alice", "偏爱自然景点", "explicit", 8.0)
            self.reopen_store()
            await self.manager.add_memory("alice", " 偏爱自然景点 ", "implicit", 6.0)

        self.reopen_store()
        items = await self.manager.store.list_all("alice")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].weight, 10.0)
        self.assertEqual(items[0].content, "偏爱自然景点")


class InMemoryRecallTests(RecallContract, unittest.IsolatedAsyncioTestCase):
    def make_store(self):
        return InMemoryStore()


class SqliteRecallTests(RecallContract, unittest.IsolatedAsyncioTestCase):
    def make_store(self):
        return SqliteMemoryStore(self.path)
