"""JSON 五级容错解析测试。

覆盖 `trip_planner_agent.py` 里四个纯字符串处理函数：
    _sanitize_json_str / _fix_unescaped_quotes / _repair_truncated_json / _parse_response

这些函数是「大模型输出坏 JSON 时不让整个任务失败」的关键防线，
但它们全是纯函数变换，非常适合单测——这也是补测试的第一优先级。
"""

import json

import pytest


# ============ _sanitize_json_str：清理格式污染 ============

class TestSanitizeJsonStr:

    def test_移除_markdown_代码块包裹(self, planner):
        raw = '```json\n{"city": "大理"}\n```'
        assert json.loads(planner._sanitize_json_str(raw)) == {"city": "大理"}

    def test_移除无语言标记的代码块(self, planner):
        raw = '```\n{"a": 1}\n```'
        assert json.loads(planner._sanitize_json_str(raw)) == {"a": 1}

    def test_移除_js_风格注释(self, planner):
        raw = '{\n// 这是注释\n"a": 1,\n/* 块注释 */\n"b": 2\n}'
        assert json.loads(planner._sanitize_json_str(raw)) == {"a": 1, "b": 2}

    def test_移除尾部逗号(self, planner):
        # 大模型很常见的错误：多一个逗号
        raw = '{"a": 1, "b": [1, 2, ], }'
        assert json.loads(planner._sanitize_json_str(raw)) == {"a": 1, "b": [1, 2]}

    def test_移除控制字符(self, planner):
        raw = '{"a": "x\x00\x07y"}'
        assert json.loads(planner._sanitize_json_str(raw)) == {"a": "xy"}

    def test_中文引号转为单引号而不破坏结构(self, planner):
        """中文双引号出现在字符串**值内部**，若替换成标准双引号会破坏 JSON 结构。

        这是原实现的注释里明确写到的坑，这里固化为回归用例。
        """
        raw = '{"description": "他说\u201c你好\u201d就走了"}'
        cleaned = planner._sanitize_json_str(raw)
        parsed = json.loads(cleaned)  # 不抛异常即说明结构未被破坏
        assert "你好" in parsed["description"]

    def test_全角冒号与逗号被替换(self, planner):
        raw = '{"a"\uff1a1\uff0c"b"\uff1a2}'
        assert json.loads(planner._sanitize_json_str(raw)) == {"a": 1, "b": 2}

    def test_算术表达式被求值(self, planner):
        """模型有时会把预算写成 30+54=84，直接解析会失败。"""
        raw = '{"total": 30+54+120=204}'
        assert json.loads(planner._sanitize_json_str(raw))["total"] == 204

    def test_算术表达式无等号时安全求值(self, planner):
        raw = '{"total": 30+54}'
        assert json.loads(planner._sanitize_json_str(raw))["total"] == 84

    def test_无等号且表达式非法时不崩溃(self, planner):
        """非法表达式应原样保留（后续解析失败会被下一级修复接管），不能抛异常。"""
        raw = '{"total": 1+}'
        # 不应抛异常
        planner._sanitize_json_str(raw)


# ============ _fix_unescaped_quotes：修复值内未转义引号 ============

class TestFixUnescapedQuotes:

    def test_值内部未转义引号被修正(self, planner):
        raw = '{"description": "这是"好的"景点"}'
        fixed = planner._fix_unescaped_quotes(raw)
        # 修复后应能被解析
        assert json.loads(fixed)["description"] == "这是'好的'景点"

    def test_正常_json_不被改动(self, planner):
        raw = '{"a": "b", "c": "d"}'
        assert json.loads(planner._fix_unescaped_quotes(raw)) == {"a": "b", "c": "d"}

    def test_已转义的引号不受影响(self, planner):
        raw = '{"a": "say \\"hi\\""}'
        assert json.loads(planner._fix_unescaped_quotes(raw))["a"] == 'say "hi"'

    def test_嵌套结构与数组末尾引号识别(self, planner):
        raw = '{"list": [{"n": "x"}]}'
        assert json.loads(planner._fix_unescaped_quotes(raw)) == {"list": [{"n": "x"}]}


# ============ _repair_truncated_json：截断补全 ============

