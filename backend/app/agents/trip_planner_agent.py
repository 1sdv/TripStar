"""多智能体旅行规划系统"""

import json
import asyncio
import os
from typing import Dict, Any, List, Callable, Awaitable, Optional
from hello_agents import SimpleAgent
from hello_agents.tools import MCPTool
from ..services.llm_service import get_llm
from ..services.metrics import stage_timer, record_retrieval
from ..services.provider_service import get_hotels, get_weather, probe_mcp_tools
from ..models.schemas import TripRequest, TripPlan, DayPlan, Attraction, Meal, WeatherInfo, Location, Hotel
from ..config import get_settings

# ============ Agent提示词 (动态模版化，支持 amap / google 双供应商) ============


# 每个城市的采集阶段（顺序即进度顺序）。
# 进度由「阶段在列表里的位置」推导，而不是写死 `progress_step * 2` 这类步长乘法——
# 那样一旦增删阶段，所有偏移都得手改，极易错位。
CITY_COLLECTION_STAGES = ("attraction_search", "rag_search", "weather_search", "hotel_search")
# 采集阶段占用的进度区间（%），其后留给 planning
_COLLECTION_PROGRESS_START = 10
_COLLECTION_PROGRESS_END = 85


def _stage_progress(stage: str, city_index: int, total_cities: int) -> int:
    """计算「第 city_index 个城市的第 stage 阶段」对应的进度百分比。"""
    try:
        stage_index = CITY_COLLECTION_STAGES.index(stage)
    except ValueError:
        stage_index = 0
    per_city = (_COLLECTION_PROGRESS_END - _COLLECTION_PROGRESS_START) / max(1, total_cities)
    per_stage = per_city / len(CITY_COLLECTION_STAGES)
    value = _COLLECTION_PROGRESS_START + city_index * per_city + stage_index * per_stage
    return int(round(value))


def _build_weather_agent_prompt(tool_prefix: str) -> str:
    """构建天气查询 Agent 的系统提示词。

    Args:
        tool_prefix: "amap" 或 "google"
    """
    tool_name = f"{tool_prefix}_maps_weather"
    return f"""你是天气查询专家。你的任务是查询指定城市的天气信息。

**重要提示:**
1. 你必须使用工具来查询天气!不要自己编造天气信息!
2. 系统为你绑定的真实工具名称叫做 `{tool_name}`，你**只能而且必须**原样输出这个名字。

**工具调用格式:**
使用天气工具时,必须严格按照以下单行格式输出，**不要带任何多余的字符或JSON block**:
`[TOOL_CALL:{tool_name}:city=城市名]`

**示例:**
用户: "查询北京天气"
你的回复: [TOOL_CALL:{tool_name}:city=北京]

用户: "上海的天气怎么样"
你的回复: [TOOL_CALL:{tool_name}:city=上海]

**注意:**
1. 必须使用工具,不要直接回答
2. 格式必须完全正确,包括方括号和冒号
3. 必须输出 `{tool_name}` 作为工具名。
"""


def _build_hotel_agent_prompt(tool_prefix: str) -> str:
    """构建酒店推荐 Agent 的系统提示词。"""
    tool_name = f"{tool_prefix}_maps_text_search"
    return f"""你是酒店推荐专家。你的任务是根据城市和景点位置推荐合适的酒店。

**重要提示:**
1. 你必须使用工具来搜索酒店!不要自己编造酒店信息!
2. 系统为你绑定的真实工具名称叫做 `{tool_name}`，你**只能而且必须**原样输出这个名字。

**工具调用格式:**
使用text_search工具搜索酒店时,必须严格按照以下单行格式输出，**不要带任何多余的字符或JSON block**:
`[TOOL_CALL:{tool_name}:keywords=酒店,city=城市名]`

**示例:**
用户: "搜索北京的酒店"
你的回复: [TOOL_CALL:{tool_name}:keywords=酒店,city=北京]

**注意:**
1. 必须使用工具,不要直接回答
2. 格式必须完全正确,包括方括号和冒号
3. 关键词使用"酒店"或"宾馆"
4. 必须输出 `{tool_name}` 作为工具名。
"""


# 保留原有静态常量作为向后兼容 alias（部分外部代码可能引用到）
ATTRACTION_AGENT_PROMPT = ""  # 已弃用，景点改走小红书
WEATHER_AGENT_PROMPT = _build_weather_agent_prompt("amap")
HOTEL_AGENT_PROMPT = _build_hotel_agent_prompt("amap")

