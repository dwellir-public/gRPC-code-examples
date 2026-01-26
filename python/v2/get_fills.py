#!/usr/bin/env python3
"""
Get Fills Example - Hyperliquid gRPC API v2

This example demonstrates how to get fills at a specific position from Hyperliquid L1 using the gRPC API.
You can request:
  - Latest fills: No arguments (default)
  - Historical fills by timestamp: --timestamp <ms_since_epoch>
  - Historical fills by block height: --block <block_height>
  - Historical fills by relative time: --minutes-ago <minutes>

Verbosity levels:
  (default)  - Block number, time, fill count, summary
  -v         - Add individual fill details (first 5)
  -vv        - Add all fills with more details
  -vvv       - Add raw JSON keys for debugging

Usage:
  python get_fills.py                          # Get latest fills
  python get_fills.py --minutes-ago 10         # Get fills from 10 minutes ago
  python get_fills.py --timestamp 1702800000000  # Get fills at specific timestamp
  python get_fills.py --block 12345678         # Get fills at specific block height
  python get_fills.py -v                       # Show individual fills

Environment variables (or .env file):
  HYPERLIQUID_ENDPOINT - gRPC endpoint (default: api-hyperliquid-mainnet-grpc.n.dwellir.com:443)
  API_KEY - API key for authentication (optional)
"""

