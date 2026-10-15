"""知识库灌入契约测试。

这里验证的是「数据进得去、检索查得到」的几条硬约束：
    ① destination 必须归一化成「云南X」原子值（写错=永远检索不到）
    ② 目的地推断按「首次出现位置」而不是名称长度（真实踩过的 bug）
    ③ post_id 必须是唯一正整数（为 0 会让检索去重退化）
    ④ 切块参数与文档长度下限
    ⑤ 三种素材格式的解析
"""

import json

import pytest


# ============ ① 目的地归一化 ============

class TestNormalizeDestination:

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("大理", "云南大理"),
            ("大理市", "云南大理"),
            ("大理白族自治州", "云南大理"),
            ("云南大理", "云南大理"),
            ("云南省大理", "云南大理"),
            ("丽江", "云南丽江"),
            ("景洪", "云南西双版纳"),      # 别名映射
            ("中甸", "云南香格里拉"),      # 旧称映射
            ("宁蒗", "云南泸沽湖"),        # 别名映射
        ],
    )
    def test_云南城市被规范化(self, raw, expected):
        from app.services.rag.ingest import normalize_destination

        dest, _ = normalize_destination(raw)
        assert dest == expected

    @pytest.mark.parametrize("raw", ["北京", "上海", "成都", "广州", "火星"])
    def test_非云南目的地被拒绝(self, raw):
        """拒绝而非放行：错误的目的地会让检索永远查不到，必须在源头卡住。"""
        from app.services.rag.ingest import normalize_destination

        dest, reason = normalize_destination(raw)
        assert dest == ""
        assert "白名单" in reason

    def test_目的地为空时按内容推断(self):
        """推断只扫「标题 + 正文前 200 字」（有意的性能设计），
        因此真实素材的城市名要在开头出现——游记通常开篇就点明地点。"""
        from app.services.rag.ingest import normalize_destination

        dest, reason = normalize_destination("", content="大理洱海骑行很舒服，从才村码头出发。", title="环海攻略")
        assert dest == "云南大理"
        assert "推断" in reason

    def test_超出前200字不参与推断(self):
        """明确记录这个设计边界：靠后的城市名不参与推断。"""
        from app.services.rag.ingest import normalize_destination

        dest, reason = normalize_destination("", content="很长的开场白" * 60 + "后面才提到大理", title="无标题")
        assert dest == ""

    def test_推断按首次出现位置而非名称长度(self):
        """回归用例：真实踩过的 bug。

        「建水古城比大理安静太多」——`大理` 先出现，但按名称长度排序会先命中
        更长的城市名，导致整篇被误标。必须按**首次出现位置**取。
        """
        from app.services.rag.ingest import normalize_destination

        content = "建水古城比大理安静太多，临安路的青石板路晚上几乎没人。"
        dest, _ = normalize_destination("", content=content, title="建水慢游")
        assert dest == "云南建水"

    def test_无法判定时返回空并给原因(self):
        from app.services.rag.ingest import normalize_destination

        dest, reason = normalize_destination("", content="今天天气不错", title="随笔")
        assert dest == ""
        assert "无法判定" in reason


# ============ ② post_id 契约 ============

class TestMakePostId:

    def test_是正整数(self):
        from app.services.rag.ingest import make_post_id

        pid = make_post_id("https://example.com/a")
        assert isinstance(pid, int)
        assert pid > 0

    def test_同输入稳定可复现(self):
        """幂等重灌依赖这一点：同一篇文档每次算出的 post_id 必须相同。"""
        from app.services.rag.ingest import make_post_id

        assert make_post_id("seed-1") == make_post_id("seed-1")

    def test_不同输入不碰撞(self):
        from app.services.rag.ingest import make_post_id

        ids = {make_post_id(f"seed-{i}") for i in range(200)}
        assert len(ids) == 200

    def test_优先使用靠前的候选(self):
        from app.services.rag.ingest import make_post_id

        assert make_post_id("first", "second") == make_post_id("first")

    def test_跳过空候选(self):
        from app.services.rag.ingest import make_post_id

        assert make_post_id("", None, "real") == make_post_id("real")

    def test_全空时抛异常(self):
        from app.services.rag.ingest import make_post_id

        with pytest.raises(ValueError):
            make_post_id("", None)


# ============ ③ 切块 ============

class TestChunkText:

    def test_短文本单块(self):
        from app.services.rag.ingest import chunk_text

        chunks = chunk_text("很短的正文", chunk_size=100)
        assert chunks == ["很短的正文"]

    def test_长文本多块且带重叠(self):
        from app.services.rag.ingest import chunk_text

        text = "字" * 250
        chunks = chunk_text(text, chunk_size=100, overlap=20)
        assert len(chunks) == 3
        # 相邻块重叠 20 字
        assert chunks[0][-20:] == chunks[1][:20]

    def test_不丢内容(self):
        from app.services.rag.ingest import chunk_text

        text = "".join(str(i % 10) for i in range(500))
        chunks = chunk_text(text, chunk_size=100, overlap=25)
        assert chunks[0][0] == "0"
        assert chunks[-1][-1] == text[-1]

    def test_空文本返回空列表(self):
        from app.services.rag.ingest import chunk_text

        assert chunk_text("") == []
        assert chunk_text("   ") == []


