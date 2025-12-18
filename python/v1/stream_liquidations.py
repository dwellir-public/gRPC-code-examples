#!/usr/bin/env python3
"""
Stream Liquidations Example - Hyperliquid gRPC API v1

This example demonstrates how to stream and detect liquidation events from Hyperliquid L1.
Liquidations are extracted from the fills stream by detecting fills that have a 'liquidation' field.

You can start streaming from:
  - Latest: No arguments (default)
  - Historical by timestamp: --timestamp <ms_since_epoch>
  - Historical by relative time: --minutes-ago <minutes>

Verbosity levels:
  (default)  - Liquidation events with basic info
  -v         - Add more details (direction, closed PnL)
  -vv        - Add user addresses and liquidation info
  -vvv       - Add debug info for all fills

Usage:
  python stream_liquidations.py                    # Stream from latest
  python stream_liquidations.py --minutes-ago 60  # Look back 1 hour for liquidations
  python stream_liquidations.py -v                 # More details

Environment variables (or .env file):
  HYPERLIQUID_ENDPOINT - gRPC endpoint (default: api-hyperliquid-mainnet-grpc.n.dwellir.com:443)
  API_KEY - API key for authentication (optional)
"""

import argparse
import grpc
import json
import signal
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from dotenv import load_dotenv

import hyperliquid_pb2 as pb
import hyperliquid_pb2_grpc as pb_grpc

# Load environment variables from .env file
load_dotenv()

DEFAULT_ENDPOINT = "api-hyperliquid-mainnet-grpc.n.dwellir.com:443"
MAX_MESSAGE_SIZE = 150 * 1024 * 1024  # 150MB