class TestRepairTruncatedJson:

    def test_截断的字符串值被闭合(self, planner):
        raw = '{"city": "大理", "desc": "这是一个被截断的描'
        assert json.loads(planner._repair_truncated_json(raw))["city"] == "大理"

    def test_缺失的闭合括号被补齐(self, planner):
        raw = '{"days": [{"date": "2026-05-01"}'
        parsed = json.loads(planner._repair_truncated_json(raw))
        assert parsed["days"][0]["date"] == "2026-05-01"

    def test_多层嵌套缺失括号被补齐(self, planner):
        raw = '{"a": {"b": {"c": [1, 2'
        parsed = json.loads(planner._repair_truncated_json(raw))
        assert parsed["a"]["b"]["c"] == [1, 2]

    def test_尾部悬挂逗号被移除(self, planner):
        raw = '{"a": 1, "b": 2,'
        assert json.loads(planner._repair_truncated_json(raw)) == {"a": 1, "b": 2}

    def test_已完整的_json_保持不变(self, planner):
        raw = '{"a": 1, "b": [1, 2]}'
        assert json.loads(planner._repair_truncated_json(raw)) == {"a": 1, "b": [1, 2]}

    def test_无法修复时返回空串(self, planner):
        """返回空串表示「修不了」，由上层容错链继续试别的候选，而不是抛异常中断。"""
        assert planner._repair_truncated_json("完全不是JSON") == ""

    def test_空输入抛_ValueError(self, planner):
        with pytest.raises(ValueError, match="为空"):
            planner._repair_truncated_json("")

    def test_截断点落在键名中间时可修复(self, planner):
        """回归用例：截断点正好切在键名中间（如 `"attrac`）。

        原实现只做「闭合字符串 + 补括号」，会把残缺键名补成一个合法但无意义的
        键（`"attrac"`），紧跟着没有冒号和值，JSON 仍然非法。
        """
        raw = '{"days": [{"date": "2026-05-01", "attrac'
        repaired = planner._repair_truncated_json(raw)
        parsed = json.loads(repaired)  # 不应抛异常
        assert parsed["days"][0]["date"] == "2026-05-01"

    def test_截断点在键的冒号后无值时可修复(self, planner):
        raw = '{"city": "大理", "days":'
        parsed = json.loads(planner._repair_truncated_json(raw))
        assert parsed["city"] == "大理"


# ============ _parse_response：端到端容错链路 ============

VALID_PLAN = {
    "city": "大理",
    "cities": ["大理"],
    "start_date": "2026-05-01",
    "end_date": "2026-05-03",
    "days": [
        {
            "date": "2026-05-01",
            "day_index": 0,
            "city": "大理",
            "description": "抵达并游览",
            "transportation": "公共交通",
            "accommodation": "民宿",
            "attractions": [],
            "meals": [],
        }
    ],
    "weather_info": [],
    "overall_suggestions": "注意防晒",
}


