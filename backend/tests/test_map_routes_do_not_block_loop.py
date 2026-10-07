"""回归测试：地图 / POI 路由不得阻塞事件循环。

背景
----
``backend/app/api/routes/map.py`` 与 ``poi.py`` 中的路由都是 ``async def``，
但它们直接调用了**同步**代码。阻塞来自两处：

1. **服务方法调用**（每次请求）：``AmapService`` 的方法最终走到 hello_agents
   的 ``MCPTool.run()``：

   * ``hello_agents/tools/builtin/protocol_tools.py:447-458``：另开一个事件循环
     放到**工作线程**里执行 MCP 操作，然后 ``return future.result()``——
     **阻塞当前调用线程**直到整个 MCP 往返结束；
   * 每次调用都会经 stdio 传输 spawn 一个 ``uvx amap-mcp-server`` 子进程
     （``hello_agents/protocols/mcp/client.py``），即进程启动 + 握手 + 调用。

2. **服务实例构造**（每个进程一次）：``get_amap_service()`` 是单例，首次调用会
   构造 ``MCPTool``，而 ``MCPTool.__init__`` 在
   ``protocol_tools.py:124`` 调用 ``self._discover_tools()``，后者同样在
   ``:271`` 的 ``future.result()`` 上阻塞——即启动后的**第一个**地图 / POI
   请求会额外承担一次 MCP 服务发现。

两处都发生在事件循环线程上，因此任何一个地图 / POI 请求都会把整个 uvicorn
worker 冻结数秒。冻结期间 ``/api/trip/status`` 轮询、``/api/trip/ws/{task_id}``
的进度推送、以及其它用户的请求全部停摆。行程规划过程中前端会并发拉取 POI 与
景点图片，所以这不是边缘场景。

用例做法：用「同步 sleep」的假服务 / 假工厂模拟上述阻塞，同时在旁边跑一个每
5ms 递增一次的 ticker。若阻塞留在事件循环线程上，ticker 会被饿死（约 0 次）；
反之会跑满约 50 次。

完全离线：不访问网络、不需要 API Key，也不启动任何子进程。
"""

import asyncio
import contextlib
import sys
import time
import types
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from app.api.routes import map as map_routes
from app.api.routes import poi as poi_routes
from app.models.schemas import RouteRequest
from app.services import amap_service

# 假阻塞的时长，以及 ticker 的间隔
BLOCK_SECONDS = 0.25
TICK_INTERVAL = 0.005
EXPECTED_TICKS = int(BLOCK_SECONDS / TICK_INTERVAL)
# 事件循环只要还能被调度，ticks 就应接近 EXPECTED_TICKS；这里取一个极宽松的
# 下限，避免慢速 CI 上偶发失败。
MIN_TICKS = 10


class _BlockingAmapService:
    """同步 sleep 的假服务，模拟 MCP 往返对调用线程的阻塞。"""

    def __init__(self) -> None:
        self.mcp_tool = types.SimpleNamespace(
            _available_tools=[{"name": "maps_text_search"}]
        )

    def _block(self) -> None:
        time.sleep(BLOCK_SECONDS)

    def search_poi(self, *args, **kwargs):
        self._block()
        return []

    def get_weather(self, *args, **kwargs):
        self._block()
        return []

    def plan_route(self, *args, **kwargs):
        self._block()
        return None

    def get_poi_detail(self, *args, **kwargs):
        self._block()
        return None


def _blocking_factory(service: _BlockingAmapService):
    """模拟 get_amap_service() 首次构造 MCPTool 时的阻塞。"""

    def factory():
        time.sleep(BLOCK_SECONDS)
        return service

    return factory


async def _ticks_during(coro) -> int:
    """统计 coro 执行期间事件循环还能调度多少次 ticker。"""
    ticks = 0

    async def ticker() -> None:
        nonlocal ticks
        while True:
            ticks += 1
            await asyncio.sleep(TICK_INTERVAL)

    task = asyncio.create_task(ticker())
    try:
        await coro
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
    return ticks


class _LoopStarvationAssertions(unittest.TestCase):
    def assert_loop_not_starved(self, coro, label: str) -> None:
        ticks = asyncio.run(_ticks_during(coro))
        self.assertGreaterEqual(
            ticks,
            MIN_TICKS,
            f"{label} 执行期间事件循环被阻塞：ticker 只运行了 {ticks} 次"
            f"（预期约 {EXPECTED_TICKS} 次）。该路由把同步的阻塞调用留在了"
            f"事件循环线程上，会冻结整个 worker。",
        )


