# Memory persistence regression tests

Run from the repository root with Python 3.10+ and the backend dependencies installed:

```sh
python -m unittest discover -s backend/tests -v
```

For these tests alone, the following subset of existing backend dependencies is sufficient:

```sh
python -m pip install "aiosqlite>=0.20.0" "httpx>=0.27.0" "pydantic-settings>=2.0.0" "python-dotenv>=1.0.0"
```

The tests use temporary SQLite databases and a controlled clock. No LLM/map credentials,
external API calls, or running application server are needed.

Coverage includes storage round trips through a new connection/store instance, updates,
user-scoped reads/deletes, duplicate preference merging, and the same recall behavior
for in-memory and SQLite stores. Recall must persist decayed weights and access times
for all surviving items before applying TOP-K, remove expired items, and preserve the
existing count/content limits when building the planner's preference prompt.