def parse_args():
    parser = argparse.ArgumentParser(
        description="Stream liquidation events from Hyperliquid L1 gRPC API (v1)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Stream from latest
  %(prog)s --minutes-ago 60         # Look back 1 hour
  %(prog)s -m 60                    # Short form: 1 hour ago
  %(prog)s --timestamp 1702800000000  # From specific timestamp (ms)
  %(prog)s --count 10               # Stop after 10 liquidations
  %(prog)s -v                       # Show more details
  %(prog)s -vv                      # Show user addresses
  %(prog)s -vvv                     # Debug mode (show all fills)
        """
    )

    position_group = parser.add_mutually_exclusive_group()
    position_group.add_argument(
        "-t", "--timestamp",
        type=int,
        help="Start streaming from specific timestamp (milliseconds since epoch)"
    )
    position_group.add_argument(
        "-m", "--minutes-ago",
        type=float,
        help="Start streaming from X minutes ago"
    )

    parser.add_argument(
        "-c", "--count",
        type=int,
        default=0,
        help="Stop after N liquidations (0 = unlimited, default: 0)"
    )

    parser.add_argument(
        "--stats-interval",
        type=int,
        default=100,
        help="Print stats every N blocks (default: 100)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (-v, -vv, -vvv)"
    )

    return parser.parse_args()


def extract_liquidations(data: bytes, verbosity: int) -> list:
    """Extract liquidation events from fills data."""
    liquidations = []

    try:
        fills_data = json.loads(data.decode("utf-8"))

        # Debug: show structure at highest verbosity
        if verbosity >= 3:
            print(f"\n[DEBUG] Fills data type: {type(fills_data).__name__}")
            if isinstance(fills_data, dict):
                print(f"[DEBUG] Keys: {list(fills_data.keys())}")

        # Handle different data structures
        # Structure 1: {"block_number": ..., "events": [...]} or {"height": ..., "fills": [...]}
        if isinstance(fills_data, dict):
            events = fills_data.get("events") or fills_data.get("fills", [])
            block_number = fills_data.get("block_number") or fills_data.get("height")
            block_time = fills_data.get("block_time") or fills_data.get("time")

            for event in events:
                if not isinstance(event, list) or len(event) < 2:
                    # Try treating as dict directly
                    if isinstance(event, dict) and "liquidation" in event:
                        liq = extract_single_liquidation(
                            event.get("user", ""), event, block_number, block_time
                        )
                        if liq:
                            liquidations.append(liq)
                    continue

                user_address, fill_data = event[0], event[1]

                if not isinstance(fill_data, dict):
                    continue

                # Check for liquidation
                if "liquidation" in fill_data:
                    liq = extract_single_liquidation(
                        user_address, fill_data, block_number, block_time
                    )
                    if liq:
                        liquidations.append(liq)

        # Structure 2: [user_address, fill_data] (single fill)
        elif isinstance(fills_data, list) and len(fills_data) == 2:
            user_address, fill_data = fills_data

            if isinstance(fill_data, dict) and "liquidation" in fill_data:
                liq = extract_single_liquidation(user_address, fill_data)
                if liq:
                    liquidations.append(liq)

    except json.JSONDecodeError as e:
        if verbosity >= 2:
            print(f"[DEBUG] JSON decode error: {e}")
    except Exception as e:
        if verbosity >= 2:
            print(f"[DEBUG] Error extracting liquidations: {e}")

    return liquidations


def extract_single_liquidation(user_address: str, fill_data: dict,
                                block_number: int = None, block_time = None) -> dict:
    """Extract a single liquidation event from fill data."""
    liquidation_info = fill_data.get("liquidation", {})
    liquidated_user = liquidation_info.get("liquidatedUser", "")
    direction = fill_data.get("dir", "")

    # Only include closing positions where user matches liquidated user
    is_closing = "close" in direction.lower() if direction else False
    is_liquidated_user = user_address.lower() == liquidated_user.lower() if liquidated_user else False

    if is_closing and is_liquidated_user:
        return {
            "user_address": user_address,
            "coin": fill_data.get("coin", "?"),
            "price": fill_data.get("px", "?"),
            "size": fill_data.get("sz", "?"),
            "side": fill_data.get("side", "?"),
            "timestamp": fill_data.get("time"),
            "direction": direction,
            "closed_pnl": fill_data.get("closedPnl", "0"),
            "liquidation_info": liquidation_info,
            "block_number": block_number,
            "block_time": block_time,
        }

    return None


def format_liquidation(liq: dict, verbosity: int, liq_num: int) -> str:
    """Format a liquidation event for display."""
    lines = []

    # Header
    coin = liq["coin"]
    size = liq["size"]
    price = liq["price"]
    side = liq["side"]
    side_str = "LONG" if side in ("B", "BUY") else "SHORT" if side in ("A", "SELL") else side

    lines.append(f"🔥 LIQUIDATION #{liq_num}: {coin} {side_str}")
    lines.append(f"   Size: {size} @ ${price}")

    # Additional details at verbosity >= 1
    if verbosity >= 1:
        closed_pnl = liq["closed_pnl"]
        direction = liq["direction"]
        lines.append(f"   P&L: ${closed_pnl} | {direction}")

        if liq["block_number"]:
            block_num = liq["block_number"]
            if isinstance(block_num, int):
                lines.append(f"   Block: #{block_num:,}")
            else:
                lines.append(f"   Block: #{block_num}")

    # User address at verbosity >= 2
    if verbosity >= 2:
        addr = liq["user_address"]
        if addr:
            lines.append(f"   User: {addr[:10]}...{addr[-8:]}")

        liq_info = liq["liquidation_info"]
        if liq_info:
            mark_px = liq_info.get("markPx", "?")
            liquidator = liq_info.get("liquidator", "")
            if liquidator:
                lines.append(f"   Mark: ${mark_px} | Liquidator: {liquidator[:10]}...")

    return "\n".join(lines)


def main():
    args = parse_args()

    endpoint = os.getenv("HYPERLIQUID_ENDPOINT", DEFAULT_ENDPOINT)
    if ":" not in endpoint:
        endpoint = endpoint + ":443"

    api_key = os.getenv("API_KEY")

    print("Hyperliquid gRPC - Stream Liquidations Example (v1 API)")
    print("========================================================")
    print(f"Endpoint: {endpoint}")
    if api_key:
        print("Using API key authentication")
    print(f"Verbosity: {args.verbose}")
    if args.count > 0:
        print(f"Will stop after {args.count} liquidations")

    # Create SSL credentials
    credentials = grpc.ssl_channel_credentials()

    # Create channel with options
    options = [
        ("grpc.max_receive_message_length", MAX_MESSAGE_SIZE),
    ]

    # Prepare metadata with API key if provided
    metadata = [("x-api-key", api_key)] if api_key else None

    print("Connecting to gRPC server...")
    with grpc.secure_channel(endpoint, credentials, options=options) as channel:
        client = pb_grpc.HyperLiquidL1GatewayStub(channel)
        print("Connected successfully!\n")

        # Create request based on arguments
        if args.timestamp:
            request = pb.Timestamp(timestamp=args.timestamp)
            ts_datetime = datetime.fromtimestamp(args.timestamp / 1000, tz=timezone.utc)
            print(f"Starting from timestamp {args.timestamp}")
            print(f"  ({ts_datetime.strftime('%Y-%m-%d %H:%M:%S UTC')})")
        elif args.minutes_ago:
            timestamp_ms = int((time.time() - args.minutes_ago * 60) * 1000)
            request = pb.Timestamp(timestamp=timestamp_ms)
            ts_datetime = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
            print(f"Starting from {args.minutes_ago} minutes ago...")
            print(f"  (timestamp: {timestamp_ms}, {ts_datetime.strftime('%Y-%m-%d %H:%M:%S UTC')})")
        else:
            request = pb.Timestamp(timestamp=0)
            print("Starting from latest...")

        print("Watching for liquidations...")
        print("Press Ctrl+C to stop\n")

        block_count = 0
        liquidation_count = 0
        start_time = time.time()
        running = True

        # Track liquidations by coin
        coin_stats = defaultdict(lambda: {"count": 0, "volume": 0.0})

        def signal_handler(sig, frame):
            nonlocal running
            print("\n\nStopping stream...")
            running = False

        signal.signal(signal.SIGINT, signal_handler)

        try:
            for response in client.StreamBlockFills(request, metadata=metadata):
                if not running:
                    break

                block_count += 1

                # Extract liquidations
                liquidations = extract_liquidations(response.data, args.verbose)

                for liq in liquidations:
                    liquidation_count += 1

                    # Track stats
                    coin = liq["coin"]
                    try:
                        size = float(liq["size"])
                        coin_stats[coin]["count"] += 1
                        coin_stats[coin]["volume"] += size
                    except (ValueError, TypeError):
                        pass

                    # Display liquidation
                    print(format_liquidation(liq, args.verbose, liquidation_count))
                    print()

                    # Check if we've reached the count limit
                    if args.count > 0 and liquidation_count >= args.count:
                        print(f"Reached {args.count} liquidations, stopping...")
                        running = False
                        break

                # Print stats periodically
                if args.stats_interval > 0 and block_count % args.stats_interval == 0:
                    elapsed = time.time() - start_time
                    rate = block_count / elapsed if elapsed > 0 else 0
                    print(f"📊 Stats: {block_count:,} blocks | {liquidation_count} liquidations | {rate:.1f} blocks/sec")

        except grpc.RpcError as e:
            print(f"Stream error: {e.code()}: {e.details()}")

        # Final stats
        elapsed = time.time() - start_time
        print(f"\n{'='*50}")
        print(f"Session Summary")
        print(f"{'='*50}")
        print(f"Duration: {elapsed:.1f} seconds")
        print(f"Blocks processed: {block_count:,}")
        print(f"Total liquidations: {liquidation_count}")

        if coin_stats:
            print(f"\nLiquidations by coin:")
            for coin in sorted(coin_stats.keys(), key=lambda c: -coin_stats[c]["count"]):
                stats = coin_stats[coin]
                print(f"  {coin}: {stats['count']} liquidations, {stats['volume']:.4f} total size")


if __name__ == "__main__":
    main()
