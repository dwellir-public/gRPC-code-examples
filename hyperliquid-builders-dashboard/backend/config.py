"""
Configuration module for Hyperliquid Builders Dashboard.

This module handles:
- Loading environment variables from .env files
- Server configuration (host, port, API keys)
- Builder metadata from builders.json (names, colors, logos)
"""

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Default Dwellir gRPC endpoint for Hyperliquid mainnet
DEFAULT_GRPC_ENDPOINT = "api-hyperliquid-mainnet-grpc.n.dwellir.com:443"


@dataclass
class Config:
    """
    Application configuration loaded from environment variables.

    Environment variables:
        GRPC_ENDPOINT: Hyperliquid gRPC endpoint (default: Dwellir mainnet)
        API_KEY: Optional API key for authenticated requests
        HOST: Server bind address (default: 0.0.0.0)
        PORT: Server port (default: 8000)
    """

    grpc_endpoint: str
    api_key: str | None
    host: str
    port: int

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        endpoint = os.getenv("GRPC_ENDPOINT", DEFAULT_GRPC_ENDPOINT)

        # Normalize endpoint: strip protocol prefix and ensure port is present
        endpoint = endpoint.replace("https://", "").replace("http://", "")
        if "/:" in endpoint:
            endpoint = endpoint.replace("/:", ":")
        if ":" not in endpoint:
            endpoint = f"{endpoint}:443"

        return cls(
            grpc_endpoint=endpoint,
            api_key=os.getenv("API_KEY"),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
        )


@dataclass
class BuilderInfo:
    """
    Metadata for a known builder.

    Attributes:
        name: Display name (e.g., "Rage Trade")
        color: Hex color for charts (e.g., "#3B82F6")
        logo: URL to builder's logo image
    """

    name: str
    color: str
    logo: str


# Default styling for unknown builders
DEFAULT_OTHER = BuilderInfo(name="Other", color="#4B5563", logo="")


def load_builders_config() -> tuple[dict[str, BuilderInfo], BuilderInfo]:
    """
    Load builder metadata from builders.json.

    The JSON file maps builder addresses to their display info:
    {
        "builders": {
            "0x123...": {"name": "Builder Name", "color": "#hex", "logo": "url"}
        },
        "other": {"name": "Other", "color": "#hex"}
    }

    Returns:
        Tuple of (address -> BuilderInfo dict, "Other" category config)
    """
    builders_file = Path(__file__).parent / "builders.json"

    if not builders_file.exists():
        logger.warning(f"builders.json not found at {builders_file}")
        return {}, DEFAULT_OTHER

    try:
        with open(builders_file) as f:
            data = json.load(f)

        # Parse each builder entry, normalizing addresses to lowercase
        builders = {}
        for addr, info in data.get("builders", {}).items():
            if isinstance(info, dict):
                builders[addr.lower()] = BuilderInfo(
                    name=info.get("name", addr[:10]),
                    color=info.get("color", "#6B7280"),
                    logo=info.get("logo", ""),
                )

        # Parse "Other" category config
        other_data = data.get("other", {})
        other = BuilderInfo(
            name=other_data.get("name", "Other"),
            color=other_data.get("color", "#4B5563"),
            logo=other_data.get("logo", ""),
        )

        logger.info(f"Loaded {len(builders)} known builders from config")
        return builders, other

    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to parse builders.json: {e}")
        return {}, DEFAULT_OTHER


# Load builder config at module import time
BUILDERS, OTHER_BUILDER = load_builders_config()


def is_known_builder(address: str) -> bool:
    """Check if a builder address is in our known builders list."""
    return address.lower() in BUILDERS