PLANNER_AGENT_PROMPT = """你是行程规划专家。你的任务是根据景点信息和天气信息,生成详细的旅行计划。支持单城市和多城市行程。

请严格按照以下JSON格式返回旅行计划:
```json
{
  "city": "首个城市名称(兼容字段)",
  "cities": ["城市1", "城市2"],
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "days": [
    {
      "date": "YYYY-MM-DD",
      "day_index": 0,
      "city": "当天所在城市",
      "is_transfer_day": false,
      "transfer_info": "",
      "description": "第1天行程概述",
      "transportation": "交通方式",
      "accommodation": "住宿类型",
      "hotel": {
        "name": "酒店名称",
        "address": "酒店地址",
        "location": {"longitude": 116.397128, "latitude": 39.916527},
        "price_range": "300-500元",
        "rating": "4.5",
        "distance": "距离景点2公里",
        "type": "经济型酒店",
        "estimated_cost": 400
      },
      "attractions": [
        {
          "name": "景点名称",
          "address": "详细地址",
          "location": {"longitude": 116.397128, "latitude": 39.916527},
          "visit_duration": 120,
          "description": "景点详细描述",
          "category": "景点类别",
          "ticket_price": 60,
          "reservation_required": false,
          "reservation_tips": ""
        }
      ],
      "meals": [
        {"type": "breakfast", "name": "早餐推荐", "description": "早餐描述", "estimated_cost": 30},
        {"type": "lunch", "name": "午餐推荐", "description": "午餐描述", "estimated_cost": 50},
        {"type": "dinner", "name": "晚餐推荐", "description": "晚餐描述", "estimated_cost": 80}
      ]
    }
  ],
  "weather_info": [
    {
      "date": "YYYY-MM-DD",
      "city": "当天所在城市",
      "day_weather": "晴",
      "night_weather": "多云",
      "day_temp": 25,
      "night_temp": 15,
      "wind_direction": "南风",
      "wind_power": "1-3级"
    }
  ],
  "overall_suggestions": "总体建议",
  "budget": {
    "total_attractions": 180,
    "total_hotels": 1200,
    "total_meals": 480,
    "total_transportation": 200,
    "total_inter_city_transport": 0,
    "total": 2060
  }
}
```

**⚠️ JSON 格式关键约束（违反将导致系统崩溃）：**
- budget 中所有费用字段（total_attractions、total_hotels、total_meals、total_transportation、total_inter_city_transport、total）必须是**纯数字**，绝对禁止出现算术表达式！
  - ✅ 正确: "total_attractions": 324
  - ❌ 错误: "total_attractions": 30+54+120+120=324
  - ❌ 错误: "total_attractions": "324元"
- ticket_price、estimated_cost 等所有价格字段也必须是纯数字，不带单位

**重要提示:**
1. weather_info数组必须包含每一天的天气信息，每条记录必须包含 city 字段标明该天所在城市
2. 温度必须是纯数字(不要带°C等单位)
3. 每天安排2-3个景点(城际移动日可减少为1-2个)
4. 考虑景点之间的距离和游览时间
5. 每天必须包含早中晚三餐
6. 提供实用的旅行建议
7. **必须包含预算信息**:
   - 景点门票价格(ticket_price)
   - 餐饮预估费用(estimated_cost)
   - 酒店预估费用(estimated_cost)
   - 预算汇总(budget)包含各项总费用
8. **预约信息透传**: 如果景点搜索数据中包含 reservation_required 和 reservation_tips 字段，请务必将它们完整保留在对应景点的JSON中。需要预约的景点请在 description 中也提醒游客提前预约
9. **景点图片**: 不需要在JSON中填写 image_url 字段，图片由前端根据景点名称自动从小红书获取。
10. **多城市行程要求**:
    - 每个 day 对象中必须包含 "city" 字段标明当天所在城市
    - 城市切换当天设置 "is_transfer_day": true，并在 "transfer_info" 中**仅给出交通方式建议和大致时长**（如"建议乘坐高铁，约2-3小时"），**禁止编造具体车次、班次号、出发时间、到达时间等不可验证的信息**
    - 城际移动日的景点数量可适当减少为1-2个
    - budget 中的 "total_inter_city_transport" 统计城际交通费用(单城市时为0)
    - "cities" 数组列出所有途经城市(单城市时只有一个元素)
"""


