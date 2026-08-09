# AGENTS.md

This file provides guidance to the AI agent when working with code in this repository.

TripStar (旅途星辰): Vue 3 + FastAPI multi-agent travel planner. Xiaohongshu (小红书) scraping → LLM extraction → Google/AMap geocoding → LLM itinerary JSON.

## Setup & commands

```bash
# backend — npm install is REQUIRED, not optional: the XHS signature engine runs JS via PyExecJS
cd backend && npm install && uv venv .venv && source .venv/bin/activate && uv pip install -r requirements.txt
uvicorn app.api.main:app --reload --port 8000      # run from backend/, not repo root

cd frontend && npm install && npm run dev          # :5173
```

- There are **no tests, linters, or CI**. Never claim "tests pass". Verify by running the app.
- `npm run build` = `vue-tsc && vite build`; the Dockerfile deliberately skips `vue-tsc` (`npx vite build`). Type errors ship in Docker but break local builds.
- Docker binds **7860** (`start.sh`, gunicorn, `backend.app.api.main:app`); local dev is 8000.
- Must stay `--workers 1`: WebSocket subscribers live in an in-process dict.

## Config

- `backend/app/config.py` — pydantic-settings. LLM vars accept either name via `AliasChoices`: `LLM_API_KEY|OPENAI_API_KEY`, `LLM_BASE_URL|OPENAI_BASE_URL`, `LLM_MODEL_ID|OPENAI_MODEL`.
- `backend/runtime_settings.json` (written by `PUT /api/settings`) is loaded at import and **overrides env vars**. If keys seem wrong, check this file before `.env`.
- `CORS_ORIGINS` is a **comma-separated string**, not a JSON list.
- Required: LLM key/base/model, `VITE_AMAP_WEB_KEY`, `XHS_COOKIE`. Optional: `GOOGLE_MAPS_API_KEY`, `GOOGLE_MAPS_PROXY`.
- `config.py` also loads a sibling `../HelloAgents/.env` if present (non-overriding).

## Backend gotchas

- **HelloAgents agents are instantiated, never subclassed**: `SimpleAgent(name, llm, system_prompt)` + `.add_tool()`. No decorators. `.run()` is sync → always wrap in `asyncio.to_thread`. Tool calls are a prompt-taught text protocol: `[TOOL_CALL:tool:k=v]`.
- MCP tool names in prompts need the server prefix (`amap_maps_weather`, `amap_maps_text_search`) because `auto_expand=True`; `AmapService.run()` uses unprefixed `maps_*`.
- `_parse_response()` in `agents/trip_planner_agent.py` is a deliberate 6-stage JSON repair chain ending in an LLM repair call. LLMs return malformed JSON here constantly — don't "simplify" it.
- In `plan_trip`, the three per-city lookups (attractions/weather/hotels) run under one `asyncio.gather`, but **cities stay sequential on purpose**: `weather_agent`/`hotel_agent` are shared singletons and must not be driven concurrently. Attraction failures abort the plan; weather/hotel failures degrade to a placeholder string.
- Tasks persist to `backend/data/trip_tasks/{task_id}.json`; loaded at import of `api/routes/trip.py`, and unfinished tasks are force-failed on restart. Progress is pushed over `WS /api/trip/ws/{task_id}`; `GET /api/trip/status/{id}` is for resume.
- `xhs_sign/sign_util.py` compiles ~4MB of JS at import via PyExecJS — needs `node` on PATH and `backend/node_modules`. Expired cookie surfaces as XHS code `300011` → `XHSCookieExpiredError`; network/parse failures raise `XHSFetchError` instead, so don't collapse the two.
- Geocoding returns `Optional[dict]` and yields `None` on failure — never re-introduce a fixed coordinate fallback, which silently plots attractions in the wrong city. Callers omit `location` and let the planner LLM fill it.
- Map dispatch: Google if `GOOGLE_MAPS_API_KEY` set, else AMap. One Google geocode failure latches the whole process to AMap; `PUT /api/settings` clears it via `reset_google_geo_failure()`.
- `GET /api/settings` **masks** `openai_api_key`/`xhs_cookie`/`vite_amap_web_key`; `update_runtime_settings` ignores any value containing the mask char (`\u2022`). `get_runtime_settings()` always masks — read the `settings` object directly if you need a real value in-process.
- `/api/poi/photo` is backed by a bounded TTL cache in `xhs_service.py` — it is a live Xiaohongshu scrape, so don't bypass the cache or the cookie gets rate-limited.
- `app/api/routes/map.py` + `AmapService` MCP-result parsing are still unimplemented stubs; they now return `success=False` with an explanatory message rather than faking success.
- Code comments, log messages, and prompts are in Chinese — match that.

## Frontend gotchas

- Locale IDs are full tags: `'zh-CN' | 'en-US' | 'ja-JP'` (files are `zh.json`/`en.json`/`ja.json`). Never use `'zh'`. Any new string must be added to **all three** locale JSONs or it silently falls back to Chinese.
- The UI language is sent to the backend as the `language` field in the plan request body.
- No Pinia/router file: routes are declared inline in `src/main.ts` and are **lazy-loaded** — keep them that way, static-importing `Result.vue` drags echarts/html2canvas/swiper into the entry chunk. Cross-route state is `sessionStorage` (`tripPlan`, `graphData`, `planId`).
- An in-flight plan is recoverable: the task id is stored under `tripstar.pendingTaskId` and `Landing.vue` re-attaches on mount via `resumeTripPlan()`. Clear that key whenever a task settles.
- `src/services/api.ts` resolves `baseURL` per request (localStorage → `VITE_API_BASE_URL` → `window.location.origin`), so the `vite.config.ts` `/api` proxy is effectively unused and backend CORS matters. `timeout: 0` and no retries are intentional.
- AMap `securityJsCode` comes from `VITE_AMAP_SECURITY_JS_CODE`, substituted into `index.html` by a small `transformIndexHtml` plugin in `vite.config.ts` (Vite's built-in `%VAR%` replacement leaves the literal placeholder when the var is undefined). There is no `VITE_` var for the Google key — it comes from backend settings.
- AMap needs `WebGLParams.preserveDrawingBuffer: true` or the html2canvas export renders blank.
- echarts is an **on-demand build** (`echarts/core` + `echarts.use([...])`). Using a new chart type or component means registering it and extending the local `ECOption` compose type; `EChartsOption` does not exist on `echarts/core`.
- `initMap()` guards against its own timeout via a `mapInitGeneration` token. Any new `await` inside the Google init path needs the same staleness check, or a timed-out init resurrects a second live map.
- `src/styles/global.css` is a vendored third-party theme (~9k lines) — don't edit it. Real styling is scoped `<style>` per component with hand-written `rgba()` + `backdrop-filter`, gold accents `#FFD699`/`#FFB347`.
- `src/views/Result.vue` is a ~4.7k-line monolith (maps, ECharts graph, export, chat host). Expect to edit it in place.
- Anything written into `innerHTML` (the export builder, map info windows) must go through `escapeHtml`/`safeImageUrl` — all of that content is LLM-generated.

## Repo etiquette

- PRs follow `.github/pull_request_template.md`.
- User-facing docs exist in three languages: update `README.md`, `README_en.md`, and `README_ja.md` together.
