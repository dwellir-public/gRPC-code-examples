"""
Builder statistics aggregation module.

This module processes fill events from the Hyperliquid gRPC stream and
aggregates statistics per builder, including:
- Trade count and volume
- Builder fees (revenue) in USD
- Unique users per builder

The StatsAggregator is thread-safe and can be accessed from multiple
async tasks simultaneously.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any

from config import BUILDERS, OTHER_BUILDER, is_known_builder

logger = logging.getLogger(__name__)


@dataclass
class BuilderStats:
    """
    Accumulated statistics for a single builder address.

    Tracks volume, fees, and user counts since the server started.
    """

    address: str          # Builder's Ethereum address (lowercase)
    name: str             # Display name from config or truncated address
    color: str            # Chart color (hex)
    logo: str             # Logo URL
    is_known: bool        # True if in builders.json
    trade_count: int = 0
    total_volume_usd: float = 0.0
    total_fees_usd: float = 0.0
    unique_users: set = field(default_factory=set)  # Set of user addresses
    last_active: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dictionary for API responses."""
        return {
            "address": self.address,
            "name": self.name,
            "color": self.color,
            "logo": self.logo,
            "isKnown": self.is_known,
            "tradeCount": self.trade_count,
            "totalVolumeUsd": round(self.total_volume_usd, 2),
            "totalFeesUsd": round(self.total_fees_usd, 6),
            "uniqueUsers": len(self.unique_users),
            "lastActive": self.last_active.isoformat() if self.last_active else None,
        }


@dataclass
class StatsAggregator:
    """
    Thread-safe aggregator for builder statistics.

    Processes incoming fill events and maintains running totals
    for each builder. Data is served to the frontend via REST/WebSocket.
    """

    builders: dict[str, BuilderStats] = field(default_factory=dict)
    all_users: set = field(default_factory=set)  # Global unique user set
    started_at: datetime = field(default_factory=lambda: datetime.utcnow())  # When streaming started
    _lock: Lock = field(default_factory=Lock)

    def process_fill(
        self,
        fill_data: dict[str, Any],
        user_address: str | None = None,
        block_time: datetime | None = None,
    ) -> str | None:
        """
        Process a single fill event and update builder stats.

        Fill data structure (from Hyperliquid):
            {
                "builder": "0x...",      # Builder address
                "px": "1234.56",         # Price
                "sz": "0.1",             # Size
                "builderFee": "0.05",    # Fee amount
                "feeToken": "USDC",      # Fee denomination
                "coin": "ETH",           # Trading pair
                ...
            }

        Returns:
            Builder address if processed, None if skipped
        """
        builder_address = fill_data.get("builder")
        if not builder_address:
            return None

        builder_address = builder_address.lower()

        # Parse numeric fields from fill data
        try:
            price = float(fill_data.get("px", 0))
            size = float(fill_data.get("sz", 0))
            builder_fee = float(fill_data.get("builderFee", 0))
        except (ValueError, TypeError):
            return None

        # Only count fees in USD stablecoins (USDC, USDH, etc.)
        # Non-USD fees are logged and excluded from totals
        fee_token = fill_data.get("feeToken") or ""
        if not fee_token.startswith("USD"):
            if builder_fee > 0:
                logger.warning(
                    f"Skipping non-USD fee: {builder_fee} {fee_token} "
                    f"(builder={builder_address[:10]}...)"
                )
            builder_fee = 0.0

        volume_usd = price * size
        timestamp = block_time or datetime.utcnow()

        with self._lock:
            # Create new builder entry if first time seeing this address
            if builder_address not in self.builders:
                self.builders[builder_address] = self._create_builder_stats(builder_address)

            # Update running totals
            stats = self.builders[builder_address]
            stats.trade_count += 1
            stats.total_volume_usd += volume_usd
            stats.total_fees_usd += builder_fee
            stats.last_active = timestamp

            # Track unique users
            if user_address:
                user_addr_lower = user_address.lower()
                stats.unique_users.add(user_addr_lower)
                self.all_users.add(user_addr_lower)

        return builder_address

    def _create_builder_stats(self, address: str) -> BuilderStats:
        """Create a new BuilderStats entry for an address."""
        known = is_known_builder(address)
        if known:
            info = BUILDERS[address]
            return BuilderStats(
                address=address,
                name=info.name,
                color=info.color,
                logo=info.logo,
                is_known=True,
            )
        else:
            return BuilderStats(
                address=address,
                name=self._truncate_address(address),
                color=OTHER_BUILDER.color,
                logo=OTHER_BUILDER.logo,
                is_known=False,
            )

    def get_all_stats(self) -> list[dict[str, Any]]:
        """Get detailed statistics for all builders (used by table view)."""
        with self._lock:
            return [stats.to_dict() for stats in self.builders.values()]

    def get_chart_data(self) -> dict[str, Any]:
        """
        Get aggregated chart data for the dashboard.

        Groups known builders individually and consolidates all unknown
        builders into an "Other" category. Returns data optimized for
        chart rendering.

        Returns:
            {
                "builders": [{name, color, logo, volume, trades, fees, users}, ...],
                "totals": {volume, fees, users, avgRevenuePerUser}
            }
        """
        with self._lock:
            known_builders = []
            # Accumulators for unknown builders
            other_volume = 0.0
            other_trades = 0
            other_fees = 0.0
            other_users: set = set()

            total_volume = 0.0
            total_fees = 0.0

            # Separate known vs unknown builders
            for stats in self.builders.values():
                total_volume += stats.total_volume_usd
                total_fees += stats.total_fees_usd

                if stats.is_known:
                    known_builders.append({
                        "name": stats.name,
                        "color": stats.color,
                        "logo": stats.logo,
                        "volume": round(stats.total_volume_usd, 2),
                        "trades": stats.trade_count,
                        "fees": round(stats.total_fees_usd, 6),
                        "users": len(stats.unique_users),
                    })
                else:
                    # Aggregate unknown builders into "Other"
                    other_volume += stats.total_volume_usd
                    other_trades += stats.trade_count
                    other_fees += stats.total_fees_usd
                    other_users.update(stats.unique_users)

            # Sort by fees (revenue) descending
            known_builders.sort(key=lambda x: x["fees"], reverse=True)

            # Append "Other" category at the end if any unknown builder activity
            if other_trades > 0:
                known_builders.append({
                    "name": OTHER_BUILDER.name,
                    "color": OTHER_BUILDER.color,
                    "logo": OTHER_BUILDER.logo,
                    "volume": round(other_volume, 2),
                    "trades": other_trades,
                    "fees": round(other_fees, 6),
                    "users": len(other_users),
                })

            total_users = len(self.all_users)

            return {
                "builders": known_builders,
                "totals": {
                    "volume": round(total_volume, 2),
                    "fees": round(total_fees, 6),
                    "users": total_users,
                    "avgRevenuePerUser": round(total_fees / total_users, 6) if total_users else 0,
                },
                "startedAt": self.started_at.isoformat() + "Z",
            }

    @staticmethod
    def _truncate_address(address: str) -> str:
        """Format address for display: 0x1234...5678"""
        if len(address) > 10:
            return f"{address[:6]}...{address[-4:]}"
        return address
