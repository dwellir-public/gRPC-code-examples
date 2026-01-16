# Hyperliquid Builders Dashboard

A real-time dashboard that tracks builder fees and trading volume on Hyperliquid L1 using gRPC streaming.

## Overview

This dashboard connects to Hyperliquid's gRPC API to stream live fill events and aggregates statistics per builder. It displays:

- **Total Revenue**: Sum of all builder fees (in USD stablecoins)
- **Total Volume**: Cumulative trading volume
- **Unique Users**: Count of distinct wallet addresses
- **Builder Rankings**: Sortable by fees or volume

## Architecture

```
┌─────────────────┐     gRPC Stream      ┌─────────────────┐
│   Hyperliquid   │ ──────────────────▶  │  Python Backend │
│   L1 Gateway    │     Fill Events      │    (FastAPI)    │
└─────────────────┘                      └────────┬────────┘
                                                  │
                                           WebSocket
                                                  │
                                         ┌────────▼────────┐
                                         │  React Frontend │
                                         │    (Vite)       │
                                         └─────────────────┘
```

### Backend (`/backend`)

- **FastAPI** server with WebSocket support
- **gRPC client** connecting to Hyperliquid L1 Gateway
- **StatsAggregator** for real-time statistics processing
- Filters fees to only include USD stablecoins (USDC, USDH, etc.)

### Frontend (`/frontend`)

- **React 18** with TypeScript
- **Vite** for fast development
- Real-time updates via WebSocket
- Dark/light theme support

## Prerequisites

- Python 3.11+
- Node.js 18+
- A Dwellir API key (optional, for higher rate limits)

## Quick Start

### 1. Clone and Setup

```bash
cd hyperliquid-builders-dashboard
```

### 2. Configure Environment

Create a `.env` file in the `/backend` directory:

```env
# Optional: Use your own gRPC endpoint
GRPC_ENDPOINT=api-hyperliquid-mainnet-grpc.n.dwellir.com:443

# Optional: API key for authenticated requests
API_KEY=your-api-key-here

# Server configuration
HOST=0.0.0.0
PORT=8000
```

### 3. Install Dependencies

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

### 4. Run the Application

**Option A: Use the start script (recommended)**
```bash
./start.sh
```

**Option B: Run manually**

Terminal 1 - Backend:
```bash
cd backend
source venv/bin/activate
python main.py
```

Terminal 2 - Frontend:
```bash
cd frontend
npm run dev
```

### 5. Access the Dashboard

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Configuration

### Builder Configuration (`builders.json`)

Add known builders with custom names, colors, and logos:

```json
{
  "builders": {
    "0x1234...": {
      "name": "My Builder",
      "color": "#3B82F6",
      "logo": "https://example.com/logo.png"
    }
  },
  "other": {
    "name": "Other",
    "color": "#4B5563"
  }
}
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GRPC_ENDPOINT` | Hyperliquid gRPC endpoint | `api-hyperliquid-mainnet-grpc.n.dwellir.com:443` |
| `API_KEY` | Optional API key for auth | None |
| `HOST` | Server bind address | `0.0.0.0` |
| `PORT` | Server port | `8000` |

## API Endpoints

### REST

- `GET /` - Health check
- `GET /api/stats` - Detailed builder statistics
- `GET /api/chart` - Aggregated chart data

### WebSocket

- `WS /ws` - Real-time updates stream

Message types:
- `initial_stats` - Sent on connection with current state
- `stats_update` - Sent when new fills are processed

## Development

### Backend

```bash
cd backend
source venv/bin/activate
python main.py  # Runs with auto-reload
```

### Frontend

```bash
cd frontend
npm run dev     # Development server
npm run build   # Production build
npm run preview # Preview production build
```

## Fee Token Handling

The dashboard only counts fees denominated in USD stablecoins:
- USDC
- USDH
- Any token starting with "USD"

Non-USD fees are logged but excluded from totals to ensure accurate USD reporting.

## Project Structure

```
hyperliquid-builders-dashboard/
├── backend/
│   ├── main.py              # FastAPI server entry point
│   ├── grpc_client.py       # Hyperliquid gRPC client
│   ├── builder_stats.py     # Statistics aggregation
│   ├── config.py            # Configuration management
│   ├── builders.json        # Known builder metadata
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Main application component
│   │   ├── components/      # React components
│   │   ├── hooks/           # Custom React hooks
│   │   └── types.ts         # TypeScript definitions
│   └── package.json         # Node dependencies
├── start.sh                 # Convenience script to run both
└── README.md                # This file
```

## Powered By

- [Dwellir](https://dwellir.com) - Blockchain infrastructure
- [Hyperliquid](https://hyperliquid.xyz) - High-performance DEX

## License

MIT
