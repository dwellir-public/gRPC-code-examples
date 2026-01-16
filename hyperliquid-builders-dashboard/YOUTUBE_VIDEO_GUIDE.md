# YouTube Video Guide: Hyperliquid Builders Dashboard

A complete guide for creating a YouTube video explaining this project.

---

## Video Overview

**Title Ideas:**
- "Build a Real-Time Hyperliquid Dashboard with gRPC & React"
- "Streaming Blockchain Data: Hyperliquid Builder Analytics Dashboard"
- "Python + React: Live Trading Dashboard with gRPC Streaming"

**Duration:** 15-25 minutes

**Target Audience:** Developers interested in blockchain data, real-time applications, gRPC

---

## Video Structure

### 1. Introduction (1-2 minutes)

**Script:**
> "In this video, I'll show you how to build a real-time dashboard that tracks builder fees on Hyperliquid - one of the fastest decentralized exchanges.
>
> We'll use gRPC streaming to get live trade data, process it with a Python backend, and display it with a React frontend.
>
> By the end, you'll have a working dashboard that updates in real-time as trades happen on the blockchain."

**Visuals:**
- Show the running dashboard
- Highlight data updating in real-time
- Quick scroll through the code structure

---

### 2. Architecture Overview (2-3 minutes)

**Script:**
> "Let me explain how this works at a high level.
>
> Hyperliquid exposes a gRPC API that streams fill events - every trade that happens on the exchange.
>
> Our Python backend connects to this stream and processes each fill, extracting the builder address and fees.
>
> It aggregates these stats and broadcasts updates over WebSocket to any connected frontend clients.
>
> The React frontend displays this data with charts and rankings that update instantly."

**Visuals:**
- Draw or show the architecture diagram from README
- Highlight data flow: Hyperliquid → gRPC → Python → WebSocket → React

---

### 3. Project Setup (3-4 minutes)

**Script:**
> "Let's get the project running. First, clone the repo and look at the structure."

**Demo Steps:**
1. Show project structure
2. Create `.env` file with gRPC endpoint
3. Set up Python virtual environment
4. Install Python dependencies
5. Install Node dependencies
6. Run `./start.sh`

**Commands to show:**
```bash
# Backend setup
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend setup
cd frontend
npm install

# Run both
./start.sh
```

---

### 4. Backend Deep Dive (5-7 minutes)

#### 4a. Configuration (`config.py`)

**Script:**
> "The config module loads environment variables and builder metadata. Notice how we normalize the gRPC endpoint and load builder names from a JSON file."

**Key points:**
- Environment variable handling
- Builder metadata from `builders.json`
- Default Dwellir endpoint

#### 4b. gRPC Client (`grpc_client.py`)

**Script:**
> "This is where we connect to Hyperliquid. The gRPC client opens a streaming connection and yields fill data as it arrives.
>
> Each fill contains the price, size, builder address, and importantly - the fee amount and fee token."

**Key points:**
- Async generator pattern
- SSL credentials
- Large message size handling (150MB)
- Automatic reconnection

#### 4c. Stats Aggregation (`builder_stats.py`)

**Script:**
> "The StatsAggregator is the heart of the backend. It processes each fill and updates running totals.
>
> Notice how we only count fees in USD stablecoins - any fee token starting with 'USD' like USDC or USDH."

**Key points:**
- Thread-safe with Lock
- USD fee filtering (important!)
- Unique user tracking
- Known vs Unknown builders

#### 4d. FastAPI Server (`main.py`)

**Script:**
> "The main file ties it all together. We have a background task that processes the gRPC stream, and a WebSocket endpoint that broadcasts updates.
>
> When a client connects, they immediately receive the current state, then get updates as new fills come in."

**Key points:**
- Lifespan handler for startup/shutdown
- WebSocket connection manager
- Broadcast pattern

---

### 5. Frontend Deep Dive (4-5 minutes)

