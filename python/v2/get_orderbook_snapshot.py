#!/usr/bin/env python3
"""
Get OrderBook Snapshot Example - Hyperliquid gRPC API v2

This example demonstrates how to get a single order book snapshot from Hyperliquid L1 using the gRPC API.
You can request:
  - Current snapshot: No arguments (default)
  - Historical snapshot: Set timestamp to a specific time (milliseconds since epoch)

Verbosity levels:
  (default)  - Size, market count, sample markets
  -v         - Add bid/ask counts per market
  -vv        - Add best bid/ask prices
  -vvv       - Add raw JSON keys for debugging

Usage:
  python get_orderbook_snapshot.py                          # Get current snapshot
  python get_orderbook_snapshot.py --timestamp 1702800000000  # Get historical snapshot
  python get_orderbook_snapshot.py -v                       # Show more details

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
from datetime import datetime, timezone
from dotenv import load_dotenv

import hyperliquid_pb2 as pb
import hyperliquid_pb2_grpc as pb_grpc

# Load environment variables from .env file
load_dotenv()

DEFAULT_ENDPOINT = "api-hyperliquid-mainnet-grpc.n.dwellir.com:443"
# Use -1 for unlimited message size
MAX_MESSAGE_SIZE = -1


def parse_args():
    parser = argparse.ArgumentParser(
        description="Get orderbook snapshot from Hyperliquid L1 gRPC API (v2)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Get current snapshot
  %(prog)s --timestamp 1702800000000  # Get snapshot at specific timestamp (ms)
  %(prog)s -v                       # Show bid/ask counts
  %(prog)s -vv                      # Show best prices
  %(prog)s -vvv                     # Debug mode
        """
    )

    parser.add_argument(
        "-t", "--timestamp",
        type=int,
        default=0,
        help="Timestamp in milliseconds since epoch (0 = current snapshot)"
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

    print("Hyperliquid gRPC - Get OrderBook Snapshot Example (v2 API)")
    print("===========================================================")
    print(f"Endpoint: {endpoint}")
    if api_key:
        print("Using API key authentication")
    print(f"Verbosity: {args.verbose}")
    print(f"Max message size: {'unlimited' if MAX_MESSAGE_SIZE == -1 else f'{MAX_MESSAGE_SIZE / 1024 / 1024:.0f} MB'}")

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

        # Create request
        # v2 API uses Timestamp with timestamp_ms field
        request = pb.Timestamp(timestamp_ms=args.timestamp)

        if args.timestamp == 0:
            print("Requesting current OrderBook snapshot...")
        else:
            ts_datetime = datetime.fromtimestamp(args.timestamp / 1000, tz=timezone.utc)
            print(f"Requesting OrderBook snapshot at timestamp {args.timestamp}")
            print(f"  ({ts_datetime.strftime('%Y-%m-%d %H:%M:%S UTC')})")

        print("(Note: This may take a moment as snapshots can be very large)\n")

        start_time = time.time()

        try:
            response = client.GetOrderBookSnapshot(request, metadata=metadata, timeout=120)
            elapsed = time.time() - start_time
            print(f"Received OrderBook snapshot in {elapsed:.2f} seconds!\n")

            # Process the snapshot
            process_orderbook_snapshot(response.data, args.verbose)

        except grpc.RpcError as e:
            print(f"gRPC Error: {e.code()}: {e.details()}")
            if "RESOURCE_EXHAUSTED" in str(e.code()):
                print("\nTip: The message size exceeded the limit. This may be a server-side limit.")
            sys.exit(1)


def process_orderbook_snapshot(data: bytes, verbosity: int):
    """Process and display orderbook snapshot data."""
    try:
        snapshot = json.loads(data.decode("utf-8"))
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        return

    # Debug: show raw keys at highest verbosity
    if verbosity >= 3:
        print(f"[DEBUG] Raw JSON keys: {list(snapshot.keys())}")
        for key, value in snapshot.items():
            if isinstance(value, list):
                print(f"  {key}: list with {len(value)} items")
            elif isinstance(value, dict):
                print(f"  {key}: dict with keys {list(value.keys())[:5]}...")
            else:
                print(f"  {key}: {type(value).__name__} = {str(value)[:50]}")
        print()

    size_mb = len(data) / (1024 * 1024)

    # Get levels/markets
    levels = snapshot.get("levels", [])
    if not isinstance(levels, list):
        levels = []
    market_count = len(levels)

    # Print header
    print(f"--- OrderBook Snapshot ({market_count} markets) ---")
    print(f"Size: {size_mb:.2f} MB")

    # Display timestamp if available
    time_val = snapshot.get("time")
    if isinstance(time_val, (int, float)):
        try:
            snapshot_time = datetime.fromtimestamp(time_val / 1000, tz=timezone.utc)
            print(f"Time: {snapshot_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC")
        except (ValueError, OSError):
            print(f"Time: {time_val}")

    if market_count == 0:
        print("  (no markets in snapshot)")
        return

    # Show markets
    max_show = 5 if verbosity == 0 else (10 if verbosity == 1 else 15)
    print(f"\nMarkets (showing {min(max_show, market_count)} of {market_count}):")

    for i, level in enumerate(levels[:max_show]):
        if not isinstance(level, dict):
            continue

        coin = level.get("coin", "?")
        bids = level.get("bids", [])
        asks = level.get("asks", [])
        bid_count = len(bids) if isinstance(bids, list) else 0
        ask_count = len(asks) if isinstance(asks, list) else 0

        if verbosity == 0:
            # Just coin name
            print(f"  {i+1:3}. {coin}")
        elif verbosity >= 1:
            # Add bid/ask counts
            line = f"  {i+1:3}. {coin:12} | Bids: {bid_count:5,} | Asks: {ask_count:5,}"

            # Add best bid/ask at verbosity >= 2
            if verbosity >= 2:
                best_bid = "---"
                best_ask = "---"

                if bids and isinstance(bids[0], dict):
                    best_bid = bids[0].get("px", "?")
                if asks and isinstance(asks[0], dict):
                    best_ask = asks[0].get("px", "?")

                line += f" | Best: {best_bid} / {best_ask}"

            print(line)

    if market_count > max_show:
        print(f"  ... and {market_count - max_show} more markets")

    # Summary stats
    total_bids = sum(len(l.get("bids", [])) for l in levels if isinstance(l, dict))
    total_asks = sum(len(l.get("asks", [])) for l in levels if isinstance(l, dict))
    print(f"\nTotal: {total_bids:,} bid levels, {total_asks:,} ask levels across {market_count} markets")


if __name__ == "__main__":
    main()
