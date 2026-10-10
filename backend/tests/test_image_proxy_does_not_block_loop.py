"""回归测试：``/api/poi/image?url=`` 代理不得在事件循环上同步下载图片。

背景
----
``backend/app/api/routes/poi.py::proxy_attraction_image`` 是 ``async def``，但
``url`` 分支直接调用了**同步**的 ``xhs_service.fetch_xhs_image_bytes()``：

* 先读磁盘图片缓存（``_read_image_cache``，同步文件 I/O）；
* 缓存未命中时用 ``httpx.get`` **同步**下载图片，超时上限 15 秒。

整段下载都发生在 uvicorn worker 的事件循环线程上，因此任何一个
``/api/poi/image?url=...`` 请求都会把该 worker 冻结数百毫秒到十几秒。冻结期间
``/api/trip/status`` 轮询、``/api/trip/ws/{task_id}`` 的进度推送、以及其它用户的
请求全部停摆。行程结果页会为每条内嵌的小红书直链并发请求该代理，因此这不是
边缘场景。

同文件的 ``name`` 分支已经用 ``await asyncio.to_thread(get_photo_bytes_from_xhs, ...)``
规避（``get_photo_bytes_from_xhs`` 内部再 ``asyncio.to_thread``），``url`` 分支
漏掉了同样的处理。

用例做法与 ``test_map_routes_do_not_block_loop.py`` 相同：用「同步 sleep」的假
``fetch_xhs_image_bytes`` 模拟上述阻塞，同时在旁边跑一个每 5ms 递增一次的
ticker。若阻塞留在事件循环线程上，ticker 会被饿死（约 0 次）；反之会跑满约
50 次。完全离线：不访问网络、不需要 Cookie 或 API Key，也不启动子进程。
"""

import asyncio
import contextlib
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from app.api.routes import poi as poi_routes
from app.services import xhs_service

# 假阻塞的时长，以及 ticker 的间隔
BLOCK_SECONDS = 0.25
TICK_INTERVAL = 0.005
EXPECTED_TICKS = int(BLOCK_SECONDS / TICK_INTERVAL)
# 事件循环只要还能被调度，ticks 就应接近 EXPECTED_TICKS；这里取一个极宽松的
# 下限，避免慢速 CI 上偶发失败。
MIN_TICKS = 10

_STABLE_IMAGE_URL = "https://sns-img-qc.xhscdn.com/notes_pre_post/example.jpg"


def _blocking_fetch(*_args, **_kwargs):
    """同步 sleep 的假 ``fetch_xhs_image_bytes``，模拟直链下载阻塞调用线程。"""
    time.sleep(BLOCK_SECONDS)
    return b"fake-image-bytes", "image/jpeg"


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


class ImageProxyDoesNotBlockTheLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        patcher = mock.patch.object(
            xhs_service, "fetch_xhs_image_bytes", new=_blocking_fetch
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_url_branch_does_not_block_the_loop(self) -> None:
        ticks = asyncio.run(
            _ticks_during(poi_routes.proxy_attraction_image(url=_STABLE_IMAGE_URL))
        )
        self.assertGreaterEqual(
            ticks,
            MIN_TICKS,
            f"/api/poi/image?url= 执行期间事件循环被阻塞：ticker 只运行了 {ticks} 次"
            f"（预期约 {EXPECTED_TICKS} 次）。该路由把同步的图片下载留在了事件循环"
            f"线程上，会冻结整个 worker。",
        )


if __name__ == "__main__":
    unittest.main()
