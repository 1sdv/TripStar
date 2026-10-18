"""回归测试：缺少目的地城市的请求必须在入口被拦截（422）。

背景
----
``TripRequest`` 的 ``city`` 默认空字符串、``cities`` 默认空列表，而
``normalize_cities`` 只在「其中一方有值」时做互补填充，**两边都为空时不做任何
检查**，于是这样的请求能通过校验：

* ``POST /api/trip/plan`` 先返回 ``200 {task_id}``；
* 后台任务 ``_run_trip_planning`` 里 ``_build_planner_query()`` 访问
  ``cities[0]``，抛出 ``IndexError: list index out of range``；
* 用户最终通过 WebSocket 看到的是
  「旅行计划生成失败: list index out of range」——一个既无法定位、
  也不提示真正原因的报错。

而 ``trip_planner_agent.py`` 里已经写着「``List[CityStay]`` — 已由
``normalize_cities`` 保证非空」，说明这本就是预期不变量，只是校验没有落实。

本文件完全离线：不访问网络、不需要任何 API Key。
"""

import sys
import unittest
from pathlib import Path
import tempfile
from unittest import mock

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from pydantic import ValidationError

from app.models.schemas import TripRequest


def _payload(**overrides):
    """一个除目的地城市外字段齐全的合法请求体。"""
    payload = {
        "start_date": "2026-05-01",
        "end_date": "2026-05-02",
        "travel_days": 2,
        "transportation": "公共交通",
        "accommodation": "经济型酒店",
        "preferences": ["历史文化"],
        "language": "zh",
    }
    payload.update(overrides)
    return payload


class TripRequestCityValidationTests(unittest.TestCase):
    """单元层：``cities`` 非空是后续流程依赖的不变量。"""

    def test_city_only_is_normalized_to_cities(self) -> None:
        request = TripRequest(**_payload(city="北京"))

        self.assertEqual([(c.city, c.days) for c in request.cities], [("北京", 2)])

    def test_cities_only_is_normalized_to_city(self) -> None:
        request = TripRequest(**_payload(cities=[{"city": "西安", "days": 3}]))

        self.assertEqual(request.city, "西安")

    def test_missing_city_and_cities_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            TripRequest(**_payload())

    def test_empty_cities_without_city_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            TripRequest(**_payload(cities=[]))

    def test_empty_city_string_without_cities_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            TripRequest(**_payload(city=""))

    def test_blank_city_among_valid_ones_is_rejected(self) -> None:
        """逐条检查，而不是「全部为空才拒绝」。

        若只判断「是否至少有一个非空」，下面这条请求会被接受，并带着一个空白
        城市名一路走到 trip_planner_agent，为那一天生成没有城市名的日程。
        这是模糊测试发现的漏洞（4000 轮随机组合中 1000 例破坏了不变量）。
        """
        with self.assertRaises(ValidationError):
            TripRequest(
                **_payload(cities=[{"city": "北京", "days": 2}, {"city": "", "days": 1}])
            )

    def test_blank_leading_city_is_rejected(self) -> None:
        """cities[0] 为空白时，city 会被填成空白，必须一并拒绝。"""
        with self.assertRaises(ValidationError):
            TripRequest(
                **_payload(cities=[{"city": "  ", "days": 2}, {"city": "上海", "days": 1}])
            )

    def test_whitespace_only_city_is_normalized_from_cities(self) -> None:
        """city 只有空白但 cities 有效时，取首个城市作为主城市，而不是保留空白。"""
        request = TripRequest(
            **_payload(city="   ", cities=[{"city": "广州", "days": 2}])
        )

        self.assertEqual(request.city, "广州")

    def test_multi_city_request_is_untouched(self) -> None:
        request = TripRequest(
            **_payload(cities=[{"city": "北京", "days": 2}, {"city": "西安", "days": 3}])
        )

        self.assertEqual([c.city for c in request.cities], ["北京", "西安"])
        self.assertEqual(request.city, "北京")


class PlanEndpointValidationTests(unittest.TestCase):
    """接口层：非法请求应在入口得到 422，而不是 200 之后异步失败。

    这两个用例会把请求真的发给应用，因此必须先把副作用隔离掉：
    一旦校验失效（即回归状态），``POST /api/trip/plan`` 会成功创建任务、
    启动后台规划并调用 ``_persist_task_state()`` 往
    ``backend/data/trip_tasks/`` 写 JSON——该目录被 .gitignore 忽略，
    ``git status`` 看不到，而 ``_load_persisted_tasks()`` 又会在下次导入时
    把它们读回来（打印「已加载 N 个持久化旅行任务」）。既污染仓库，
    又让测试变慢（实测 1.0s → 17.4s）。因此这里把任务目录指向临时目录，
    并把后台规划替换为 no-op，使测试在任何修复状态下都不产生外部副作用。
    """

    def setUp(self) -> None:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        async def _noop_run_trip_planning(task_id, request):  # pragma: no cover - 仅隔离用
            return None

        for patcher in (
            mock.patch("app.api.routes.trip._TASKS_DATA_DIR", Path(tmpdir.name)),
            mock.patch("app.api.routes.trip._run_trip_planning", new=_noop_run_trip_planning),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def _client(self):
        from fastapi.testclient import TestClient

        from app.api.main import app

        return TestClient(app)

    def test_plan_without_city_returns_422(self) -> None:
        response = self._client().post("/api/trip/plan", json=_payload())

        self.assertEqual(
            response.status_code,
            422,
            f"缺少目的地城市应被校验拦截，实际返回 {response.status_code}: {response.text[:200]}",
        )

    def test_validation_error_message_is_actionable(self) -> None:
        """422 的 detail 里必须给出可读原因。

        注意：该校验位于 model_validator(mode="after")，所以 FastAPI 返回的
        ``loc`` 是 ``["body"]`` 而不是 ``["body","city"]``——断言字段名只会
        因为中文提示里恰好含 "city" 而通过，属于假阳性。这里改为断言提示文本。
        """
        response = self._client().post("/api/trip/plan", json=_payload())

        self.assertEqual(response.status_code, 422)
        messages = " ".join(
            str(item.get("msg", "")) for item in response.json().get("detail", [])
        )
        self.assertIn("目的地城市", messages, f"422 未给出可读原因: {response.text[:200]}")

    def test_plan_with_blank_city_returns_422(self) -> None:
        """只有空白的城市名同样是无效输入，不能走到下游才炸。"""
        response = self._client().post("/api/trip/plan", json=_payload(city="   "))

        self.assertEqual(
            response.status_code,
            422,
            f"空白城市名应被校验拦截，实际返回 {response.status_code}: {response.text[:200]}",
        )


if __name__ == "__main__":
    unittest.main()
