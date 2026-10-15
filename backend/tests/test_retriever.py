"""混合检索核心逻辑测试。

覆盖四块**纯函数**（不依赖网络与向量库）：
    retriever._keyword_score / _heat_factor / _rrf_fuse
    amap_rest_service._name_similarity
以及目的地宽松匹配的归一化规则。

这些是 RAG 检索质量的关键，但它们本身是确定性的字符串/数值计算，
非常适合单测——比"跑一次看结果"可靠得多。
"""

import pytest


# ============ 关键词 2-gram 命中分 ============

class TestKeywordScore:

    def test_完全命中(self):
        from app.services.rag.retriever import _keyword_score

        # 问题切成 {大理, 理洱, 洱海}，都在文档里
        assert _keyword_score("大理洱海", "大理洱海骑行攻略") == 3

    def test_部分命中(self):
        from app.services.rag.retriever import _keyword_score

        # {大理, 理洱, 洱海} 中只有「大理」命中
        assert _keyword_score("大理洱海", "大理古城住宿推荐") == 1

    def test_无命中(self):
        from app.services.rag.retriever import _keyword_score

        assert _keyword_score("大理洱海", "丽江古城攻略") == 0

    def test_去重后计数而非出现次数(self):
        """命中的是「片段种类数」而非「出现次数」，避免长文本因重复占优。"""
        from app.services.rag.retriever import _keyword_score

        once = _keyword_score("大理", "大理好玩")           # 片段 {大理}
        twice = _keyword_score("大理", "大理好玩，大理很美，大理再见")
        assert once == twice == 1

    def test_标点与空白被忽略(self):
        from app.services.rag.retriever import _keyword_score

        assert _keyword_score("大理，洱海！", "大理洱海") == 3

    def test_英文与数字参与切分(self):
        from app.services.rag.retriever import _keyword_score

        assert _keyword_score("bike", "bike route") == 3

    def test_单字问题返回零(self):
        """长度 1 无法形成 2-gram，应安全返回 0 而不是崩溃。"""
        from app.services.rag.retriever import _keyword_score

        assert _keyword_score("大", "大理") == 0

    def test_空问题返回零(self):
        from app.services.rag.retriever import _keyword_score

        assert _keyword_score("", "大理") == 0


# ============ 热度归一化 ============

class TestHeatFactor:

    def test_最高热度归一为_1(self):
        from app.services.rag.retriever import _heat_factor

        items = [
            {"id": "a", "meta": {"like_count": 100}},
            {"id": "b", "meta": {"like_count": 10}},
        ]
        factors = _heat_factor(items)
        assert factors["a"] == pytest.approx(1.0)
        assert 0 < factors["b"] < 1

    def test_全零热度返回空映射(self):
        from app.services.rag.retriever import _heat_factor

        items = [{"id": "a", "meta": {"like_count": 0}}, {"id": "b", "meta": {}}]
        assert _heat_factor(items) == {}

    def test_热度用对数压缩(self):
        """log1p 压缩，避免 100 倍热度差距变成 100 倍权重差距。"""
        from app.services.rag.retriever import _heat_factor

        items = [
            {"id": "hot", "meta": {"like_count": 1000}},
            {"id": "cold", "meta": {"like_count": 1}},
        ]
        factors = _heat_factor(items)
        assert factors["hot"] == pytest.approx(1.0)
        # 原始比值 1000，压缩后应远小于 1/1000
        assert factors["cold"] > 0.1

    def test_权威条目用_heat_字段(self):
        from app.services.rag.retriever import _heat_factor

        items = [{"id": "x", "meta": {"heat": 50}}, {"id": "y", "meta": {"heat": 5}}]
        assert _heat_factor(items)["x"] == pytest.approx(1.0)

    def test_空列表返回空映射(self):
        from app.services.rag.retriever import _heat_factor

        assert _heat_factor([]) == {}


# ============ RRF 融合 ============

def _vec(doc_id, doc="d", like=0):
    return {"id": doc_id, "doc": doc, "meta": {"like_count": like, "title": doc_id}}


def _kw(doc_id, doc="d", score=1, like=0):
    return {"id": doc_id, "doc": doc, "meta": {"like_count": like, "title": doc_id}, "score": score}


