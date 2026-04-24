# TripStar - AI Travel Agent


> **A Multi-Agent Collaborative Travel Planning Platform Based on the HelloAgents Framework**
<img width="1823" height="805" alt="image" src="https://github.com/user-attachments/assets/e7fb750f-32e5-4a77-93f7-e7b1c4e5e915" />
<p align="center">
  <img src="https://img.shields.io/badge/license-GPL--2.0-orange">
  <img src="https://img.shields.io/badge/version-v2.0.0-green">
  <img src="https://img.shields.io/badge/Docker-Build-blue?logo=docker">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg">
  <img src="https://img.shields.io/badge/vue-3.x-brightgreen.svg">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-teal.svg">
</p>

<div align="center">

[🇨🇳 中文](README.md) | [🇺🇸 English](README_en.md) | [🇯🇵 日本語](README_ja.md)

</div>

> [!IMPORTANT]
> 
> You can try the project directly online. For the full experience, you can deploy it locally. **Due to risk control, the online trial does not connect to Xiaohongshu (RED)**: [TripStar - AI Travel Agent](https://modelscope.cn/studios/lcclxy/Journey-to-the-China)
> 
> Features include: Travel Plans, Attraction Maps Overview, Budget Details, Daily Itinerary: Itinerary Description, Transportation, Accommodation Recommendations, Attraction Scheduling (address, duration, description, reservation reminders), Dining Plans, Weather Information, Knowledge Graph Visualization, Immersive AI Q&A Companion...

## Project Introduction

**TripStar** is an innovative AI travel agent application, a multi-agent collaborative travel planning platform based on the HelloAgents framework, designed to solve the "information overload" and "decision fatigue" users face when planning trips.

Unlike traditional travel guide websites, this project adopts an innovative model based on **Large Language Models (LLM)** and **Multi-Agent** collaboration. Like an experienced human travel butler, it comprehensively considers users' personalized needs (preferences: transportation, accommodation style, travel interests, special requests, etc.), automatically searching for travel info, checking local weather, curating hotels, and planning optimal attraction routes to **quickly generate a travel itinerary**.

### Core Highlights

* **Deep Xiaohongshu (RED) Integration**: Attraction recommendations and travel guide data come directly from real users' travelogues on Xiaohongshu. LLMs intelligently refine this data to extract the most authentic tips and check-in suggestions. Attraction images are also retrieved in real-time from Xiaohongshu, ensuring the display of the latest, authentic user-taken scenery photos.
* **Attraction Reservation Reminders**: Intelligently identifies attractions mentioned in Xiaohongshu travelogues that require advance booking (e.g., the Forbidden City, Shaanxi History Museum), distinctly highlighting reservation prompts and channels in the itinerary cards to save you a wasted trip.
* **Multi-Language & Internationalization Support**: Deeply integrates Vue I18n, while natively supporting language localization at both the LLM prompt level and the knowledge graph data structure. The system UI and AI Q&A seamlessly switch between multiple languages (Chinese/English/Japanese), dynamically translating generated travel plans into the target language to provide a barrier-free trip planning experience for global travelers.
* **Dual-Engine Custom Interactive Map**: Deeply integrates and supports seamless switching and automatic fallback between **Google Maps** and **AMap (GaoDe)**. Uses Google Maps overseas and falls back to AMap domestically. Dynamically draws a real latitude and longitude route ("Start - Attraction - End"), with high-end customized basemap colors, giving an instant preview of attraction locations for easy itinerary scheduling.
* **Precise Budget Detail Panel**: Intelligently aggregates multi-dimensional expenses like tickets, dining, accommodation, and transportation, providing an intuitive financial panel to keep your travel budget in check.
* **Multi-Agent Collaboration**: Employs multiple agents with clear divisions of labor (e.g., Weather Forecaster, Hotel Recommendation Expert), working together via a defined Workflow to complete complex travel planning tasks.
* **Knowledge Graph Visualization**: Real-time conversion of generated itinerary data into a node-relationship graph, intuitively displaying the spatial structure of "City - Days - Itinerary Nodes - Budget".
* **Immersive AI Q&A Companion**: After generating the report, provides a floating AI Q&A window (bottom left). The AI retains complete contextual memory of the itinerary, allowing users to ask follow-up questions at any time regarding itinerary details (like ticket prices, or suitability).
* **Luxury Dark Glassmorphism Design**: A completely redesigned Dark Luxury Glassmorphism UI, offering a highly immersive, premium visual experience.

---
> For example, if you want to travel to USA-NewYork, simply fill in the destination, dates, and preferences, wait for the itinerary planning results, and preview how to arrange your tour at a glance.
<img width="1599" height="741" alt="image" src="https://github.com/user-attachments/assets/959d4a2e-7e2b-4136-bd93-bc9ba90a4e80" />


## System Architecture

The project uses a standard decoupled frontend-backend architecture, divided into the Vue frontend interaction layer, FastAPI backend service layer, and the LLM/Agents intelligent inference layer.

```mermaid
graph TD
    subgraph G1 ["Frontend View"]
        A1["Param Input Home.vue"]
        A2["Immersive Loading Animation"]
        A3["Premium Itinerary Result.vue"]
        A4["Knowledge Graph Sidebar"]
        A5["AI Travel Agent Float Window"]
    end

    subgraph G2 ["Backend Gateway"]
        B1["Async Polling <br/> POST/plan & GET/status"]
        B2["Contextual AI Q&A<br/>POST/chat/ask"]
        B3["Attraction Image API<br/>GET/poi/photo"]
    end

    subgraph G3 ["Multi-Agent Engine"]
        C1["Main Journey Agent"]
        C2["Xiaohongshu Parser<br/>(SSR + LLM Refine)"]
        C3["Weather Agent"]
        C4["Hotel Recommendation Agent"]
    end

    subgraph G4 ["Service Layer"]
        D1["LLM API <br/> doubao-seed-1-8-251228"]
        D2["Geocoding / POI Search Server <br/> (AMap/Google)"]
        D3["Weather/Time Retrieval Tool"]
        D4["Xiaohongshu API<br/>Search/SSR Scrape"]
    end

    %% Interactions
    A1 --> B1
    A3 <--> B1
    A3 --> B3
    A5 <--> B2

    B1 --> C1
    B2 --> D1
    B3 --> D4

    C1 --> C2
    C1 --> C3
    C1 --> C4

    C2 <--> D4
    C2 --> D1
    C2 --> D2
    C3 <--> D3
    C4 <--> D2
```

---

## Core Features & Workflow

### 1. Asynchronous Polling System (Solves Gateway Timeout)

To solve the 504 Gateway Timeout issue caused by long-duration LLM inference, the backend routing mechanism was refactored:

* **`POST /api/trip/plan`**: Instantly returns a `task_id`, pushing the multi-minute inference task into the background via `asyncio.create_task`.
* **`GET /api/trip/status/{task_id}`**: The frontend makes lightweight polling requests every 3 seconds to get the real-time processing progress (e.g., "🔍 Searching for attractions...") until the status hits `completed`.

### 2. Multi-Agent Architecture (Agentic Workflow)

Upon receiving natural language instructions, the Main Agent breaks down the task using ReAct:

1. **Xiaohongshu Attraction Extraction**: Searches city travel guide posts, extracts their text via an SSR scraper, and then uses the LLM to refine the lengthy travelogues into structured data: attraction names, authentic reviews, play durations, and reservation requirements. Finally, a POI search API is used to fetch precise coordinates.
2. **Weather & Hotel**: The Weather agent queries the climate for the target dates; the Hotel agent finds suitable lodging options based on the budget.
3. **Route Orchestration**: The Main Agent gathers third-party data, orchestrates the workflow, and calculates the distances and optimal visit orders to avoid backtracking.
4. **Attraction Image Search (Frontend Driven)**: After generating the itinerary, the frontend independently calls the `/api/poi/photo` endpoint for each attraction. The backend then searches for the newest posts on Xiaohongshu based on the attraction name, scraping the direct link of the first image via SSR, ensuring an authentic real-life snapshot.
5. **Result Aggregation**: The final output is structured JSON encompassing budget details, daily schedules, reservation reminders, and anti-scam tips.

### 3. Data-Driven Dynamic Component Rendering

The frontend renders dynamic Vue structures recursively by reading JSON data:

* **Map JS API Components**: Dynamically reads POI coordinates to draw polylines and map markers.
* **ECharts Knowledge Graph**: Translates the hierarchical travel structure into a relational node network (an early form of a graph database).

---

## Quick Deployment Guide

### Environment Prerequisites

* Python 3.10+
* Node.js 18+
* Large Model API Key (OpenAI-compatible endpoints highly recommended, e.g., Doubao, [MiniMax-M2.7](https://platform.minimax.io/docs/api-reference/text-openai-api))
* AMap Keys (Web Service & Web JS API) with **Security JSCode configured in `index.html`** or Google Maps APIs. If using [Google Maps](https://developers.google.com/maps/apis-by-platform), you must enable: **Geocoding API, Places API (New), Directions API, Maps JavaScript API, and Weather API** in Google Cloud Console, and an active billing account is strictly required.
* Xiaohongshu Cookie (Retrieve from browser dev tools after logging in on Web)
* The `uv` package manager

### Docker / Compose Conventions

It is highly recommended to start the project (both frontend and backend) via `docker-compose`. Ensure your `.env` variables are configured before starting:

* The backend does NOT read the `backend/.env` file during container startup. All config is passed via environments setup.
* `docker-compose.yaml` explicitly maps essential proxies and API keys, supporting variables like `GOOGLE_MAPS_API_KEY` and `GOOGLE_MAPS_PROXY`.
* Frontend build-time variable `VITE_AMAP_WEB_JS_KEY` is injected via `build.args`.

**One-Click Start Command:**
```bash
# Build and run containers in background
docker-compose up -d --build

# Follow service logs
docker-compose logs -f
```

For local development, follow the distinct environment configurations below.

### Local Development

#### 1. Start Backend

```bash
# Navigate to backend directory
cd backend

# Install Node.js dependencies for Xiaohongshu signature engine
npm install

# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install project dependencies
pip install -r requirements.txt

# Copy config and fill your API KEYs
cp .env.example .env
# [Required] LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_ID (pick a model good at JSON struct)
# [Optional] VITE_AMAP_WEB_KEY
# [Required] XHS_COOKIE
# [Required] GOOGLE_MAPS_API_KEY, GOOGLE_MAPS_PROXY

# Start FastAPI (Uvicorn recommended)
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```
Once the API is live, visit `http://localhost:8000/docs` to test Interactive Swagger integrations.

#### 2. Start Frontend

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (npm/pnpm/yarn)
npm install

# Set frontend environment config.
# [Required] VITE_AMAP_WEB_KEY (Same as backend)
# [Required] VITE_AMAP_WEB_JS_KEY 
# **MUST ALSO inject Security JSCode in index.html (AMap API v2.0 requirement)**

# Run Vite dev server
npm run dev
```

---

## Directory Structure

```text
TripStar/
├── backend/                       # Python FastAPI Backend
│   ├── app/
│   │   ├── api/routes/            # Core routing (trip.py, poi.py, chat.py)
│   │   ├── agents/                # Agent definitions (trip_planner_agent.py)
│   │   ├── services/              # Business logic layers
│   │   │   ├── xhs_service.py     # RED Parsing/SSR/LLM
│   │   │   ├── llm_service.py     # Base LLM Wrapper
│   │   │   └── knowledge_graph_service.py  # KG formatting
│   │   └── models/                # Pydantic Schemas
│   └── .env                       # Local Env
│
├── frontend/                      # Vue 3 Frontend UI
│   ├── src/
│   │   ├── views/                 # Views (Home.vue; Result.vue)
│   │   ├── components/            # UI components
│   │   └── services/              # Async polling & retries
│   ├── index.html                 # Index Entry & AMap Token injection
│   ├── .env                       # Frontend Local Env
│   └── package.json
│
├── Dockerfile                     # Generic Prod Docker
├── docker-compose.yaml            # Single-node Compose Setup
└── README_en.md
```
> Below are some of the operation results, exploring rich functions...
<img width="1599" height="823" alt="image" src="https://github.com/user-attachments/assets/0af91914-a087-496f-8a69-caed6748374d" />
<img width="1649" height="805" alt="image" src="https://github.com/user-attachments/assets/c1d08148-6f81-4428-b10d-ff51083af1a6" />
<img width="1598" height="801" alt="image" src="https://github.com/user-attachments/assets/1b4b745e-98f1-4868-a6dd-d32909077713" />


## Future Optimizations
- [x] ~~Xiaohongshu Integration~~
- [x] ~~Attraction Images via Xiaohongshu Search~~
- [x] ~~Attraction Reservation Prompts~~
- [x] ~~Google Maps Dual-Engine Fallback~~
- [x] ~~i18n Multi-Language Model Inference Adaptation & Deep Knowledge Graph Translation~~
- [x] ~~History Plans Record Support~~
- [x] ~~HTTP/SOCKS5 Proxy Config~~
- [x] ~~Better Export Image aesthetics~~
- [ ] Multi-City Travel Planning
- [ ] Advanced Dining Recommendations

## Star History

<a href="https://www.star-history.com/?repos=1sdv%2FTripStar&type=date&logscale=&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/image?repos=1sdv/TripStar&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/image?repos=1sdv/TripStar&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/image?repos=1sdv/TripStar&type=date&legend=top-left" />
 </picture>
</a>

## 🙏 Acknowledgements
Thanks to the [linux.do](https://linux.do/) community for communication and feedback, making TripStar iterate more efficiently.