class ServiceMethodDoesNotBlockTheLoopTests(_LoopStarvationAssertions):
    """每次请求都会发生的阻塞：同步的 AmapService 方法调用。"""

    def setUp(self) -> None:
        service = _BlockingAmapService()
        for module in (map_routes, poi_routes):
            patcher = mock.patch.object(module, "get_amap_service", return_value=service)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_map_poi_route_does_not_block_the_loop(self) -> None:
        self.assert_loop_not_starved(
            map_routes.search_poi(keywords="故宫", city="北京"),
            "GET /api/map/poi",
        )

    def test_map_weather_route_does_not_block_the_loop(self) -> None:
        self.assert_loop_not_starved(
            map_routes.get_weather(city="北京"),
            "GET /api/map/weather",
        )

    def test_map_route_route_does_not_block_the_loop(self) -> None:
        request = RouteRequest(
            origin_address="北京市朝阳区阜通东大街6号",
            destination_address="北京市海淀区上地十街10号",
        )
        self.assert_loop_not_starved(
            map_routes.plan_route(request),
            "POST /api/map/route",
        )

    def test_poi_detail_route_does_not_block_the_loop(self) -> None:
        self.assert_loop_not_starved(
            poi_routes.get_poi_detail(poi_id="B000A8UIN8"),
            "GET /api/poi/detail/{poi_id}",
        )

    def test_poi_search_route_does_not_block_the_loop(self) -> None:
        self.assert_loop_not_starved(
            poi_routes.search_poi(keywords="故宫", city="北京"),
            "GET /api/poi/search",
        )


class ServiceCreationDoesNotBlockTheLoopTests(_LoopStarvationAssertions):
    """每个进程一次的阻塞：get_amap_service() 首次构造 MCPTool 并做服务发现。"""

    def setUp(self) -> None:
        service = _BlockingAmapService()
        for module in (map_routes, poi_routes):
            patcher = mock.patch.object(
                module, "get_amap_service", new=_blocking_factory(service)
            )
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_map_poi_route_does_not_block_on_service_creation(self) -> None:
        self.assert_loop_not_starved(
            map_routes.search_poi(keywords="故宫", city="北京"),
            "GET /api/map/poi 的服务实例构造",
        )

    def test_map_weather_route_does_not_block_on_service_creation(self) -> None:
        self.assert_loop_not_starved(
            map_routes.get_weather(city="北京"),
            "GET /api/map/weather 的服务实例构造",
        )

    def test_poi_search_route_does_not_block_on_service_creation(self) -> None:
        self.assert_loop_not_starved(
            poi_routes.search_poi(keywords="故宫", city="北京"),
            "GET /api/poi/search 的服务实例构造",
        )


class ServiceSingletonIsThreadSafeTests(unittest.TestCase):
    """把取实例挪进线程后，单例本身必须线程安全。

    改动前 get_amap_service() 在事件循环线程上被调用，事件循环天然把
    「检查 - 构造 - 赋值」串行化了。改成 asyncio.to_thread 之后，并发首次请求
    会同时进入该函数：若不加锁，多个线程都会看到 _amap_service is None 而各建
    一个 AmapService——而每次构造都包含一次 MCP 服务发现往返，多出来的实例
    随即被覆盖丢弃。
    """

    def test_concurrent_first_calls_create_exactly_one_instance(self) -> None:
        created = []

        class _SlowService:
            def __init__(self) -> None:
                # 放大构造窗口，使竞争在未加锁时能稳定复现
                time.sleep(0.05)
                created.append(self)

        workers = 8
        with mock.patch.object(amap_service, "AmapService", _SlowService), mock.patch.object(
            amap_service, "_amap_service", None
        ):
            with ThreadPoolExecutor(max_workers=workers) as pool:
                results = list(
                    pool.map(lambda _: amap_service.get_amap_service(), range(workers))
                )

        self.assertEqual(
            len(created),
            1,
            f"并发首次调用构造了 {len(created)} 个实例（应为 1）——单例存在竞态",
        )
        self.assertEqual(len({id(r) for r in results}), 1, "并发调用返回了不同实例")


if __name__ == "__main__":
    unittest.main()
