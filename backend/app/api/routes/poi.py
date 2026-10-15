"""POI相关API路由

注：`/poi/search` 与 `/poi/detail` 曾走 AmapService（MCP），但该服务的方法
只返回空列表（结果未解析），且前端地图/路线由前端 JS SDK 直接完成、
从不调用这两个接口，因此已随 AmapService 一并移除。
本模块现只保留真正在用的景点图片接口。
"""

import asyncio
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from typing import Optional

router = APIRouter(prefix="/poi", tags=["POI"])


@router.get(
    "/image",
    summary="代理获取小红书图片",
    description="按景点名从缓存取图（miss 自动重搜新直链并立即下载），或代理白名单内的小红书稳定直链，规避 CDN 防盗链与时效签名（issue #28）"
)
async def proxy_attraction_image(name: Optional[str] = None, url: Optional[str] = None):
    """
    代理小红书图片，二选一传参：

    - name: 景点名。优先读关键词磁盘缓存；miss 时自动重搜新直链并立即下载
      （搜索返回的直链约 1 分钟即失效，浏览器直接引用必然 403）。
    - url: 小红书稳定格式图片直链（仅限 *.xiaohongshu.com / *.xhscdn.com），
      用于代理行程数据中内嵌的直链。
    """
    from fastapi.responses import Response
    from ...services.xhs_service import (
        XHSImageProxyError,
        fetch_xhs_image_bytes,
        get_photo_bytes_from_xhs,
    )

    if name:
        result = await get_photo_bytes_from_xhs(f"{name} 风景")
        if result is None:
            raise HTTPException(status_code=404, detail=f"未能获取 {name} 的景点图片")
        data, content_type = result
        return Response(
            content=data,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=86400"},
        )

    if url:
        try:
            data, content_type = fetch_xhs_image_bytes(url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except XHSImageProxyError as e:
            print(f"❌ 图片代理失败: {e}")
            raise HTTPException(status_code=502, detail=str(e))
        except Exception as e:
            print(f"❌ 图片代理异常: {e}")
            raise HTTPException(status_code=502, detail=f"图片代理请求失败: {e}")
        return Response(
            content=data,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=86400"},
        )

    raise HTTPException(status_code=400, detail="必须提供 name 或 url 查询参数")


@router.get(
    "/photo",
    summary="获取景点图片",
    description="优先返回高德官方图库直链；仅当 ENABLE_XHS 开启时才用小红书兜底"
)
async def get_attraction_photo(name: str, city: Optional[str] = None):
    """
    获取景点图片地址。

    返回的 `photo_url` 是**可直接用于 <img src> 的地址**：
    - 高德：官方图库绝对直链（稳定、不校验 Referer、无时效签名）
    - 小红书兜底：后端代理的相对路径，由前端拼上 API base

    Args:
        name: 景点名称
        city: 所在城市（建议传，能显著提高高德搜索的准确度）

    Returns:
        图片URL 与来源标识
    """
    from ...config import get_settings
    from ...services.amap_rest_service import get_poi_photo_url

    try:
        # httpx.get 是阻塞调用：必须放到线程里，否则会冻结整个事件循环
        photo_url = await asyncio.to_thread(get_poi_photo_url, name, city or "")
        source = "amap" if photo_url else ""

        # 小红书只在显式开启时作为兜底；它依赖登录 Cookie 与混淆 JS 签名，
        # 稳定性不如官方 API，因此默认不参与。
        if not photo_url and get_settings().enable_xhs:
            from ...services.xhs_service import get_photo_from_xhs

            # 加“风景”前缀是为了避开同名歌曲、小说、人名等干扰
            xhs_url = await get_photo_from_xhs(f"{name} 风景")
            if xhs_url:
                # 小红书直链带约 1 分钟时效签名，不能直接给前端，
                # 必须走后端按名字代理（缓存 miss 时会自动重搜重取）
                photo_url = f"/api/poi/image?name={quote(name)}"
                source = "xhs"

        if not photo_url:
            # 兜底：交由前端展示默认占位图
            print(f"⚠️ 未找到「{name}」的景点图片 (city={city or '-'})")

        return {
            "success": True,
            "message": "获取图片成功" if photo_url else "未找到图片",
            "data": {
                "name": name,
                "photo_url": photo_url,
                "source": source,
            }
        }

    except Exception as e:
        print(f"❌ 获取景点图片失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取景点图片失败: {str(e)}"
        )