#### 5a. WebSocket Hook (`useWebSocket.ts`)

**Script:**
> "The frontend uses a custom React hook to manage the WebSocket connection. It handles automatic reconnection and parses incoming messages into typed state."

**Key points:**
- Connection lifecycle
- Automatic reconnect (3 second delay)
- TypeScript types for messages

#### 5b. Main Components

**Script:**
> "The app is composed of several components:
> - StatsCards show the key metrics at the top
> - RevenueChart displays a horizontal bar chart of builder fees
> - TopBuilders is a sidebar that can toggle between fees and volume
>
> All components receive data from the WebSocket hook and re-render when new data arrives."

**Key points:**
- Component composition
- Data flow from hook to components
- Real-time re-rendering

---

### 6. Live Demo (2-3 minutes)

**Script:**
> "Let's watch it in action. I'll open the dashboard and we'll see updates coming in as trades happen on Hyperliquid.
>
> Notice the block number incrementing - that's the Hyperliquid block we're processing.
>
> You can toggle the sidebar between fees and volume to see different rankings.
>
> The theme toggle switches between dark and light mode."

**Demo:**
- Show dashboard running
- Point out real-time updates
- Toggle fees/volume
- Toggle theme
- Show WebSocket messages in browser dev tools

---

### 7. Customization Ideas (1-2 minutes)

**Script:**
> "Here are some ways you could extend this:
> - Add more charts like a pie chart for market share
> - Filter by specific builders or time ranges
> - Add historical data with a database
> - Deploy it publicly for others to use
> - Add alerts when certain builders exceed thresholds"

---

### 8. Conclusion (1 minute)

**Script:**
> "That's it! You now have a working real-time dashboard for Hyperliquid builder analytics.
>
> The key takeaways are:
> - gRPC streaming is perfect for real-time blockchain data
> - WebSockets let you push updates to the frontend efficiently
> - React hooks make state management clean
>
> Check out the GitHub repo linked below, and let me know in the comments what you'd like to see next.
>
> Thanks for watching!"

---

## Recording Tips

### Screen Setup
- Use 1920x1080 resolution
- Increase terminal/editor font size to 16-18pt
- Use a clean, minimal editor theme
- Hide unnecessary UI elements

### Code Walkthrough
- Collapse unrelated code sections
- Highlight important lines
- Add visual markers or annotations
- Zoom in on key sections

### Demo Recording
- Have the dashboard already running
- Prepare the browser with dev tools ready
- Clear any personal data from screen
- Test audio levels before recording

### Post-Production
- Add chapter markers for easy navigation
- Include code snippets as overlays
- Add captions for accessibility
- Include links to repo in description

---

## Video Description Template

```
Build a real-time dashboard for tracking Hyperliquid builder fees and trading volume using gRPC streaming.

This tutorial covers:
- Setting up a Python FastAPI backend with gRPC client
- Processing live blockchain data streams
- Broadcasting updates via WebSocket
- Building a React frontend with live updates
- TypeScript type safety throughout

Technologies used:
- Python 3.11+ / FastAPI / grpcio
- React 18 / TypeScript / Vite
- Hyperliquid L1 gRPC API
- WebSocket for real-time updates

Links:
- GitHub Repo: [your-repo-url]
- Dwellir (gRPC Provider): https://dwellir.com
- Hyperliquid: https://hyperliquid.xyz

Chapters:
0:00 Introduction
1:30 Architecture Overview
4:00 Project Setup
7:00 Backend Deep Dive
14:00 Frontend Deep Dive
19:00 Live Demo
22:00 Customization Ideas
23:30 Conclusion

#blockchain #python #react #grpc #hyperliquid #trading #dashboard
```

---

## Thumbnail Ideas

- Split screen: Code on left, dashboard on right
- "LIVE DATA" badge with streaming animation
- Hyperliquid + Dwellir logos
- Chart/graph visual with upward trend
