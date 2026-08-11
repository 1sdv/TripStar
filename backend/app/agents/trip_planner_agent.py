"""多智能体旅行规划系统"""

import json
import asyncio
import os
from typing import Dict, Any, List, Callable, Awaitable, Optional
from hello_agents import SimpleAgent
from hello_agents.tools import MCPTool
from ..services.llm_service import get_llm
from ..models.schemas import TripRequest, TripPlan, DayPlan, Attraction, Meal, WeatherInfo, Location, Hotel
from ..config import get_settings

# ============ Agent提示词 (动态模版化，支持 amap / google 双供应商) ============


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

    async def _fallback_amap_weather(self, city: str) -> str:
        """使用高德天气 HTTP REST API 直接获取天气, 作为 Google Weather 的降级备选。

        跳过 MCP Agent 调用, 直接用 httpx 请求高德天气 API。
        """
        import httpx
        settings = get_settings()
        amap_key = settings.vite_amap_web_key
        if not amap_key:
            return "高德 Web Key 未配置，无法降级查询天气"

        # 很多时候 request.city 会带有国家/省份前缀，例如 "中国-北京"
        # 高德天气 API 严格要求城市名或 adcode，所以我们提取最后一段
        clean_city = city.split("-")[-1].strip()

        # 高德天气 REST API: https://lbs.amap.com/api/webservice/guide/api/weatherinfo
        url = "https://restapi.amap.com/v3/weather/weatherInfo"
        params = {"key": amap_key, "city": clean_city, "extensions": "all", "output": "JSON"}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, params=params)
                data = resp.json()
            forecasts = data.get("forecasts", [])
            if not forecasts:
                return f"高德天气 API 无预报数据: {json.dumps(data, ensure_ascii=False)}"
            casts = forecasts[0].get("casts", [])
            result_lines = []
            for c in casts:
                result_lines.append(
                    f"{c.get('date','')}: 白天{c.get('dayweather','')} {c.get('daytemp','')}°C, "
                    f"夜间{c.get('nightweather','')} {c.get('nighttemp','')}°C, "
                    f"{c.get('daywind','')}风 {c.get('daypower','')}"
                )
            return "\n".join(result_lines) if result_lines else json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return f"高德天气降级 HTTP 请求失败: {e}"
    
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

            from ..services.xhs_service import search_xhs_attractions
            keywords = request.preferences[0] if request.preferences else "景点"
            _lang = (getattr(request, 'language', 'zh') or 'zh').strip().lower().split('-')[0]
            _lang_hint = "" if _lang == "zh" else f" Please respond in {'English' if _lang == 'en' else _lang}."

            # ========== 按城市逐一搜集信息 ==========
            all_attractions: Dict[str, str] = {}
            all_weather: Dict[str, str] = {}
            all_hotels: Dict[str, str] = {}

            for idx, city_stay in enumerate(cities):
                city = city_stay.city
                # 计算当前城市对应的进度区间: 10 ~ 75 之间按城市均分
                progress_base = int(10 + (idx / total_cities) * 65)
                progress_step = max(int(65 / total_cities / 3), 3)
                city_label = f" ({idx+1}/{total_cities})" if total_cities > 1 else ""

                # [1] 景点搜索
                print(f"  [{idx+1}/{total_cities}] 正在搜索 {city} 的景点...")
                await self._emit_progress(
                    progress_callback, "attraction_search",
                    f"正在搜索 {city} 的景点...{city_label}",
                    progress_base
                )
                attraction_response = await asyncio.to_thread(
                    search_xhs_attractions, city, keywords, _lang
                )
                all_attractions[city] = attraction_response
                print(f"📍 {city} 景点搜索结果: {attraction_response[:150]}...")

                # [2] 天气查询
                print(f"  [{idx+1}/{total_cities}] 正在查询 {city} 的天气...")
                await self._emit_progress(
                    progress_callback, "weather_search",
                    f"正在查询 {city} 的天气...{city_label}",
                    progress_base + progress_step
                )
                weather_query = f"请查询{city}的天气信息{_lang_hint}"
                weather_response = await asyncio.to_thread(self.weather_agent.run, weather_query)
                print(f"🌤️  {city} 天气查询结果: {weather_response[:150]}...")

                # Google 天气降级
                _weather_fail_keywords = ("无法", "失败", "错误", "error", "unknown", "抱歉", "sorry")
                if self.map_provider == "google" and any(kw in weather_response.lower() for kw in _weather_fail_keywords):
                    print(f"  ⚠️ {city} Google 天气查询失败，降级到高德天气 API...")
                    try:
                        weather_response = await self._fallback_amap_weather(city)
                        print(f"  ✅ {city} 高德天气降级成功: {weather_response[:150]}...")
                    except Exception as _wb_err:
                        print(f"  ❌ {city} 高德天气降级也失败: {_wb_err}")
                all_weather[city] = weather_response

                # [3] 酒店搜索
                print(f"  [{idx+1}/{total_cities}] 正在搜索 {city} 的酒店...")
                await self._emit_progress(
                    progress_callback, "hotel_search",
                    f"正在搜索 {city} 的酒店...{city_label}",
                    progress_base + progress_step * 2
                )
                hotel_query = f"请搜索{city}的{request.accommodation}酒店{_lang_hint}"
                hotel_response = await asyncio.to_thread(self.hotel_agent.run, hotel_query)
                all_hotels[city] = hotel_response
                print(f"🏨 {city} 酒店搜索结果: {hotel_response[:150]}...")

            print(f"\n✅ 全部 {total_cities} 个城市基础信息搜集完成\n")

            # ========== 统一规划阶段 ==========
            planning_label = "正在生成多城市行程计划..." if total_cities > 1 else "正在生成旅行计划..."
            print(f"📋 步骤4: {planning_label}")
            await self._emit_progress(progress_callback, "planning", planning_label, 85)

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

            planner_response = await self._run_planner_with_retry(
                request,
                all_attractions,
                all_weather,
                all_hotels,
                memory_snippet,
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
    ) -> str:
        """规划阶段使用更长超时，并在超时后重试一次。

        Args:
            attractions: {city_name: 景点搜索结果文本}
            weather: {city_name: 天气查询结果文本}
            hotels: {city_name: 酒店搜索结果文本}
            memory_snippet: 用户历史偏好文本，注入规划 Prompt
        """
        timeout = int(os.getenv("TRIP_PLANNER_TIMEOUT", "180"))
        planner_query = self._build_planner_query(request, attractions, weather, hotels, memory_snippet)

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
    ) -> str:
        """构建行程规划查询（支持多城市）

        Args:
            attractions: {city_name: 景点搜索结果文本}
            weather: {city_name: 天气查询结果文本}
            hotels: {city_name: 酒店搜索结果文本}
            memory_snippet: 用户历史偏好文本
        """
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
            if is_multi_city:
                query += f"""
--- {city} ({cs.days}天) ---
**{city} 景点信息:**
{attractions.get(city, '无')}
**{city} 天气信息:**
{weather.get(city, '无')}
**{city} 酒店信息:**
{hotels.get(city, '无')}
"""
            else:
                query += f"""
**景点信息:**
{attractions.get(city, '无')}

**天气信息:**
{weather.get(city, '无')}

**酒店信息:**
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

    def _repair_truncated_json(self, json_str: str) -> str:
        """修复被 max_tokens 截断的不完整 JSON。

        策略：
        1. 如果最后一个字符在字符串值内部，先关闭该字符串。
        2. 移除最后一个不完整的键值对（trailing comma 之后的碎片）。
        3. 根据打开/关闭的括号差额，补齐缺失的 ] 和 }。
        """
        import re as _re

        s = json_str.rstrip()
        if not s:
            return s

        # --- Step 1: 关闭未终止的字符串 ---
        in_str = False
        escape = False
        for ch in s:
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if ch == '"':
                in_str = not in_str
        if in_str:
            # 去掉尾部可能的碎片转义符
            s = s.rstrip('\\')
            s += '"'

        # --- Step 2: 移除尾部不完整的键值对碎片 ---
        # 常见模式: 值字符串闭合后紧跟着换行但后面没有逗号/括号
        # 或者尾部是 "key": 但缺少值
        # 尝试反复去除尾部碎片直到以合法的 JSON 结构字符结尾
        for _ in range(10):
            stripped = s.rstrip()
            if not stripped:
                break
            last = stripped[-1]
            if last in ('}', ']', '"', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
                        'e', 'l', 's'):
                # 'e' for true/false, 'l' for null, 's' unlikely but safe
                break
            # 当前尾部是非法字符(如冒号、逗号、空键名开头等)，回退一个 token
            s = stripped[:-1]

        # 移除尾部悬挂的逗号
        s = _re.sub(r',\s*$', '', s)

        # --- Step 3: 补齐缺失的闭合括号 ---
        open_braces = s.count('{') - s.count('}')
        open_brackets = s.count('[') - s.count(']')

        # 更精确: 扫描非字符串中的括号
        stack = []
        in_str2 = False
        esc2 = False
        for ch in s:
            if esc2:
                esc2 = False
                continue
            if ch == '\\' and in_str2:
                esc2 = True
                continue
            if ch == '"':
                in_str2 = not in_str2
                continue
            if in_str2:
                continue
            if ch in ('{', '['):
                stack.append(ch)
            elif ch == '}' and stack and stack[-1] == '{':
                stack.pop()
            elif ch == ']' and stack and stack[-1] == '[':
                stack.pop()

        # 用精确的 stack 逆序关闭
        closing = [']' if c == '[' else '}' for c in reversed(stack)]
        if closing:
            s += '\n' + ''.join(closing)

        return s

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
            response = llm._client.chat.completions.create(
                model=llm.model,
                messages=[{"role": "user", "content": repair_prompt}],
                temperature=0.0,
                max_tokens=1500,
            )
            content = response.choices[0].message.content or ""
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
                raise ValueError("响应中未找到JSON数据")
            
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
                return TripPlan(**data)
            except Exception as e_llm:
                print(f"⚠️  LLM 修复后仍然解析失败: {e_llm}")
                # 最终 raise 最初的错误
                raise ValueError(f"行程 JSON 解析失败: {str(last_error)}") from last_error
            
        except ValueError:
            raise
        except Exception as e:
            print(f"⚠️  解析响应失败: {str(e)}")
            raise ValueError(f"行程 JSON 解析失败: {str(e)}") from e
    
    def _create_fallback_plan(self, request: TripRequest) -> TripPlan:
        """创建备用计划(当Agent失败时)"""
        from datetime import datetime, timedelta
        
        # 解析日期
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
        
        # 创建每日行程
        days = []
        for i in range(request.travel_days):
            current_date = start_date + timedelta(days=i)
            
            day_plan = DayPlan(
                date=current_date.strftime("%Y-%m-%d"),
                day_index=i,
                description=f"第{i+1}天行程",
                transportation=request.transportation,
                accommodation=request.accommodation,
                attractions=[
                    Attraction(
                        name=f"{request.city}景点{j+1}",
                        address=f"{request.city}市",
                        location=Location(longitude=116.4 + i*0.01 + j*0.005, latitude=39.9 + i*0.01 + j*0.005),
                        visit_duration=120,
                        description=f"这是{request.city}的著名景点",
                        category="景点"
                    )
                    for j in range(2)
                ],
                meals=[
                    Meal(type="breakfast", name=f"第{i+1}天早餐", description="当地特色早餐"),
                    Meal(type="lunch", name=f"第{i+1}天午餐", description="午餐推荐"),
                    Meal(type="dinner", name=f"第{i+1}天晚餐", description="晚餐推荐")
                ]
            )
            days.append(day_plan)
        
        return TripPlan(
            city=request.city,
            start_date=request.start_date,
            end_date=request.end_date,
            days=days,
            weather_info=[],
            overall_suggestions=f"这是为您规划的{request.city}{request.travel_days}日游行程,建议提前查看各景点的开放时间。"
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

