"""
Hyperliquid Builders Dashboard - Backend Server

FastAPI server that provides real-time builder statistics from Hyperliquid L1.

Architecture:
    1. gRPC client connects to Hyperliquid and streams fill events
    2. StatsAggregator processes fills and maintains running totals
    3. WebSocket broadcasts updates to connected frontend clients
    4. REST endpoints provide initial data and health checks

Run with: python main.py
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from builder_stats import StatsAggregator
from config import Config
from grpc_client import HyperliquidGrpcClient, parse_block_time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.

    Handles connection lifecycle and broadcasts stats updates
    to all connected frontend clients.
    """

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected (total: {len(self.active_connections)})")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a disconnected client."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Client disconnected (total: {len(self.active_connections)})")

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Send a message to all connected clients."""
        if not self.active_connections:
            return

        # Track failed connections for cleanup
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # Clean up dead connections
        for conn in disconnected:
            self.disconnect(conn)


# =============================================================================
# Global Application State
# =============================================================================

config = Config.from_env()
grpc_client = HyperliquidGrpcClient(config)
stats_aggregator = StatsAggregator()
connection_manager = ConnectionManager()

# Background task handle for graceful shutdown
stream_task: asyncio.Task | None = None


# =============================================================================
# gRPC Stream Processing
# =============================================================================

async def process_fills_stream() -> None:
    """
    Background task that continuously processes the gRPC fills stream.

    Connects to Hyperliquid, processes incoming fill events, updates
    statistics, and broadcasts changes to WebSocket clients.
    Automatically reconnects on connection failures.
    """
    while True:
        try:
            await grpc_client.connect()

            async for block_fills in grpc_client.stream_fills():
                block_time = parse_block_time(block_fills)
                events = block_fills.get("events", [])
                updated_builders: set[str] = set()

                # Process each fill event in the block
                for event in events:
                    # Events are [user_address, fill_data] pairs
                    if not isinstance(event, list) or len(event) < 2:
                        continue

                    user_address = event[0] if isinstance(event[0], str) else None
                    fill_data = event[1]
                    if not isinstance(fill_data, dict):
                        continue

                    builder = stats_aggregator.process_fill(fill_data, user_address, block_time)
                    if builder:
                        updated_builders.add(builder)

                # Broadcast update if any builders were affected
                if updated_builders:
                    await connection_manager.broadcast({
                        "type": "stats_update",
                        "data": stats_aggregator.get_all_stats(),
                        "chartData": stats_aggregator.get_chart_data(),
                        "blockNumber": block_fills.get("block_number"),
                    })

        except Exception as e:
            logger.error(f"Stream error: {e}")
            await grpc_client.disconnect()
            logger.info("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)


# =============================================================================
# Application Lifecycle
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan handler for startup/shutdown.

    On startup: Launches background gRPC stream processor
    On shutdown: Cancels stream task and disconnects cleanly
    """
    global stream_task

    logger.info("Starting Hyperliquid Builders Dashboard")
    logger.info(f"gRPC endpoint: {config.grpc_endpoint}")

    # Start background stream processing
    stream_task = asyncio.create_task(process_fills_stream())

    yield  # Application runs here

    # Graceful shutdown
    logger.info("Shutting down...")
    if stream_task:
        stream_task.cancel()
        try:
            await stream_task
        except asyncio.CancelledError:
            pass
    await grpc_client.disconnect()


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="Hyperliquid Builders Dashboard",
    description="Real-time builder statistics from Hyperliquid L1",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# REST Endpoints
# =============================================================================

@app.get("/")
async def root() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "hyperliquid-builders-dashboard"}


@app.get("/api/stats")
async def get_stats() -> dict[str, Any]:
    """Get detailed statistics for all builders."""
    return {"data": stats_aggregator.get_all_stats()}


@app.get("/api/chart")
async def get_chart_data() -> dict[str, Any]:
    """Get aggregated chart data (known builders + Other category)."""
    return stats_aggregator.get_chart_data()


# =============================================================================
# WebSocket Endpoint
# =============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time stats updates.

    On connect: Sends current stats immediately
    Ongoing: Receives broadcast updates when new fills arrive
    """
    await connection_manager.connect(websocket)

    # Send current state immediately on connect
    await websocket.send_json({
        "type": "initial_stats",
        "data": stats_aggregator.get_all_stats(),
        "chartData": stats_aggregator.get_chart_data(),
    })

    # Keep connection alive and handle disconnect
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        reload=True,
    )