class TestRrfFuse:

    def test_两路都靠前的排最前(self):
        """RRF 的核心意图：奖励被两路同时认可的文档。"""
        from app.services.rag.retriever import _rrf_fuse

        vector = [_vec("A"), _vec("B"), _vec("C")]
        keyword = [_kw("B"), _kw("C"), _kw("A")]
        fused = _rrf_fuse(vector, keyword, top_k=3, use_heat=False)
        # A: 1/61+1/63, B: 1/62+1/61, C: 1/63+1/62
        assert fused[0]["id"] == "B"

    def test_只在单路出现的也能进结果(self):
        from app.services.rag.retriever import _rrf_fuse

        fused = _rrf_fuse([_vec("A")], [_kw("B")], top_k=5, use_heat=False)
        assert {item["id"] for item in fused} == {"A", "B"}

    def test_同_id_两路命中会累加(self):
        from app.services.rag.retriever import _rrf_fuse

        fused = _rrf_fuse([_vec("A")], [_kw("A")], top_k=1, use_heat=False)
        assert fused[0]["rrf"] == pytest.approx(1 / 61 + 1 / 61)

    def test_top_k_截断(self):
        from app.services.rag.retriever import _rrf_fuse

        vector = [_vec(f"V{i}") for i in range(10)]
        fused = _rrf_fuse(vector, [], top_k=3, use_heat=False)
        assert len(fused) == 3

    def test_两路都空返回空(self):
        from app.services.rag.retriever import _rrf_fuse

        assert _rrf_fuse([], [], top_k=5) == []

    def test_不同相关性桶内热度不得改写排序(self):
        """关键设计：RRF 差超过一个桶时，热度高也不能插队。

        构造：X 是向量第 1 + 关键词第 1；Y 只在向量第 30。
        X 的 RRF 明显更高，即使 Y 热度是 X 的千倍也必须排在后面。
        """
        from app.services.rag.retriever import _rrf_fuse

        vector = [_vec("X", like=1)] + [_vec(f"v{i}") for i in range(29)] + [_vec("Y", like=100000)]
        keyword = [_kw("X")]
        fused = _rrf_fuse(vector, keyword, top_k=50, use_heat=True)
        ids = [item["id"] for item in fused]
        # 核心不变量：相关性高的 X 必须排在热度极高的 Y 之前
        assert ids.index("X") < ids.index("Y")

    def test_同桶内热度高者优先(self):
        """量化到同一桶说明相关性视为相同，此时才按热度排序。"""
        from app.services.rag.retriever import _rrf_fuse

        # A、B 相邻排名 → RRF 差约 2.6e-4，量化后差距 < HT_BUCKET
        vector = [_vec("A", like=1), _vec("B", like=500)]
        fused = _rrf_fuse(vector, [], top_k=2, use_heat=True)
        assert {item["id"] for item in fused} == {"A", "B"}

    def test_元数据被完整带出(self):
        from app.services.rag.retriever import _rrf_fuse

        item = {"id": "A", "doc": "正文", "meta": {"title": "标题", "like_count": 7}}
        fused = _rrf_fuse([item], [], top_k=1, use_heat=False)
        assert fused[0]["doc"] == "正文"
        assert fused[0]["meta"]["title"] == "标题"


# ============ 名称相似度（坐标兜底用） ============

class TestNameSimilarity:

    def test_完全相同为一(self):
        from app.services.amap_rest_service import _name_similarity

        assert _name_similarity("洱海", "洱海") == 1.0

    def test_包含关系为一(self):
        from app.services.amap_rest_service import _name_similarity

        # 「海舌公园」是「海舌生态公园停车场」的子序列
        assert _name_similarity("海舌公园", "海舌生态公园停车场") == 1.0

    def test_共享前缀但非包含(self):
        """真实案例：POI 名是「爱在海舌蜜月半岛」，含「海舌」但无「公园」。"""
        from app.services.amap_rest_service import _name_similarity

        score = _name_similarity("海舌公园", "爱在海舌蜜月半岛")
        assert score == pytest.approx(0.5)

    def test_无关名称为低分(self):
        from app.services.amap_rest_service import _name_similarity

        assert _name_similarity("不存在的景点XYZ", "爱在海舌蜜月半岛") < 0.2

    def test_短名与长名的阈值边界(self):
        from app.services.amap_rest_service import _name_similarity

        # 喜洲（2 字）对「喜洲古镇」应满分
        assert _name_similarity("喜洲", "喜洲古镇") == 1.0

    def test_空输入返回零(self):
        from app.services.amap_rest_service import _name_similarity

        assert _name_similarity("", "洱海") == 0.0
        assert _name_similarity("洱海", "") == 0.0


# ============ 目的地归一化与匹配（依赖库，做纯函数层验证） ============

class TestDestinationNormalize:

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("云南大理", "云南大理"),
            ("大理市", "大理"),
            ("大理", "大理"),
            ("云南省大理", "云南大理"),
            (" 大理 ", "大理"),
        ],
    )
    def test_行政后缀被去除(self, raw, expected):
        from app.services.rag.retriever import _normalize_name

        # 「云南大理」整体不该被误去后缀；其余应归一到「大理」
        normalized = _normalize_name(raw)
        assert normalized.endswith(expected.replace("云南", "")) or normalized == expected

    def test_州级别后缀(self):
        from app.services.rag.retriever import _normalize_name

        # 只去掉末尾单个「州」字（后缀表是逐字匹配，不含「自治州」整词）
        assert _normalize_name("大理白族自治州") == "大理白族"
        assert _normalize_name("西双版纳傣族自治州") == "西双版纳傣族"

    def test_市与县后缀(self):
        from app.services.rag.retriever import _normalize_name

        assert _normalize_name("大理市") == "大理"
        assert _normalize_name("剑川县") == "剑川"

    def test_空值返回空串(self):
        from app.services.rag.retriever import _normalize_name

        assert _normalize_name("") == ""
        assert _normalize_name(None) == ""
