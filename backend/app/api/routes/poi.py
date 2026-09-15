"""POI相关API路由"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from ...services.amap_service import get_amap_service

router = APIRouter(prefix="/poi", tags=["POI"])


class POIDetailResponse(BaseModel):
    """POI详情响应"""
    success: bool
    message: str
    data: Optional[dict] = None


@router.get(
    "/detail/{poi_id}",
    response_model=POIDetailResponse,
    summary="获取POI详情",
    description="根据POI ID获取详细信息,包括图片"
)
async def get_poi_detail(poi_id: str):
    """
    获取POI详情
    
    Args:
        poi_id: POI ID
        
    Returns:
        POI详情响应
    """
    try:
        amap_service = get_amap_service()
        
        # 调用高德地图POI详情API
        result = amap_service.get_poi_detail(poi_id)
        
        return POIDetailResponse(
            success=True,
            message="获取POI详情成功",
            data=result
        )
        
    except Exception as e:
        print(f"❌ 获取POI详情失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取POI详情失败: {str(e)}"
        )


@router.get(
    "/search",
    summary="搜索POI",
    description="根据关键词搜索POI"
)
async def search_poi(keywords: str, city: str = "北京"):
    """
    搜索POI

    Args:
        keywords: 搜索关键词
        city: 城市名称

    Returns:
        搜索结果
    """
    try:
        amap_service = get_amap_service()
        result = amap_service.search_poi(keywords, city)

        return {
            "success": True,
            "message": "搜索成功",
            "data": result
        }

    except Exception as e:
        print(f"❌ 搜索POI失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"搜索POI失败: {str(e)}"
        )


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
    description="根据景点名称从小红书获取图片"
)
async def get_attraction_photo(name: str, city: Optional[str] = None):
    """
    获取景点图片

    Args:
        name: 景点名称
        city: 所在城市

    Returns:
        图片URL
    """
    try:
        from ...services.xhs_service import get_photo_from_xhs
        
        # 为了避免同名的流行歌曲（如许嵩的《断桥残雪》）、小说或人名干扰
        # 强制带上前缀“景点”，能够绝对限定搜索范围在旅游打卡贴内
        query_kw = f"{name} 风景"
        photo_url = await get_photo_from_xhs(query_kw)

        if not photo_url:
            # 兜底：交由前端展示默认占位图
            print(f"⚠️ 无法为 {name} 找到对应的小红书景点图片，返回空")
            photo_url = ""
            
        return {
            "success": True,
            "message": "获取图片成功",
            "data": {
                "name": name,
                "photo_url": photo_url
            }
        }

    except Exception as e:
        print(f"❌ 获取景点图片失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取景点图片失败: {str(e)}"
        )