import argparse
import grpc
import json
import sys
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
        description="Get fills at a specific position from Hyperliquid L1 gRPC API (v2)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Get latest fills
  %(prog)s --minutes-ago 10         # Get fills from 10 minutes ago
  %(prog)s -m 10                    # Short form: 10 minutes ago
  %(prog)s --timestamp 1702800000000  # Get fills at specific timestamp (ms)
  %(prog)s --block 12345678         # Get fills at specific block height
  %(prog)s -b 12345678              # Short form: block height
  %(prog)s -v                       # Show individual fill details
  %(prog)s -vv                      # Show all fills with more details
  %(prog)s -vvv                     # Debug mode (show raw JSON keys)
        """
    )

    position_group = parser.add_mutually_exclusive_group()
    position_group.add_argument(
        "-t", "--timestamp",
        type=int,
        help="Get fills at specific timestamp (milliseconds since epoch)"
    )
    position_group.add_argument(
        "-b", "--block",
        type=int,
        help="Get fills at specific block height"
    )
    position_group.add_argument(
        "-m", "--minutes-ago",
        type=float,
        help="Get fills from X minutes ago"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (-v, -vv, -vvv)"
    )

    return parser.parse_args()


def main():
    args = parse_args()

    endpoint = os.getenv("HYPERLIQUID_ENDPOINT", DEFAULT_ENDPOINT)
    # Ensure endpoint has port
    if ":" not in endpoint:
        endpoint = endpoint + ":443"

    api_key = os.getenv("API_KEY")

    print("Hyperliquid gRPC - Get Fills Example (v2 API)")
    print("==============================================")
    print(f"Endpoint: {endpoint}")
    if api_key:
        print("Using API key authentication")
    print(f"Verbosity: {args.verbose}")

    # Create SSL credentials
    credentials = grpc.ssl_channel_credentials()

    # Create channel with options for large messages
    options = [
        ("grpc.max_receive_message_length", MAX_MESSAGE_SIZE),
        ("grpc.max_send_message_length", MAX_MESSAGE_SIZE),
    ]

    # Prepare metadata with API key if provided
    metadata = [("x-api-key", api_key)] if api_key else None

    print("Connecting to gRPC server...")
    with grpc.secure_channel(endpoint, credentials, options=options) as channel:
        client = pb_grpc.HyperliquidL1GatewayStub(channel)
        print("Connected successfully!\n")

        # Create request based on arguments
        # v2 API uses Position with oneof { timestamp_ms, block_height }
        if args.timestamp:
            request = pb.Position(timestamp_ms=args.timestamp)
            ts_datetime = datetime.fromtimestamp(args.timestamp / 1000, tz=timezone.utc)
            print(f"Requesting fills at timestamp {args.timestamp}")
            print(f"  ({ts_datetime.strftime('%Y-%m-%d %H:%M:%S UTC')})")
        elif args.block:
            request = pb.Position(block_height=args.block)
            print(f"Requesting fills at block height {args.block:,}")
        elif args.minutes_ago:
            timestamp_ms = int((time.time() - args.minutes_ago * 60) * 1000)
            request = pb.Position(timestamp_ms=timestamp_ms)
            ts_datetime = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
            print(f"Requesting fills from {args.minutes_ago} minutes ago...")
            print(f"  (timestamp: {timestamp_ms}, {ts_datetime.strftime('%Y-%m-%d %H:%M:%S UTC')})")
        else:
            # Empty Position targets latest data
            request = pb.Position()
            print("Requesting latest fills...")

        print()
        start_time = time.time()

        try:
            response = client.GetFills(request, metadata=metadata, timeout=60)
            elapsed = time.time() - start_time
            print(f"Received fills in {elapsed:.2f} seconds!\n")

            # Process the fills
            process_block_fills(response.data, args.verbose)

        except grpc.RpcError as e:
            print(f"gRPC Error: {e.code()}: {e.details()}")
            if "RESOURCE_EXHAUSTED" in str(e.code()):
                print("\nTip: The message size exceeded the limit. This may be a server-side limit.")
            sys.exit(1)


def process_block_fills(data: bytes, verbosity: int):
    """Process and display block fills data."""
    try:
        block_fills = json.loads(data.decode("utf-8"))
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        return

    # Debug: show raw keys at highest verbosity
    if verbosity >= 3:
        print(f"[DEBUG] Raw JSON keys: {list(block_fills.keys())}")
        for key, value in block_fills.items():
            if isinstance(value, list):
                print(f"  {key}: list with {len(value)} items")
            elif isinstance(value, dict):
                print(f"  {key}: dict with keys {list(value.keys())}")
            else:
                print(f"  {key}: {type(value).__name__} = {value}")
        print()

    # Extract block height (try both field names for compatibility)
    block_height = block_fills.get("block_number") or block_fills.get("height", "?")

    # Extract and parse block time
    block_time = None
    block_time_str = block_fills.get("block_time")
    if block_time_str and isinstance(block_time_str, str):
        try:
            # Parse ISO format timestamp
            block_time = datetime.fromisoformat(block_time_str.replace("Z", "+00:00"))
            if block_time.tzinfo is None:
                block_time = block_time.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    else:
        # Try milliseconds format
        block_time_ms = block_fills.get("time")
        if isinstance(block_time_ms, (int, float)):
            try:
                block_time = datetime.fromtimestamp(block_time_ms / 1000, tz=timezone.utc)
            except (ValueError, OSError):
                pass

    # Extract fills/events (try both field names for compatibility)
    fills = block_fills.get("events") or block_fills.get("fills", [])
    if not isinstance(fills, list):
        fills = []
    fill_count = len(fills)

    # Print header
    print(f"--- Block #{block_height} ({fill_count} fills) ---")

    # Basic info
    if block_time:
        print(f"Time: {block_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC | Size: {len(data):,} bytes")
    else:
        print(f"Size: {len(data):,} bytes")

    if fill_count == 0:
        print("  (no fills in this block)")
        return

    # Summarize fills by coin
    coin_summary = defaultdict(lambda: {"count": 0, "buy_vol": 0.0, "sell_vol": 0.0})
    for fill in fills:
        if not isinstance(fill, dict):
            continue
        coin = fill.get("coin", "?")
        side = fill.get("side", "").upper()
        try:
            sz = float(fill.get("sz", 0))
        except (ValueError, TypeError):
            sz = 0

        coin_summary[coin]["count"] += 1
        if side == "B" or side == "BUY":
            coin_summary[coin]["buy_vol"] += sz
        elif side == "A" or side == "SELL":
            coin_summary[coin]["sell_vol"] += sz

    # Print summary
    print(f"Markets: {', '.join(sorted(coin_summary.keys()))}")

    # Show per-market summary at verbosity >= 1
    if verbosity >= 1:
        print("\nSummary by market:")
        for coin in sorted(coin_summary.keys()):
            stats = coin_summary[coin]
            total_vol = stats["buy_vol"] + stats["sell_vol"]
            print(f"  {coin}: {stats['count']} fills | Buy: {stats['buy_vol']:.4f} | Sell: {stats['sell_vol']:.4f} | Total: {total_vol:.4f}")

    # Show individual fills at verbosity >= 1
    if verbosity >= 1:
        max_show = 5 if verbosity == 1 else len(fills)
        print(f"\nFills detail{' (first 5)' if verbosity == 1 and fill_count > 5 else ''}:")

        for i, fill in enumerate(fills[:max_show]):
            if not isinstance(fill, dict):
                continue

            coin = fill.get("coin", "?")
            side = fill.get("side", "?")
            side_str = "BUY " if side in ("B", "BUY") else "SELL" if side in ("A", "SELL") else side
            px = fill.get("px", "?")
            sz = fill.get("sz", "?")

            # More details at verbosity >= 2
            if verbosity >= 2:
                oid = fill.get("oid", "")
                tid = fill.get("tid", "")
                crossed = fill.get("crossed", "")
                fee = fill.get("fee", "")
                fee_token = fill.get("feeToken", "")

                extra = []
                if oid:
                    extra.append(f"oid={oid}")
                if tid:
                    extra.append(f"tid={tid}")
                if crossed:
                    extra.append(f"crossed={crossed}")
                if fee:
                    extra.append(f"fee={fee} {fee_token}")

                extra_str = f" [{', '.join(extra)}]" if extra else ""
                print(f"  {i+1:3}. {coin:8} {side_str} {sz:>12} @ {px:<12}{extra_str}")
            else:
                print(f"  {i+1:3}. {coin:8} {side_str} {sz:>12} @ {px}")

        if verbosity == 1 and fill_count > max_show:
            print(f"  ... and {fill_count - max_show} more fills")

    # Summary
    total_fills = sum(stats["count"] for stats in coin_summary.values())
    total_buy_vol = sum(stats["buy_vol"] for stats in coin_summary.values())
    total_sell_vol = sum(stats["sell_vol"] for stats in coin_summary.values())
    print(f"\nTotal: {total_fills} fills across {len(coin_summary)} markets")
    print(f"Volume: Buy {total_buy_vol:.4f} | Sell {total_sell_vol:.4f}")


if __name__ == "__main__":
    main()