class MultiAgentTripPlanner:
    """多智能体旅行规划系统"""

    def __init__(self):
        """初始化多智能体系统"""
        print("🔄 开始初始化多智能体旅行规划系统...")

        try:
            settings = get_settings()
            self.llm = get_llm()

            # ---------- 判断地图供应商 ----------
            from ..services.map_dispatcher import get_map_provider
            self.map_provider = get_map_provider()
            print(f"  - 地图供应商: {self.map_provider.upper()}")

            if self.map_provider == "google":
                tool_prefix = "google"
                self._init_google_tools(settings)
            else:
                tool_prefix = "amap"
                self._init_amap_tools(settings)

            # ---------- 构建动态提示词 ----------
            weather_prompt = _build_weather_agent_prompt(tool_prefix)
            hotel_prompt = _build_hotel_agent_prompt(tool_prefix)

            # 取消高德景点 Agent,改用原生小红书服务
            # print("  - 创建景点搜索Agent...")

            # 创建天气查询Agent
            print("  - 创建天气查询Agent...")
            self.weather_agent = SimpleAgent(
                name="天气查询专家",
                llm=self.llm,
                system_prompt=weather_prompt
            )
            self.weather_agent.add_tool(self._active_tool)

            # 创建酒店推荐Agent
            print("  - 创建酒店推荐Agent...")
            self.hotel_agent = SimpleAgent(
                name="酒店推荐专家",
                llm=self.llm,
                system_prompt=hotel_prompt
            )
            self.hotel_agent.add_tool(self._active_tool)

            # 创建行程规划Agent(不需要工具)
            print("  - 创建行程规划Agent...")
            self.planner_agent = SimpleAgent(
                name="行程规划专家",
                llm=self.llm,
                system_prompt=PLANNER_AGENT_PROMPT
            )

            print(f"✅ 多智能体系统初始化成功 (供应商={self.map_provider})")
            print(f"   天气查询Agent: {len(self.weather_agent.list_tools())} 个工具")
            print(f"   酒店推荐Agent: {len(self.hotel_agent.list_tools())} 个工具")

            # 探测 MCP 工具是否真的展开注册。MCP 服务器不可用时工具发现会静默为空，
            # 此时直接走高德 REST，省掉「注定失败的 LLM 调用 + 错误文案回合」。
            self._mcp_ready = probe_mcp_tools(self.weather_agent) and probe_mcp_tools(self.hotel_agent)
            if self._mcp_ready:
                print("   MCP 工具已就绪（天气/酒店走 Agent 调用）")
            else:
                print("   ⚠️ MCP 工具未注册成功，天气/酒店将直接走高德 REST 兜底")

        except Exception as e:
            print(f"❌ 多智能体系统初始化失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    def _init_amap_tools(self, settings):
        """初始化高德地图 MCP 工具。"""
        print("  - 创建高德 MCP 工具...")
        self.amap_tool = MCPTool(
            name="amap",
            description="高德地图服务",
            server_command=["uvx", "amap-mcp-server"],
            env={"AMAP_MAPS_API_KEY": settings.vite_amap_web_key},
            auto_expand=True
        )
        self.amap_tool.expandable = True
        self._active_tool = self.amap_tool

    def _init_google_tools(self, settings):
        """初始化 Google Maps 本地适配器工具。"""
        print("  - 创建 Google Maps 本地适配器工具...")
        from ..services.google_map_service import GoogleMapService

        # 创建一个轻量级的本地工具适配器
        google_svc = GoogleMapService(api_key=settings.google_maps_api_key, proxy=settings.google_maps_proxy)

        class GoogleMapsNativeTool:
            """将 Google Maps API 封装为 hello_agents 可注册的工具。

            通过鸭子类型模拟 MCPTool 的接口（name, description, expandable,
            _available_tools, run），无需继承任何基类。

            注册后在 Agent 的可用工具列表中暴露为:
              - google_maps_text_search
              - google_maps_weather
              - google_maps_geo
            """

            def __init__(self):
                self.name = "google"
                self.description = "Google Maps 服务 (POI搜索/天气/地理编码)"
                self.expandable = True
                self._google_svc = google_svc
                # 模拟 MCP 子工具列表，使 hello_agents 能自动展开
                self._available_tools = [
                    {"name": "google_maps_text_search", "description": "Google POI文本搜索"},
                    {"name": "google_maps_weather", "description": "Google 天气查询"},
                    {"name": "google_maps_geo", "description": "Google 地理编码"},
                ]

            def get_expanded_tools(self):
                """返回展开的子工具列表，满足 hello_agents ToolRegistry 的接口要求。"""
                parent = self

                class _SubTool:
                    def __init__(self, name, description):
                        self.name = name
                        self.description = description
                        self.expandable = False

                    def run(self, input_data):
                        return parent.run(input_data)

                    def get_expanded_tools(self):
                        return [self]

                return [_SubTool(t["name"], t["description"]) for t in self._available_tools]

            def run(self, input_data):
                """分发 [TOOL_CALL:google_maps_*:...] 格式调用。"""
                import re as _re
                if isinstance(input_data, dict):
                    tool_name = input_data.get("tool_name", "")
                    arguments = input_data.get("arguments", {})
                elif isinstance(input_data, str):
                    # 解析 [TOOL_CALL:google_maps_xxx:key=val,...] 格式
                    match = _re.search(
                        r'\[TOOL_CALL:(\w+):(.*?)\]', input_data
                    )
                    if match:
                        tool_name = match.group(1)
                        args_str = match.group(2)
                        arguments = dict(
                            kv.split("=", 1)
                            for kv in args_str.split(",")
                            if "=" in kv
                        )
                    else:
                        return f"无法解析工具调用: {input_data}"
                else:
                    return f"不支持的输入类型: {type(input_data)}"

                return self._dispatch(tool_name, arguments)

            def _dispatch(self, tool_name: str, arguments: dict) -> str:
                import json as _json
                try:
                    if tool_name == "google_maps_text_search":
                        kw = arguments.get("keywords", "")
                        city = arguments.get("city", "")
                        results = self._google_svc.search_poi(kw, city)
                        return _json.dumps(
                            [r.model_dump() for r in results],
                            ensure_ascii=False,
                        )
                    elif tool_name == "google_maps_weather":
                        city = arguments.get("city", "")
                        results = self._google_svc.get_weather(city)
                        return _json.dumps(
                            [r.model_dump() for r in results],
                            ensure_ascii=False,
                        )
                    elif tool_name == "google_maps_geo":
                        address = arguments.get("address", "")
                        city = arguments.get("city", "")
                        loc = self._google_svc.geocode(address, city)
                        if loc:
                            return _json.dumps(loc.model_dump(), ensure_ascii=False)
                        return '{"error": "地理编码失败"}'
                    else:
                        return f'未知的 Google Maps 工具: {tool_name}'
                except Exception as e:
                    return f'Google Maps 工具调用失败: {e}'

        self._google_tool = GoogleMapsNativeTool()
        self._active_tool = self._google_tool

    async def _emit_progress(
        self,
        progress_callback: Optional[Callable[[str, str, int], Awaitable[None] | None]],
        stage: str,
        message: str,
        progress: int,
    ) -> None:
        """向上层回调任务进度（支持同步/异步回调）。"""
        if progress_callback is None:
            return
        result = progress_callback(stage, message, progress)
        if asyncio.iscoroutine(result):
            await result

    async def _retrieve_rag_notes(self, city: str, request: TripRequest) -> str:
        """检索城市游记知识库（RAG），返回可注入 Planner Prompt 的文本块。

        RAG 是增强项：未配置 embedding / 库为空 / 网络异常一律返回空字符串，
        由调用方按「无命中」处理，绝不阻断行程生成主流程。
        """
        try:
            from ..services.rag import rag_available, retrieve_notes_for_city

            available, reason = rag_available()
            if not available:
                print(f"  ℹ️ RAG 未启用: {reason}")
                return ""

            record_retrieval()
            return await asyncio.to_thread(
                retrieve_notes_for_city,
                city,
                request.preferences,
                request.free_text_input or "",
            )
        except Exception as e:
            print(f"  ⚠️ RAG 游记检索失败（已跳过，不影响主流程）: {type(e).__name__}: {e}")
            return ""

    async def plan_trip(
        self,
        request: TripRequest,
        progress_callback: Optional[Callable[[str, str, int], Awaitable[None] | None]] = None
    ) -> TripPlan:
        """
        使用多智能体协作生成旅行计划（多城市支持版）

        按 request.cities 逐城市搜集景点/天气/酒店信息，
        然后统一交给 LLM 生成跨城行程。
        单城市场景下 cities 只有一个元素，行为与原版一致。

        Args:
            request: 旅行请求

        Returns:
            旅行计划
        """
        try:
            cities = request.cities  # List[CityStay] — 已由 normalize_cities 保证非空
            total_cities = len(cities)
            city_names = [cs.city for cs in cities]

            print(f"\n{'='*60}")
            print(f"🚀 开始多智能体协作规划旅行...")
            print(f"途经城市: {' → '.join(city_names)}")
            print(f"日期: {request.start_date} 至 {request.end_date}")
            print(f"天数: {request.travel_days}天")
            print(f"偏好: {', '.join(request.preferences) if request.preferences else '无'}")
            print(f"{'='*60}\n")

            from ..services.attraction_service import search_attractions
            keywords = request.preferences[0] if request.preferences else "景点"
            _lang = (getattr(request, 'language', 'zh') or 'zh').strip().lower().split('-')[0]
            _lang_hint = "" if _lang == "zh" else f" Please respond in {'English' if _lang == 'en' else _lang}."

            # ========== 按城市逐一搜集信息 ==========
            all_attractions: Dict[str, str] = {}
            all_attraction_sources: Dict[str, str] = {}
            all_rag_notes: Dict[str, str] = {}
            all_weather: Dict[str, str] = {}
            all_hotels: Dict[str, str] = {}
            all_weather_sources: Dict[str, str] = {}
            all_hotel_sources: Dict[str, str] = {}

            for idx, city_stay in enumerate(cities):
                city = city_stay.city
                city_label = f" ({idx+1}/{total_cities})" if total_cities > 1 else ""

                # [1] 景点搜索（小红书 → 本地知识库 → 通用常识 三级降级，永不抛异常）
                print(f"  [{idx+1}/{total_cities}] 正在搜索 {city} 的景点...")
                await self._emit_progress(
                    progress_callback, "attraction_search",
                    f"正在搜索 {city} 的景点...{city_label}",
                    _stage_progress("attraction_search", idx, total_cities)
                )
                with stage_timer("attraction_search"):
                    attraction_response, attraction_source = await asyncio.to_thread(
                        search_attractions, city, keywords, _lang
                    )
                all_attractions[city] = attraction_response
                all_attraction_sources[city] = attraction_source
                print(f"📍 {city} 景点数据来源={attraction_source}: {attraction_response[:150]}...")

                # 数据源降级时补一条进度提示，避免前端看起来「卡住不动」
                if attraction_source != "小红书":
                    await self._emit_progress(
                        progress_callback, "attraction_search",
                        f"{city} 小红书不可用，已改用「{attraction_source}」...{city_label}",
                        _stage_progress("attraction_search", idx, total_cities) + 1
                    )

                # [2] RAG 游记检索（增强项：失败只记日志，不影响主流程）
                await self._emit_progress(
                    progress_callback, "rag_search",
                    f"正在检索 {city} 的游记攻略...{city_label}",
                    _stage_progress("rag_search", idx, total_cities)
                )
                note_block = await self._retrieve_rag_notes(city, request)
                if note_block:
                    all_rag_notes[city] = note_block
                    print(f"📚 {city} RAG 游记检索命中，已注入规划上下文")
                else:
                    all_rag_notes[city] = ""
                    print(f"📚 {city} RAG 无命中，跳过注入")
                # [3] 天气查询（Agent/MCP 优先 → 高德 REST 兜底）
                print(f"  [{idx+1}/{total_cities}] 正在查询 {city} 的天气...")
                await self._emit_progress(
                    progress_callback, "weather_search",
                    f"正在查询 {city} 的天气...{city_label}",
                    _stage_progress("weather_search", idx, total_cities)
                )
                with stage_timer("weather_search"):
                    weather_response, weather_source = await get_weather(
                        city, self.weather_agent, self._mcp_ready,
                        start_date=request.start_date, end_date=request.end_date,
                    )
                all_weather[city] = weather_response
                all_weather_sources[city] = weather_source
                print(f"🌤️  {city} 天气数据来源={weather_source}: {weather_response[:150]}...")

                # [4] 酒店搜索（Agent/MCP 优先 → 高德 REST 兜底）
                print(f"  [{idx+1}/{total_cities}] 正在搜索 {city} 的酒店...")
                await self._emit_progress(
                    progress_callback, "hotel_search",
                    f"正在搜索 {city} 的酒店...{city_label}",
                    _stage_progress("hotel_search", idx, total_cities)
                )
                with stage_timer("hotel_search"):
                    hotel_response, hotel_source = await get_hotels(
                        city, request.accommodation, self.hotel_agent, self._mcp_ready
                    )
                all_hotels[city] = hotel_response
                all_hotel_sources[city] = hotel_source
                print(f"🏨 {city} 酒店数据来源={hotel_source}: {hotel_response[:150]}...")

            print(f"\n✅ 全部 {total_cities} 个城市基础信息搜集完成\n")

            # ========== 统一规划阶段 ==========
            planning_label = "正在生成多城市行程计划..." if total_cities > 1 else "正在生成旅行计划..."
            print(f"📋 步骤4: {planning_label}")
            await self._emit_progress(progress_callback, "planning", planning_label, _COLLECTION_PROGRESS_END + 5)

            # 加载用户历史偏好记忆（若开启）
            memory_snippet = ""
            if os.getenv("ENABLE_USER_MEMORY", "false").lower() == "true":
                user_id = (getattr(request, "user_id", "") or "").strip()
                if user_id:
                    try:
                        from ..memory import MemoryManager
                        memory_snippet = await MemoryManager.get_instance().build_prompt_snippet(user_id)
                    except Exception as _mem_err:
                        print(f"⚠️  加载用户记忆失败: {_mem_err}")
                        memory_snippet = ""

            with stage_timer("planning"):
                planner_response = await self._run_planner_with_retry(
                    request,
                    all_attractions,
                    all_weather,
                    all_hotels,
                    memory_snippet,
                    all_rag_notes,
                    all_attraction_sources,
                    all_weather_sources,
                    all_hotel_sources,
                )
            print(f"行程规划结果: {planner_response[:300]}...\n")

            # 解析最终计划
            trip_plan = self._parse_response(planner_response, request)

            # 补全 cities 字段（LLM 可能遗漏）
            if not trip_plan.cities:
                trip_plan.cities = city_names
            # 补全每日 city 字段（单城市场景 LLM 可能遗漏）
            if total_cities == 1:
                for day in trip_plan.days:
                    if not day.city:
                        day.city = city_names[0]

            print(f"{'='*60}")
            print(f"✅ 旅行计划生成完成!")
            print(f"{'='*60}\n")

            return trip_plan

        except Exception as e:
            print(f"❌ 生成旅行计划失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"旅行计划生成失败: {str(e)}") from e
    
    def _build_attraction_query(self, request: TripRequest) -> str:
        """构建景点搜索查询 - 直接包含工具调用"""
        keywords = []
        if request.preferences:
            # 只取第一个偏好作为关键词
            keywords = request.preferences[0]
        else:
            keywords = "景点"

        # 直接返回工具调用格式，使用正确的工具名和严格的格式
        query = f"请使用amap_maps_text_search工具搜索{request.city}的{keywords}相关的景点。\n非常重要：你必须直接输出 `[TOOL_CALL:amap_maps_text_search:keywords={keywords},city={request.city}]`，不要附带任何多余的 JSON 或文字说明！"
        return query


    async def _run_planner_with_retry(
        self,
        request: TripRequest,
        attractions: Dict[str, str],
        weather: Dict[str, str],
        hotels: Dict[str, str],
        memory_snippet: str = "",
        rag_notes: Optional[Dict[str, str]] = None,
        attraction_sources: Optional[Dict[str, str]] = None,
        weather_sources: Optional[Dict[str, str]] = None,
        hotel_sources: Optional[Dict[str, str]] = None,
    ) -> str:
        """规划阶段使用更长超时，并在超时后重试一次。

        Args:
            attractions: {city_name: 景点搜索结果文本}
            weather: {city_name: 天气查询结果文本}
            hotels: {city_name: 酒店搜索结果文本}
            memory_snippet: 用户历史偏好文本，注入规划 Prompt
            rag_notes: {city_name: 游记知识库检索结果文本}，RAG 增强上下文
            attraction_sources: {city_name: 景点数据来源标签}
            weather_sources: {city_name: 天气数据来源标签}
            hotel_sources: {city_name: 酒店数据来源标签}
        """
        timeout = int(os.getenv("TRIP_PLANNER_TIMEOUT", "180"))
        planner_query = self._build_planner_query(
            request, attractions, weather, hotels, memory_snippet, rag_notes,
            attraction_sources, weather_sources, hotel_sources,
        )

        try:
            return await asyncio.to_thread(
                self.planner_agent.run,
                planner_query,
                timeout=timeout,
                temperature=0.2,
            )
        except Exception as exc:
            err_text = str(exc).lower()
            if "timeout" not in err_text and "timed out" not in err_text:
                raise

            print("⚠️  首次行程规划超时，正在重试一次...")
            planner_query += (
                "\n\n**补充要求:** 如果部分辅助信息不足，请使用保守、常见、可执行的建议补齐，"
                "但必须输出完整合法的 JSON，不要输出解释性文字。"
            )
            return await asyncio.to_thread(
                self.planner_agent.run,
                planner_query,
                timeout=timeout,
                temperature=0.2,
            )

    def _build_planner_query(
        self,
        request: TripRequest,
        attractions: Dict[str, str],
        weather: Dict[str, str],
        hotels: Dict[str, str],
        memory_snippet: str = "",
        rag_notes: Optional[Dict[str, str]] = None,
        attraction_sources: Optional[Dict[str, str]] = None,
        weather_sources: Optional[Dict[str, str]] = None,
        hotel_sources: Optional[Dict[str, str]] = None,
    ) -> str:
        """构建行程规划查询（支持多城市）

        Args:
            attractions: {city_name: 景点搜索结果文本}
            weather: {city_name: 天气查询结果文本}
            hotels: {city_name: 酒店搜索结果文本}
            memory_snippet: 用户历史偏好文本
            rag_notes: {city_name: 游记知识库检索结果文本}
            attraction_sources: {city_name: 景点数据来源标签}
            weather_sources: {city_name: 天气数据来源标签}
            hotel_sources: {city_name: 酒店数据来源标签}
        """
        rag_notes = rag_notes or {}
        attraction_sources = attraction_sources or {}
        weather_sources = weather_sources or {}
        hotel_sources = hotel_sources or {}
        cities = request.cities
        total_cities = len(cities)
        is_multi_city = total_cities > 1

        # 构建城市停留计划描述
        if is_multi_city:
            cities_info_lines = []
            day_offset = 0
            for cs in cities:
                cities_info_lines.append(
                    f"- {cs.city}: 停留 {cs.days} 天 (第{day_offset+1}天 ~ 第{day_offset+cs.days}天)"
                )
                day_offset += cs.days
            cities_desc = "\n".join(cities_info_lines)
            title = f"跨城市旅行计划（{' → '.join(cs.city for cs in cities)}）"
        else:
            cities_desc = f"- {cities[0].city}: {cities[0].days} 天"
            title = f"{cities[0].city}的{request.travel_days}天旅行计划"

        query = f"""请根据以下信息生成{title}:

**基本信息:**
- 途经城市及天数分配:
{cities_desc}
- 总天数: {request.travel_days}天
- 日期: {request.start_date} 至 {request.end_date}
- 交通方式: {request.transportation}
- 住宿: {request.accommodation}
- 偏好: {', '.join(request.preferences) if request.preferences else '无'}
"""
        if memory_snippet:
            query += f"""
{memory_snippet}
请在规划时充分参考以上用户历史偏好，使其在景点选择、餐饮、住宿、行程节奏中体现。
"""
        # 为每个城市附上搜集到的信息
        for cs in cities:
            city = cs.city
            rag_block = (rag_notes.get(city) or "").strip()
            _src = attraction_sources.get(city, "")
            # 景点数据的来源标注：降级时提示模型保守处理
            if _src == "小红书":
                attraction_line = f"**{city} 景点信息（来源：小红书实时搜索）:**" if is_multi_city else "**景点信息（来源：小红书实时搜索）:**"
            elif _src:
                attraction_line = (
                    f"**{city} 景点信息（来源：{_src}，非实时数据）:**"
                    if is_multi_city
                    else f"**景点信息（来源：{_src}，非实时数据）:**"
                )
            else:
                attraction_line = f"**{city} 景点信息:**" if is_multi_city else "**景点信息:**"

            if is_multi_city:
                query += f"""
--- {city} ({cs.days}天) ---
{attraction_line}
{attractions.get(city, '无')}
"""
                if rag_block:
                    query += f"""
**{city} 游记攻略检索（事实依据）:**
{rag_block}
"""
                query += f"""
**{city} 天气信息（来源：{weather_sources.get(city, '未知')}）:**
{weather.get(city, '无')}
**{city} 酒店信息（来源：{hotel_sources.get(city, '未知')}）:**
{hotels.get(city, '无')}
"""
            else:
                query += f"""
{attraction_line}
{attractions.get(city, '无')}
"""
                if rag_block:
                    query += f"""
**游记攻略检索（事实依据）:**
{rag_block}
"""
                query += f"""
**天气信息（来源：{weather_sources.get(city, '未知')}）:**
{weather.get(city, '无')}

**酒店信息（来源：{hotel_sources.get(city, '未知')}）:**
{hotels.get(city, '无')}
"""

        query += """
**要求:**
1. 每天安排2-3个景点(城际移动日可减少为1-2个)
2. 每天必须包含早中晚三餐
3. 每天推荐一个具体的酒店(从酒店信息中选择)
4. 考虑景点之间的距离和交通方式
5. 返回完整的JSON格式数据
6. 景点的经纬度坐标要真实准确
7. 如果天气或酒店信息不足，请基于保守、通用的旅行建议补齐，但不要输出"无法查询"之类的解释文字
8. 若提供了「游记攻略检索」，其中的避坑提醒、预约要求、游玩时长、美食推荐要优先采纳并体现在行程描述与 reservation_tips 中
9. **坐标必须来自「景点信息」中给出的 location 原文，严禁自行推算或照抄其他景点的坐标**：
   若某个景点信息里没有 location，请把该景点的 location 写成 null（或省略该字段），不要编造数字
10. 若景点信息标注了「非实时数据」，请在 description 或 reservation_tips 中提示用户自行核实门票与预约信息
"""
        if is_multi_city:
            query += """
**多城市特殊要求:**
1. 每个 day 对象中必须包含 "city" 字段标明当天所在城市
2. 城市切换当天标记 "is_transfer_day": true, 并在 "transfer_info" 中说明城际交通方式和预计时长
3. 城际移动日的景点数量可适当减少为 1-2 个
4. budget 中增加 "total_inter_city_transport" 字段统计城际交通费用
5. 景点顺序要考虑同城市内的地理位置关系
6. "cities" 数组列出所有途经城市名称
"""

        if request.free_text_input:
            query += f"\n**额外要求:** {request.free_text_input}"

        # 如果用户选择了非中文语言，指示模型用目标语言输出所有文字内容
        _lang = (getattr(request, 'language', 'zh') or 'zh').strip().lower().split('-')[0]
        if _lang != 'zh':
            _lang_names = {"en": "English", "ja": "Japanese", "ko": "Korean", "fr": "French", "de": "German", "es": "Spanish"}
            _target_lang = _lang_names.get(_lang, _lang)
            query += f"""\n\n**语言要求 (Language Requirement):**
请用 {_target_lang} 语言输出所有文字内容（包括 description, overall_suggestions, meals 中的 name/description, hotel 中的 name/address, attractions 中的 name/address/description 等）。
JSON 的 key 名称保持英文不变，只翻译 value 中的文字。"""

        return query
    
    def _sanitize_json_str(self, json_str: str) -> str:
        """清理大模型输出中常见的 JSON 格式污染"""
        import re as _re
        # 1. 移除可能包裹在外面的 ```json ... ``` 标记
        json_str = _re.sub(r'^```(?:json)?\s*', '', json_str.strip())
        json_str = _re.sub(r'```\s*$', '', json_str.strip())
        # 2. 移除 JS 风格注释 // ... 和 /* ... */
        json_str = _re.sub(r'//[^\n]*', '', json_str)
        json_str = _re.sub(r'/\*.*?\*/', '', json_str, flags=_re.DOTALL)
        # 3. 移除 JSON 值中的控制字符
        json_str = _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', json_str)
        # 4. 修复尾部逗号: },] 或 },}
        json_str = _re.sub(r',\s*([\]\}])', r'\1', json_str)
        # 5. 修复中文引号和全角标点
        #    注意: 中文双引号""必须替换为单引号，因为它们通常出现在 JSON 字符串值内部
        #    如果替换为标准双引号会破坏 JSON 结构！
        json_str = json_str.replace('\u201c', "'").replace('\u201d', "'")
        json_str = json_str.replace('\u2018', "'").replace('\u2019', "'")
        json_str = json_str.replace('\uff1a', ':')
        json_str = json_str.replace('\uff0c', ',')
        # 6. 修复 LLM 在 budget 等数值字段中输出算术表达式的问题
        #    例如: "total_attractions": 30+54+120+120=324 → "total_attractions": 324
        #    模式: 冒号后面跟着 数字[+-*/]数字...=最终结果
        def _fix_arithmetic_expr(m):
            """将算术表达式替换为等号后的最终结果，若无等号则尝试 eval"""
            expr = m.group(1).strip()
            if '=' in expr:
                # 取等号后面的最终结果
                return m.group(0).replace(m.group(1), expr.split('=')[-1].strip())
            else:
                # 没有等号，尝试安全计算
                try:
                    result = eval(expr, {"__builtins__": {}}, {})
                    return m.group(0).replace(m.group(1), str(result))
                except Exception:
                    return m.group(0)
        # 匹配 JSON 键值对中冒号后的算术表达式（含 +、-、*、= 且以数字开头）
        json_str = _re.sub(
            r':\s*(\d+(?:\s*[+\-*/]\s*\d+)+(?:\s*=\s*\d+)?)',
            _fix_arithmetic_expr,
            json_str
        )
        return json_str
    
    def _fix_unescaped_quotes(self, json_str: str) -> str:
        """修复 JSON 字符串值内部未转义的双引号
        
        例如: "description": "这是"好的"景点" 
        修复为: "description": "这是'好的'景点"
        """
        import re as _re
        result = []
        i = 0
        in_string = False
        escape_next = False
        
        while i < len(json_str):
            ch = json_str[i]
            
            if escape_next:
                result.append(ch)
                escape_next = False
                i += 1
                continue
            
            if ch == '\\' and in_string:
                escape_next = True
                result.append(ch)
                i += 1
                continue
            
            if ch == '"':
                if not in_string:
                    in_string = True
                    result.append(ch)
                else:
                    # 看下一个非空白字符是否是 JSON 结构字符
                    rest = json_str[i+1:].lstrip()
                    if rest and rest[0] in (',', '}', ']', ':'):
                        # 这是真正的字符串结尾引号
                        in_string = False
                        result.append(ch)
                    elif not rest:
                        # 到末尾了，也是结尾引号
                        in_string = False
                        result.append(ch)
                    else:
                        # 内嵌的未转义引号，替换为单引号
                        result.append("'")
            else:
                result.append(ch)
            
            i += 1
        
        return ''.join(result)

    @staticmethod
    def _balance_json_brackets(text: str) -> str:
        """在非字符串区域统计未闭合的括号并逆序补齐（同时闭合未终止的字符串）。"""
        import re as _re

        stack: list = []
        in_str = False
        escape = False
        for ch in text:
            if escape:
                escape = False
                continue
            if ch == '\\':
                if in_str:
                    escape = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch in ('{', '['):
                stack.append(ch)
            elif ch == '}' and stack and stack[-1] == '{':
                stack.pop()
            elif ch == ']' and stack and stack[-1] == '[':
                stack.pop()

        result = text
        if in_str:
            result = result.rstrip('\\') + '"'
        # 补括号前先去尾逗号：`{"a": 1,` 直接补成 `{"a": 1}` 是合法的，
        # 若先补成 `{"a": 1,}` 反而非法，会迫使上层继续剥离而丢数据。
        result = _re.sub(r',\s*$', '', result.rstrip())
        closing = [']' if c == '[' else '}' for c in reversed(stack)]
        if closing:
            result += ''.join(closing)
        return result

    def _repair_truncated_json(self, json_str: str) -> str:
        """修复被 max_tokens 截断的不完整 JSON。

        截断点可能落在任何位置（键名中间、冒号后、字符串值中间、嵌套数组里），
        用正则穷举各种形态既脆弱又容易误删合法数据。

        因此这里改用**「从尾部逐段剥离 + 每次尝试解析」**的策略：
        每次剥掉一个残缺片段就补一次括号并尝试 json.loads，
        第一个能解析的结果就是最优修复（保留尽可能多的数据）。

        返回空字符串表示「无法修复」，由调用方的多级容错链继续尝试其他候选。

        Raises:
            ValueError: 输入为空。
        """
        import json as _json
        import re as _re

        head = json_str.rstrip()
        if not head:
            raise ValueError("待修复内容为空")

        # 每次剥离「最后一个残缺片段」。
        #
        # 这里刻意**不用正则匹配尾巴**：`r',?\s*"[^"]+$'` 这类模式会跨引号段贪心
        # （对 `{"a": 1, "b"` 会一路吞到 `"a`），得到错误边界。
        # 改为按「最后一个逗号 / 容器起始」切段，只在最后一段内部处理，
        # 从结构上杜绝跨段匹配。
        #
        # 另注：悬挂逗号（`{"a": 1,`）**不能**在这里剥离——补上 `}` 就合法，
        # 提前删逗号反而会退化成 `{"a": 1` → 再剥就丢数据。因此逗号只在
        # 「没有片段可剥」时才作为最后手段处理。
        _FRAGMENT_PATTERNS = (
            r'^\s*"[^"]*"\s*:\s*$',   # 最后一段是 `"days":`（键完整、值缺失）
            r'^\s*"[^"]*"\s*$',       # 最后一段是 `"b"` / `"attrac"`（键无值）
            r'^\s*"[^"]*$',           # 最后一段是 `"attrac`（键名被截断）
            r'^\s*:\s*$',             # 最后一段是裸冒号
        )

        def _last_segment(text: str) -> tuple:
            """按最后一个逗号（或容器起始）切出最后一段，返回 (前缀含分隔符, 最后一段)。

            前缀**必须保留分隔符**：`{"a": 1, "b"` 剥掉 ` "b"` 后要得到
            `{"a": 1`，若连逗号一起丢掉会变成 `{"a": 1 "b"` 这种非法结构。
            """
            cut = max(text.rfind(','), text.rfind('{'), text.rfind('['))
            if cut < 0:
                return '', text
            return text[: cut + 1], text[cut + 1:]

        def _strip_last_fragment(text: str) -> str:
            prefix, segment = _last_segment(text)
            baseline = segment.rstrip()
            for pattern in _FRAGMENT_PATTERNS:
                reduced = _re.sub(pattern, '', segment).rstrip()
                # 必须与 baseline 比较（两侧都 rstrip）。
                # 若误用 segment.lstrip() 比较：模式没匹配时 reduced 仍是
                # ` "b"`，而 lstrip 后是 `"b"`，会被误判成「有变化」，
                # 于是返回一个和输入相同的串，剥离循环原地卡死。
                if reduced == baseline:
                    continue
                # 剥掉残段后前缀可能以逗号结尾，形成悬挂逗号 → 去掉
                rebuilt = (prefix + reduced).rstrip()
                return _re.sub(r',\s*$', '', rebuilt)
            return text

        def _usable(text: str) -> bool:
            """解析结果必须非空——防止剥离过头，把数据全删光后退化成 `{}`。"""
            if not text.strip():
                return False
            try:
                parsed = _json.loads(text)
            except Exception:
                return False
            if isinstance(parsed, (dict, list)) and not parsed:
                return False
            return True

        current = head
        for _ in range(60):
            candidate = self._balance_json_brackets(current)
            if _usable(candidate):
                return candidate

            stripped = _strip_last_fragment(current)
            if stripped == current:
                # 没有片段可剥，才处理悬挂标点（尾逗号等）
                stripped = _re.sub(r'[,:]\s*$', '', current.rstrip())
            if stripped == current or not stripped:
                break
            current = stripped

        return ""

    def _llm_repair_json(self, broken_json: str) -> str:
        """使用 LLM 修复无法自动修复的 JSON（最后手段）"""
        llm = get_llm()
        # 只发送尾部 2000 字符以节省 token
        tail = broken_json[-2000:] if len(broken_json) > 2000 else broken_json
        head = broken_json[:500] if len(broken_json) > 500 else broken_json

        repair_prompt = f"""以下是一段被截断的旅行计划 JSON，请你补全它使其成为合法的 JSON。
只输出修复后的完整 JSON，不要输出任何解释文字。

开头部分:
{head}

...(中间省略)...

尾部被截断部分:
{tail}
"""
        try:
            content = llm.invoke(
                [{"role": "user", "content": repair_prompt}],
                temperature=0.0,
                max_tokens=1500,
                stream=False,
            )
            # 从修复结果中提取 JSON
            import re as _re
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                if end > start:
                    return content[start:end].strip()
            if "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                if end > start:
                    return content[start:end].strip()
            match = _re.search(r'\{[\s\S]*\}', content)
            if match:
                return match.group()
            return content
        except Exception as e:
            print(f"⚠️  LLM 修复 JSON 失败: {e}")
            return broken_json

    def _parse_response(self, response: str, request: TripRequest) -> TripPlan:
        """
        解析Agent响应，带有多层容错清理
        
        Args:
            response: Agent响应文本
            request: 原始请求
            
        Returns:
            旅行计划
        """
        import re as _re
        try:
            # 尝试从响应中提取JSON
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                # 如果没有找到闭合的 ```，说明输出被截断，取到末尾
                if json_end == -1 or json_end <= json_start:
                    json_str = response[json_start:].strip()
                else:
                    json_str = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                if json_end == -1 or json_end <= json_start:
                    json_str = response[json_start:].strip()
                else:
                    json_str = response[json_start:json_end].strip()
            elif "{" in response:
                json_start = response.find("{")
                json_end = response.rfind("}")
                if json_end > json_start:
                    json_str = response[json_start:json_end + 1]
                else:
                    # 没有闭合的 }，取到末尾（截断场景）
                    json_str = response[json_start:]
            else:
                # 响应里根本没有 JSON（模型答非所问 / 直接道歉）。
                # 与「解析失败」同样处理：返回骨架而不是抛异常，前端可展示提示。
                print("⚠️  响应中未找到 JSON 数据，返回兜底计划骨架")
                return self._create_fallback_plan(request)
            
            # ====== 第1轮：基础清理 + 解析 ======
            json_str = self._sanitize_json_str(json_str)
            
            parse_attempts = [
                ("基础清理", json_str),
            ]

            # 预生成各轮修复候选
            fixed_quotes = self._fix_unescaped_quotes(json_str)
            parse_attempts.append(("修复未转义引号", fixed_quotes))

            # 截断修复
            repaired = self._repair_truncated_json(json_str)
            if repaired != json_str:
                parse_attempts.append(("截断修复", repaired))
                # 截断修复 + 引号修复
                repaired_fixed = self._fix_unescaped_quotes(repaired)
                if repaired_fixed != repaired:
                    parse_attempts.append(("截断+引号修复", repaired_fixed))

            # 暴力正则提取
            match = _re.search(r'\{[\s\S]*\}', json_str)
            if match:
                brutal = self._sanitize_json_str(match.group())
                brutal = self._fix_unescaped_quotes(brutal)
                parse_attempts.append(("正则提取", brutal))
                # 对正则提取的结果也做截断修复
                brutal_repaired = self._repair_truncated_json(brutal)
                if brutal_repaired != brutal:
                    parse_attempts.append(("正则+截断修复", brutal_repaired))

            # 依次尝试每种修复
            last_error = None
            for attempt_name, candidate in parse_attempts:
                try:
                    data = json.loads(candidate)
                    if attempt_name != "基础清理":
                        print(f"✅ JSON 通过「{attempt_name}」成功解析")
                        record_json_repair(attempt_name)
                    # 转换为TripPlan对象
                    return TripPlan(**data)
                except (json.JSONDecodeError, Exception) as e:
                    last_error = e
                    if attempt_name == "基础清理":
                        pos = e.pos if hasattr(e, 'pos') else 0
                        context_start = max(0, pos - 60)
                        context_end = min(len(candidate), pos + 60)
                        print(f"⚠️  首次 JSON 解析失败: {e}")
                        print(f"   出错位置附近内容: ...{candidate[context_start:context_end]}...")
                    else:
                        print(f"⚠️  「{attempt_name}」仍失败: {e}")

            # ====== 最终手段：LLM 修复 ======
            print("🔧 所有本地修复均失败，尝试使用 LLM 修复 JSON...")
            llm_fixed = self._llm_repair_json(json_str)
            llm_fixed = self._sanitize_json_str(llm_fixed)
            try:
                data = json.loads(llm_fixed)
                print("✅ JSON 通过 LLM 修复成功解析")
                record_json_repair("LLM 修复")
                return TripPlan(**data)
            except Exception as e_llm:
                print(f"⚠️  LLM 修复后仍然解析失败: {e_llm}")

            # ====== 兜底：语法已合法但缺必填字段 ======
            # 截断点落在尾部、恰好砍掉必填字段时（如 overall_suggestions），
            # 上面所有修复都会因 pydantic 校验失败而前功尽弃。
            # 这些字段缺失不致命——补默认值远好于让整个任务失败。
            for data in self._candidate_dicts(parse_attempts, llm_fixed):
                filled = self._fill_required_defaults(data, request)
                try:
                    print("✅ JSON 语法合法但缺必填字段，已补默认值后解析成功")
                    return TripPlan(**filled)
                except Exception:
                    continue

            # ====== 最后手段：兜底骨架 ======
            # 注意这是「无内容但结构真实」的骨架，不是编造出来的行程。
            # 之所以不直接抛异常：前端已能识别空 attractions 并展示提示，
            # 让用户看到「日期/城市结构 + 明确失败说明」比一个错误页更有用。
            print("⚠️  所有解析手段均失败，返回兜底计划骨架（不含编造内容）")
            try:
                return self._create_fallback_plan(request)
            except Exception as e_fallback:
                print(f"⚠️  兜底计划生成失败: {e_fallback}")
                raise ValueError(f"行程 JSON 解析失败: {str(last_error)}") from last_error
            
        except ValueError:
            raise
        except Exception as e:
            print(f"⚠️  解析响应失败: {str(e)}")
            raise ValueError(f"行程 JSON 解析失败: {str(e)}") from e
    
    @staticmethod
    def _candidate_dicts(parse_attempts, extra_text: str = ""):
        """把各级修复候选里「语法合法」的结果逐个 yield 成 dict。

        用于最后兜底：语法没问题、只是缺必填字段的场景。
        """
        import json as _json

        seen = set()
        texts = [candidate for _, candidate in parse_attempts]
        if extra_text:
            texts.append(extra_text)
        for text in texts:
            if not text or text in seen:
                continue
            seen.add(text)
            try:
                data = _json.loads(text)
            except Exception:
                continue
            if isinstance(data, dict):
                yield data

    @staticmethod
    def _fill_required_defaults(data: dict, request: TripRequest) -> dict:
        """为缺失的必填字段补上安全默认值（只补结构字段，不编造内容）。"""
        filled = dict(data)
        filled.setdefault("city", (request.cities[0].city if request.cities else request.city) or "")
        filled.setdefault("cities", [cs.city for cs in request.cities] or [filled["city"]])
        filled.setdefault("start_date", request.start_date)
        filled.setdefault("end_date", request.end_date)
        filled.setdefault("days", [])
        filled.setdefault("weather_info", [])
        # 用中性措辞，避免假装模型真的给出过建议
        filled.setdefault("overall_suggestions", "（模型未返回总结，建议出行前自行核实门票与预约信息）")
        return filled

    def _create_fallback_plan(self, request: TripRequest) -> TripPlan:
        """创建兜底计划骨架（解析彻底失败时的最后手段）。

        **刻意不编造景点、坐标、餐饮与价格**：
        原实现会生成「{城市}景点1」这种假景点，并附上写死的北京坐标
        （116.4, 39.9）——那正是本项目一直要防的坐标幻觉，比没有计划更糟。

        这里只保留**真实已知的结构信息**（城市、日期、交通、住宿偏好），
        其余留空并明确说明原因，由前端展示提示、用户决定是否重新生成。
        """
        from datetime import datetime, timedelta

        try:
            start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
        except Exception:
            start_date = None

        city_names = [cs.city for cs in request.cities] or ([request.city] if request.city else [])
        notice = "本次未能生成具体行程安排（模型输出无法解析），请重新生成。"

        days = []
        for i in range(max(1, request.travel_days)):
            date_str = (
                (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
                if start_date
                else request.start_date
            )
            day_city = ""
            if request.cities:
                # 按各城市停留天数推算当天所在城市
                offset = 0
                for cs in request.cities:
                    if i < offset + cs.days:
                        day_city = cs.city
                        break
                    offset += cs.days
            days.append(
                DayPlan(
                    date=date_str,
                    day_index=i,
                    city=day_city,
                    description=notice,
                    transportation=request.transportation,
                    accommodation=request.accommodation,
                    attractions=[],
                    meals=[],
                )
            )

        return TripPlan(
            city=city_names[0] if city_names else "",
            cities=city_names,
            start_date=request.start_date,
            end_date=request.end_date,
            days=days,
            weather_info=[],
            overall_suggestions=notice,
        )


# 全局多智能体系统实例
_multi_agent_planner = None


def get_trip_planner_agent() -> MultiAgentTripPlanner:
    """获取多智能体旅行规划系统实例(单例模式)"""
    global _multi_agent_planner

    if _multi_agent_planner is None:
        _multi_agent_planner = MultiAgentTripPlanner()

    return _multi_agent_planner


def reset_trip_planner_agent() -> None:
    """重置旅行规划多智能体实例（用于运行时配置更新后热生效）。"""
    global _multi_agent_planner
    _multi_agent_planner = None

