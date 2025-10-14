# Hyperliquid Liquidation Tracker 🔥

A beautiful, real-time liquidation tracker for Hyperliquid DEX. Monitor liquidation events as they happen with a modern web3-style interface.

![Screenshot](https://img.shields.io/badge/status-live-success)
![Python](https://img.shields.io/badge/python-3.8+-blue)
![React](https://img.shields.io/badge/react-18.2-blue)

## Features ✨

- **Real-time Liquidation Monitoring**: Stream liquidation events live from Hyperliquid
- **Beautiful Web3 UI**: Modern, gradient-based interface with smooth animations
- **Comprehensive Stats**: Track total liquidations, volume, P&L, and average position sizes
- **Detailed Event Cards**: View all liquidation details including user, coin, price, size, fees, and more
- **WebSocket Architecture**: Efficient real-time communication between backend and frontend
- **Auto-Reconnect**: Automatic reconnection handling for resilient streaming

## Architecture 🏗️

### Backend (Python)
- Connects to Hyperliquid gRPC API
- Filters block fills for liquidation events
- Broadcasts liquidations to frontend via WebSocket
- Built with `aiohttp` and `grpcio`

### Frontend (React + Vite)
- Modern React application with hooks
- Real-time WebSocket connection
- Responsive design with CSS animations
- Stats dashboard and liquidation feed

## Prerequisites 📋

- Python 3.8+
- Node.js 16+
- Access to Hyperliquid gRPC endpoint and API key

## Installation 🚀

### 1. Clone the repository

```bash
git clone <repository-url>
cd hyperliquid-liquidation-bot
```

### 2. Set up the Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your HYPERLIQUID_ENDPOINT and API_KEY
```

### 3. Set up the Frontend

```bash
cd frontend

# Install dependencies
npm install

# Configure environment (optional)
cp .env.example .env
# Edit .env to change WebSocket URL if needed
```

## Usage 🎯

### Start the Backend

```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python server.py
```

The WebSocket server will start on `http://localhost:8080`

### Start the Frontend

In a new terminal:

```bash
cd frontend
npm run dev
```

The frontend will start on `http://localhost:3000`

### Access the Application

Open your browser and navigate to `http://localhost:3000`

You'll see:
- **Connection Status**: Live indicator showing connection to backend
- **Stats Panel**: Real-time statistics of liquidation events
- **Liquidation Feed**: Cards displaying each liquidation event with full details

## Environment Variables 🔐

### Backend (.env)

```env
HYPERLIQUID_ENDPOINT=your-grpc-endpoint:443
API_KEY=your-api-key
PORT=8080  # Optional, defaults to 8080
```

### Frontend (.env)

```env
VITE_WS_URL=ws://localhost:8080/ws
```

## Project Structure 📁

```
hyperliquid-liquidation-bot/
├── backend/
│   ├── server.py              # WebSocket server and gRPC client
│   ├── hyperliquid_pb2.py     # Protobuf definitions
│   ├── hyperliquid_pb2_grpc.py
│   ├── requirements.txt
│   ├── .env.example
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── LiquidationCard.jsx
│   │   │   ├── LiquidationCard.css
│   │   │   ├── StatsPanel.jsx
│   │   │   └── StatsPanel.css
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   ├── .env.example
│   └── .env
├── .gitignore
└── README.md
```

## Liquidation Data Structure 📊

Each liquidation event contains:

```json
{
  "userAddress": "0x...",
  "coin": "CAKE",
  "price": "3.4427",
  "size": "270.0",
  "side": "A",
  "timestamp": 1760108977093,
  "startPosition": "2522.7",
  "direction": "Close Long",
  "closedPnl": "-35.1567",
  "hash": "0x...",
  "fee": "0.418288",
  "feeToken": "USDC",
  "liquidation": {
    "liquidatedUser": "0x...",
    "markPx": "3.4431",
    "method": "market"
  },
  "crossed": true
}
```

## Development 🛠️

### Backend Development

The backend uses Python's `asyncio` for concurrent operations:
- gRPC stream runs in background task
- WebSocket connections handled asynchronously
- Automatic reconnection on stream errors

### Frontend Development

Built with modern React patterns:
- Functional components with hooks
- Real-time state management
- CSS animations and transitions
- Responsive design

## Troubleshooting 🔧

### Backend not connecting to Hyperliquid

- Verify your `HYPERLIQUID_ENDPOINT` and `API_KEY` in `.env`
- Check network connectivity
- Ensure gRPC endpoint is accessible

### Frontend not connecting to backend

- Ensure backend is running on port 8080
- Check CORS settings if needed
- Verify WebSocket URL in frontend `.env`

### No liquidations appearing

- Liquidations only appear when they occur on-chain
- The interface shows "Waiting for liquidations..." until events arrive
- Check backend console for connection status

## Tech Stack 💻

**Backend:**
- Python 3.8+
- gRPC / Protocol Buffers
- aiohttp (WebSocket server)
- python-dotenv

**Frontend:**
- React 18
- Vite
- Lucide React (icons)
- Modern CSS with animations

## License 📄

MIT License - feel free to use this project for your own purposes.

## Contributing 🤝

Contributions are welcome! Please feel free to submit a Pull Request.

---

Built with 🔥 for the Hyperliquid community
