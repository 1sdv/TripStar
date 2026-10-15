# 灌库素材格式样例

这个目录是 `backend/scripts/ingest_yunnan.py` 的输入格式参考，**不是可直接使用的知识库数据**。
正式灌库时请替换成你自己的游记/攻略素材。

## 三种格式

### 1. `.md` —— 带 frontmatter（推荐，适合手工整理）

```markdown
---
title: 大理洱海西岸小众骑行路线实测
destination: 大理市          # 可写别名，脚本会归一化成「云南大理」
source_url: https://example.com/xxx
like_count: 321              # 可选，用于检索时的热度破平局
source_id: dali-001          # 可选，用于生成稳定的 post_id
---
正文内容……
```

`title` 缺失时会退而取正文里第一个 `#` 标题，再退而取文件名。

### 2. `.txt` —— 纯文本（适合直接粘贴）

没有元数据，目的地会**从标题与正文前 200 字里自动推断**（取最先出现的云南城市）。

### 3. `.jsonl` —— 爬虫直出（适合批量）

每行一个 JSON 对象，键名兼容多种别名：

| 字段 | 兼容写法 |
|---|---|
| 标题 | `title` / `name` |
| 正文 | `content` / `text` / `desc` |
| 目的地 | `destination` / `city` |
| 链接 | `url` / `source_url` |
| 热度 | `like_count` / `likeCount` |
| 稳定 ID | `post_id` / `id` |

## 两条必须遵守的约束

1. **目的地只能是云南白名单内的城市**（`app/services/rag/ingest.py` 里的
   `_YUNNAN_CITIES` + `_ALIAS`）。非云南目的地会被**直接拒绝入库**——
   这是有意的：`destination` 是检索时按城市过滤的依据，写错或写杂会让该城市
   **永远检索不到**，比不入库更糟。
2. **`destination` 会被归一化成「省+市」格式**（如 `云南大理`）。
   你可以写 `大理` / `大理市` / `大理白族自治州`，脚本都会转成 `云南大理`。

## 建议流程

```bash
# 1) 先干跑：只解析不写库，检查每篇文档识别出的目的地对不对
python backend/scripts/ingest_yunnan.py backend/data/kb_samples --dry-run

# 2) 确认无误后正式灌入（幂等，可重复执行）
python backend/scripts/ingest_yunnan.py backend/data/kb_samples

# 3) 查看知识库覆盖分布
python backend/scripts/kb_stats.py 20
```

> 干跑这一步很重要：目的地推断是按「首次出现位置」取城市名的，
> 像「建水古城比大理安静太多」这种对比句如果处理不当会误判——
> 脚本已修正该问题，但换用新素材时仍建议先干跑确认。

## 关于 Embedding 模型

入库与检索**必须使用同一个 embedding 模型**（默认 `BAAI/bge-m3`，1024 维）。
更换 `EMBEDDING_MODEL` 会让已有向量失效，需要清空 `backend/data/chroma` 重新灌库。