# ============ ④ 三种素材格式解析 ============

class TestParseMarkdown:

    def test_解析_frontmatter(self, tmp_path):
        from app.services.rag.ingest import parse_markdown

        f = tmp_path / "dali.md"
        f.write_text(
            "---\n"
            "title: 大理环洱海骑行\n"
            "destination: 大理市\n"
            "like_count: 321\n"
            "source_url: https://example.com/x\n"
            "---\n"
            "正文内容在这里，足够长以满足最小长度要求。" * 3,
            encoding="utf-8",
        )
        doc = parse_markdown(f)
        assert doc.title == "大理环洱海骑行"
        assert doc.destination == "云南大理"
        assert doc.like_count == 321
        assert doc.source_url == "https://example.com/x"
        assert doc.post_id > 0

    def test_无_frontmatter_时取一级标题(self, tmp_path):
        from app.services.rag.ingest import parse_markdown

        f = tmp_path / "x.md"
        f.write_text("# 丽江古城攻略\n\n正文" * 20, encoding="utf-8")
        doc = parse_markdown(f)
        assert doc.title == "丽江古城攻略"

    def test_无标题时退回文件名(self, tmp_path):
        from app.services.rag.ingest import parse_markdown

        f = tmp_path / "shangrila.md"
        f.write_text("独克宗古城的转经筒很大。" * 10, encoding="utf-8")
        doc = parse_markdown(f)
        assert doc.title == "shangrila"


class TestParseJsonl:

    def test_多行解析与字段别名兼容(self, tmp_path):
        from app.services.rag.ingest import parse_jsonl

        f = tmp_path / "crawl.jsonl"
        lines = [
            {"title": "A", "destination": "丽江", "content": "内容" * 20},
            {"name": "B", "city": "大理", "text": "正文" * 20, "likeCount": 7, "url": "https://e.com/b"},
        ]
        f.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in lines), encoding="utf-8")
        docs = parse_jsonl(f)
        assert len(docs) == 2
        assert docs[0].destination == "云南丽江"
        assert docs[1].destination == "云南大理"
        assert docs[1].title == "B"
        assert docs[1].like_count == 7
        assert docs[1].source_url == "https://e.com/b"

    def test_坏行被跳过而不中断(self, tmp_path):
        from app.services.rag.ingest import parse_jsonl

        f = tmp_path / "bad.jsonl"
        f.write_text(
            '{"title": "OK", "destination": "大理", "content": "' + "内容" * 20 + '"}\n'
            "这不是 JSON\n"
            '{"title": "OK2", "destination": "丽江", "content": "' + "正文" * 20 + '"}\n',
            encoding="utf-8",
        )
        docs = parse_jsonl(f)
        assert len(docs) == 2

    def test_行号用于生成唯一_post_id(self, tmp_path):
        from app.services.rag.ingest import parse_jsonl

        f = tmp_path / "dup.jsonl"
        # 两条都没有 id/url，只能靠行号区分
        body = json.dumps({"title": "同名", "destination": "大理", "content": "内容" * 20}, ensure_ascii=False)
        f.write_text(body + "\n" + body + "\n", encoding="utf-8")
        docs = parse_jsonl(f)
        assert docs[0].post_id != docs[1].post_id


class TestParseTxt:

    def test_纯文本按内容推断目的地(self, tmp_path):
        from app.services.rag.ingest import parse_txt

        f = tmp_path / "shangrila.txt"
        f.write_text("香格里拉三天怎么安排\n第一天到独克宗古城适应海拔。" * 5, encoding="utf-8")
        doc = parse_txt(f)
        assert doc.destination == "云南香格里拉"
        assert doc.title == "shangrila"

    def test_非云南文本目的地为空(self, tmp_path):
        from app.services.rag.ingest import parse_txt

        f = tmp_path / "bj.txt"
        f.write_text("北京故宫游玩攻略。" * 20, encoding="utf-8")
        doc = parse_txt(f)
        assert doc.destination == ""


# ============ ⑤ 文档加载 ============

class TestLoadDocuments:

    def test_目录递归加载三种格式(self, tmp_path):
        from app.services.rag.ingest import load_documents

        (tmp_path / "a.md").write_text("---\ntitle: A\ndestination: 大理\n---\n" + "内容" * 40, encoding="utf-8")
        (tmp_path / "b.txt").write_text("丽江古城" * 30, encoding="utf-8")
        (tmp_path / "c.jsonl").write_text(
            json.dumps({"title": "C", "destination": "腾冲", "content": "正文" * 30}, ensure_ascii=False),
            encoding="utf-8",
        )
        docs = load_documents(tmp_path)
        assert len(docs) == 3
        assert {d.destination for d in docs} == {"云南大理", "云南丽江", "云南腾冲"}

    def test_忽略不支持的后缀(self, tmp_path):
        from app.services.rag.ingest import load_documents

        (tmp_path / "x.pdf").write_text("二进制垃圾", encoding="utf-8")
        assert load_documents(tmp_path) == []
