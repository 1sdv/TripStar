# 05 · 偏好记忆（衰减 · 合并 · TOP-K · SQLite）

模块位置 `backend/app/memory/`，通过环境变量开关，默认**关闭**。

## 1. 开关与环境变量

| 变量 | 默认 | 作用 |
|---|---|---|
| `ENABLE_USER_MEMORY` | `false` | 总开关。关闭时 `/api/memory/*` 返回 `{code:400}`，行程结束后也不提取偏好 |
| `MEMORY_USE_SQLITE` | `false` | `true` → `SqliteMemoryStore`；否则 `InMemoryStore`（进程退出即丢） |
| `MEMORY_DECAY_FACTOR` | `0.97` | 每天衰减系数 |
| `MEMORY_THRESHOLD` | `2.0` | 低于此权重即被遗忘 |
| `MEMORY_MAX_RECALL` | `10` | TOP-K 召回上限（也是注入 prompt 的条数上限） |
| `MIN_INIT_WEIGHT` | `4.0` | 新记忆准入门槛（低于直接拒收） |
| `MEMORY_MAX_SINGLE_CONTENT` | `120` | 单条注入 prompt 时的字符截断 |

## 2. 数据模型（`data_model.py`）

```python
@dataclass
class MemoryItem:
    memory_id: str        # uuid4
    content: str          # 偏好文本，如"偏爱小众自然景点"
    source: str           # explicit（用户手动）| implicit（LLM 提取）
    weight: float         # [0,10]
    create_time: float
    last_access_time: float
    # create() / update_access() / to_dict() / from_dict()
```

## 3. 存储抽象（`base.py` / `in_memory_store.py` / `sqlite_store.py`）

`BaseMemoryStore` 接口：`save(user_id, item)`、`list_all(user_id)`、`delete(user_id, memory_id)`、`clear(user_id)`（异步）。

SQLite 表（`sqlite_store.py`，db 路径默认 `./memory.db`，相对后端工作目录）：

```sql
CREATE TABLE IF NOT EXISTS user_memory (
    user_id TEXT,
    memory_id TEXT PRIMARY KEY,
    content TEXT,
    source TEXT,
    weight REAL,
    create_time REAL,
    last_access_time REAL
);
```

写入用 `INSERT OR REPLACE`；每次操作前 `init_table()`（幂等），`aiosqlite` 延迟导入（未安装也能启动，只是不能用 SQLite 模式）。

## 4. 核心算法（`memory_manager.py`）

### 4.1 惰性遗忘

```python
async def _apply_forget_and_filter(items):
    now = time.time()
    for item in items:
        delta_days = (now - item.last_access_time) / 86400
        item.weight *= DECAY_FACTOR ** delta_days     # 0.97^天数
        item.update_access()                          # 被读到就算"用了一次"
        if item.weight >= THRESHOLD: keep
        else: mark_for_delete
```

- **惰性**：没有定时任务，只在 `recall` 时按时间差一次性乘算（指数函数可合并时间差，与持续衰减等价）。
- **基准是 `last_access_time`**，不是创建时间：不用的记忆才衰减。

### 4.2 召回

```python
async def recall_user_memory(user_id) -> List[MemoryItem]:
    all_items = await store.list_all(user_id)
    valid, remove_ids = await _apply_forget_and_filter(all_items)
    for mid in remove_ids: await store.delete(user_id, mid)     # 顺手清理
    valid.sort(key=weight, reverse=True)
    return valid[:MAX_RECALL_COUNT]
```

### 4.3 新增与合并

```python
async def add_memory(user_id, content, source, init_weight):
    if init_weight < MIN_INIT_WEIGHT: return            # 准入门槛
    若存在完全相同的 content（strip 后相等）：
        item.weight = min(10.0, item.weight + init_weight * 0.4)   # 强化 +40%
        item.update_access()
    否则：新建 MemoryItem.create(...)
```

### 4.4 注入 Agent

```python
async def build_prompt_snippet(user_id) -> str:
    memories = await recall_user_memory(user_id)        # 已衰减 + TOP-K
    每条形如 "- {content[:120]}"
    返回 "【用户历史旅行偏好】\n- …\n- …"；无记忆返回 ""
```

该文本由 `routes/trip.py` 在规划前取得，作为 `memory_snippet` 传给 `_build_planner_query()`，
插在"基本信息"之后，并附一句"请在规划时充分参考以上用户历史偏好…"。

## 5. 偏好提取（`preference_extractor.py`）

- 复用 `chat_service` 的**直连 httpx** 方式（不走 hello-agents），地址/模型/密钥实时读配置（支持设置页热更新），`trust_env=False`。
- 提示词要点：只提取**长期稳定偏好**，临时目的地与单次安排不要提取；每条给 0~10 分；输出 JSON 数组；无偏好返回 `[]`；只输出 JSON。
- 调用参数：`temperature=0.2`、`max_tokens=800`；行程内容截断 6000 字符。
- 返回 `List[(content, score)]`，并**在提取层就过滤** `score < MIN_INIT_WEIGHT` 的条目。

## 6. 触发时机（`routes/trip.py`）

```python
_user_id = (request.user_id or "").strip()
if _user_id and os.getenv("ENABLE_USER_MEMORY","false").lower() == "true":
    asyncio.create_task(_save_preferences_after_trip(_user_id, request, trip_plan))   # 不阻塞主流程
```

`_save_preferences_after_trip` 组装 `user_query`（城市/偏好/额外要求）+ `trip_content`（计划 JSON），
调 `PreferenceExtractor.extract_preferences()`，再逐条 `MemoryManager.add_memory(source="implicit")`。
任何异常只记录日志，不影响行程结果。

## 7. 用户 ID

前端 `services/api.ts` 的 `getOrCreateUserId()`：`localStorage['tripstar.user_id']`，首次用 `crypto.randomUUID()`
（不支持时 `Date.now()+random`）。提交行程时自动写入 `TripFormData.user_id`。

## 8. 复刻检查清单

- [ ] `weight *= 0.97^days_since_last_access`，阈值 2.0，读时惰性计算并删弱项。
- [ ] 相同文本合并 `+40%` 并封顶 10，同时刷新 `last_access_time`。
- [ ] 新增有准入门槛（4.0），手动添加给高初始权重（8.5）。
- [ ] 召回 = 衰减过滤 → 权重降序 → TOP-K(10)。
- [ ] 注入文本单条截断 120 字，整体最多 10 条。
- [ ] 记忆模块默认关闭，且提取失败不影响主流程。
- [ ] `user_id` 由前端生成并持久化，后端只当作不透明标识。