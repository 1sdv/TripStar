"""用户偏好记忆管理 API"""
import os

from fastapi import APIRouter, Query

from ...memory import MemoryManager, logger

router = APIRouter(prefix="/memory", tags=["用户偏好记忆"])

ENABLE_MEMORY = os.getenv("ENABLE_USER_MEMORY", "false").lower() == "true"


@router.get("/list", summary="查询用户有效记忆")
async def list_user_memory(user_id: str = Query(..., description="前端生成的唯一用户ID")):
    """返回该用户当前所有有效记忆（已执行遗忘衰减与 TOP-K 过滤）"""
    if not ENABLE_MEMORY:
        return {"code": 400, "msg": "记忆模块未开启", "data": []}
    mm = MemoryManager.get_instance()
    memory_list = await mm.recall_user_memory(user_id)
    return {
        "code": 200,
        "msg": "success",
        "data": [item.to_dict() for item in memory_list],
    }


@router.post("/add-explicit", summary="手动添加用户偏好")
async def add_manual_preference(
    user_id: str = Query(...),
    content: str = Query(..., description="偏好内容"),
):
    """用户手动添加偏好（explicit，初始权重 8.5，高于自动提取）"""
    if not ENABLE_MEMORY:
        return {"code": 400, "msg": "记忆模块未开启"}
    mm = MemoryManager.get_instance()
    await mm.add_memory(
        user_id=user_id, content=content, source="explicit", init_weight=8.5
    )
    return {"code": 200, "msg": "手动偏好添加完成"}


@router.delete("/item", summary="删除单条记忆")
async def delete_single_memory(
    user_id: str = Query(...),
    memory_id: str = Query(...),
):
    if not ENABLE_MEMORY:
        return {"code": 400, "msg": "记忆模块未开启"}
    mm = MemoryManager.get_instance()
    ok = await mm.store.delete(user_id, memory_id)
    if ok:
        logger.info(f"[MemoryDelete] user={user_id}, memory_id={memory_id}")
        return {"code": 200, "msg": "删除成功"}
    return {"code": 404, "msg": "未找到该记忆条目"}


@router.delete("/clear", summary="清空用户全部记忆")
async def clear_user_memory(user_id: str = Query(...)):
    if not ENABLE_MEMORY:
        return {"code": 400, "msg": "记忆模块未开启"}
    mm = MemoryManager.get_instance()
    await mm.store.clear(user_id)
    logger.info(f"[MemoryClear] user={user_id} all memory removed")
    return {"code": 200, "msg": "已清空该用户全部记忆"}