class TestParseResponse:

    def test_标准代码块输出可解析(self, planner, trip_request_factory):
        response = "好的，这是您的行程：\n```json\n" + json.dumps(VALID_PLAN, ensure_ascii=False) + "\n```\n希望有帮助！"
        plan = planner._parse_response(response, trip_request_factory())
        assert plan.city == "大理"
        assert len(plan.days) == 1

    def test_裸_json_输出可解析(self, planner, trip_request_factory):
        response = json.dumps(VALID_PLAN, ensure_ascii=False)
        assert planner._parse_response(response, trip_request_factory()).city == "大理"

    def test_带尾部逗号的坏_json_可解析(self, planner, trip_request_factory):
        broken = json.dumps(VALID_PLAN, ensure_ascii=False).replace('"weather_info": []', '"weather_info": [],')
        assert planner._parse_response(broken, trip_request_factory()).city == "大理"

    def test_被截断的输出可解析(self, planner, trip_request_factory):
        """截断点落在尾部可选字段时，必填字段必须被保住。

        构造要求：必填字段（city/start_date/end_date）排在前面，
        可选且靠后的字段（overall_suggestions）才是被截断的部分。
        """
        full = json.dumps(VALID_PLAN, ensure_ascii=False)
        cut = full.rindex('"overall_suggestions"')   # 从最后一个字段开始截断
        plan = planner._parse_response(full[:cut + 8], trip_request_factory())
        assert plan.city == "大理"
        assert len(plan.days) == 1

    def test_未闭合代码块可解析(self, planner, trip_request_factory):
        """模型输出到一半达到 token 上限，``` 没闭合。"""
        response = "```json\n" + json.dumps(VALID_PLAN, ensure_ascii=False)
        assert planner._parse_response(response, trip_request_factory()).city == "大理"

    def test_温度带单位被_validator_清洗(self, planner, trip_request_factory):
        """结构化输出常见问题：数值带单位。pydantic validator 应自动清洗。"""
        payload = dict(VALID_PLAN)
        payload["weather_info"] = [
            {"date": "2026-05-01", "city": "大理", "day_temp": "23°C", "night_temp": 10}
        ]
        plan = planner._parse_response(json.dumps(payload, ensure_ascii=False), trip_request_factory())
        assert plan.weather_info[0].day_temp == 23
        assert plan.weather_info[0].night_temp == 10

    def test_景点坐标可为_null(self, planner, trip_request_factory):
        """schema 已允许 location 为 None（宁可缺坐标也不许 LLM 编造）。"""
        payload = dict(VALID_PLAN)
        payload["days"] = [
            {
                "date": "2026-05-01",
                "day_index": 0,
                "city": "大理",
                "description": "游览",
                "transportation": "步行",
                "accommodation": "民宿",
                "attractions": [
                    {"name": "海舌公园", "location": None, "description": "半岛公园"},
                    {"name": "洱海", "location": {"longitude": 100.2, "latitude": 25.6}, "description": "湖"},
                ],
                "meals": [],
            }
        ]
        plan = planner._parse_response(json.dumps(payload, ensure_ascii=False), trip_request_factory())
        assert plan.days[0].attractions[0].location is None
        assert plan.days[0].attractions[1].location.longitude == 100.2

    def test_完全无法解析时返回兜底骨架(self, planner, trip_request_factory):
        """行为定义：解析彻底失败时返回骨架计划（结构真实、内容留空），
        而不是抛异常——这样前端能展示「日期结构 + 失败说明」。
        详见 TestFallbackPlan。"""
        plan = planner._parse_response("这里完全没有 JSON 内容", trip_request_factory())
        assert plan.days
        assert all(not d.attractions for d in plan.days)

    def test_响应中无_json_时返回兜底骨架(self, planner, trip_request_factory):
        plan = planner._parse_response("抱歉，我无法生成行程。", trip_request_factory())
        assert all(not d.attractions for d in plan.days)


class TestFallbackPlan:
    """兜底骨架必须「结构真实、内容不编造」。"""

    def test_不编造景点与坐标(self, planner, trip_request_factory):
        plan = planner._create_fallback_plan(trip_request_factory([("大理", 3)]))
        for day in plan.days:
            assert day.attractions == [], "兜底计划不得编造景点"
            assert day.meals == [], "兜底计划不得编造餐饮"

    def test_城市与日期结构真实(self, planner, trip_request_factory):
        plan = planner._create_fallback_plan(trip_request_factory([("昆明", 2), ("大理", 2)]))
        assert plan.cities == ["昆明", "大理"]
        assert plan.city == "昆明"
        assert len(plan.days) == 4
        # 各城市停留天数应正确分配到每天
        assert [d.city for d in plan.days] == ["昆明", "昆明", "大理", "大理"]
        # 日期连续
        assert [d.date for d in plan.days] == [
            "2026-05-01", "2026-05-02", "2026-05-03", "2026-05-04",
        ]

    def test_明确说明失败原因(self, planner, trip_request_factory):
        plan = planner._create_fallback_plan(trip_request_factory())
        assert "重新生成" in plan.overall_suggestions
        assert "重新生成" in plan.days[0].description

    def test_继承用户的交通与住宿偏好(self, planner, trip_request_factory):
        req = trip_request_factory(transportation="自驾", accommodation="豪华酒店")
        plan = planner._create_fallback_plan(req)
        assert plan.days[0].transportation == "自驾"
        assert plan.days[0].accommodation == "豪华酒店"

    def test_解析彻底失败时返回兜底骨架而非抛异常(self, planner, trip_request_factory):
        """端到端：完全无法解析的响应应得到骨架计划，让前端能展示提示。"""
        plan = planner._parse_response("这里没有任何 JSON", trip_request_factory())
        assert plan.days, "应返回带日期结构的骨架"
        assert all(not d.attractions for d in plan.days)
