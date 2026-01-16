"""
gRPC client for streaming Hyperliquid L1 fill events.

This module provides an async client that connects to the Hyperliquid gRPC
gateway and streams real-time trade fills. Each fill contains information
about trades executed on the Hyperliquid DEX, including builder fees.

Usage:
    client = HyperliquidGrpcClient(config)
    await client.connect()
    async for block_fills in client.stream_fills():
        process(block_fills)
"""

import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, Callable

import grpc

import hyperliquid_pb2 as pb
import hyperliquid_pb2_grpc as pb_grpc
from config import Config

logger = logging.getLogger(__name__)

# Large message size to handle blocks with many fills
MAX_MESSAGE_SIZE = 150 * 1024 * 1024  # 150MB


class HyperliquidGrpcClient:
    """
    Async gRPC client for streaming Hyperliquid L1 fills.

    Maintains a persistent connection to the gRPC endpoint and yields
    fill data as it arrives from the Hyperliquid blockchain.
    """

    def __init__(self, config: Config):
        self.config = config
        self._channel: grpc.aio.Channel | None = None
        self._stub: pb_grpc.HyperliquidL1GatewayStub | None = None

    async def connect(self) -> None:
        """Establish secure gRPC connection to Hyperliquid gateway."""
        credentials = grpc.ssl_channel_credentials()
        options = [("grpc.max_receive_message_length", MAX_MESSAGE_SIZE)]

        self._channel = grpc.aio.secure_channel(
            self.config.grpc_endpoint,
            credentials,
            options=options,
        )
        self._stub = pb_grpc.HyperliquidL1GatewayStub(self._channel)
        logger.info(f"Connected to {self.config.grpc_endpoint}")

    async def disconnect(self) -> None:
        """Close gRPC connection and clean up resources."""
        if self._channel:
            await self._channel.close()
            self._channel = None
            self._stub = None
            logger.info("Disconnected from gRPC endpoint")

    async def stream_fills(
        self,
        on_fills: Callable[[dict], None] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Stream fill events from Hyperliquid L1.

        Each yielded block contains fill events with structure:
        {
            "block_number": 12345,
            "block_time": "2024-01-01T00:00:00Z",
            "events": [
                [user_address, {fill_data}],
                ...
            ]
        }

        Args:
            on_fills: Optional callback invoked for each block (deprecated)

        Yields:
            Block fill data dictionaries
        """
        if not self._stub:
            raise RuntimeError("Client not connected. Call connect() first.")

        # Add API key to request metadata if configured
        metadata = [("x-api-key", self.config.api_key)] if self.config.api_key else None

        logger.info("Starting fills stream...")

        try:
            async for response in self._stub.StreamFills(pb.Position(), metadata=metadata):
                try:
                    block_fills = json.loads(response.data.decode("utf-8"))
                    if on_fills:
                        on_fills(block_fills)
                    yield block_fills
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse fill data: {e}")
                    continue

        except grpc.RpcError as e:
            logger.error(f"gRPC error: {e.code()}: {e.details()}")
            raise


def parse_block_time(block_fills: dict) -> datetime | None:
    """
    Extract block timestamp from fill data.

    Handles multiple timestamp formats:
    - ISO format string in "block_time" field
    - Unix milliseconds in "time" field

    Returns:
        UTC datetime or None if parsing fails
    """
    # Try ISO format first (e.g., "2024-01-01T00:00:00Z")
    block_time_str = block_fills.get("block_time")
    if block_time_str and isinstance(block_time_str, str):
        try:
            dt = datetime.fromisoformat(block_time_str.replace("Z", "+00:00"))
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        except ValueError:
            pass

    # Fall back to Unix milliseconds
    block_time_ms = block_fills.get("time")
    if isinstance(block_time_ms, (int, float)):
        try:
            return datetime.fromtimestamp(block_time_ms / 1000, tz=timezone.utc)
        except (ValueError, OSError):
            pass

    return None
