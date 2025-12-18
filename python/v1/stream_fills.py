#!/usr/bin/env python3
"""
Stream Fills Example - Hyperliquid gRPC API v1

This example demonstrates how to stream fills from Hyperliquid L1 using the gRPC API.
You can start streaming from:
  - Latest fills: No arguments (default)
  - Historical fills by timestamp: --timestamp <ms_since_epoch>
  - Historical fills by relative time: --minutes-ago <minutes>

Verbosity levels:
  (default)  - Block number, time, fill count, summary
  -v         - Add individual fill details (first 5)
  -vv        - Add all fills with more details
  -vvv       - Add raw JSON keys for debugging

Usage:
  python stream_fills.py                          # Stream from latest
  python stream_fills.py --minutes-ago 10         # Stream from 10 minutes ago
  python stream_fills.py --timestamp 1702800000000  # Stream from specific timestamp
  python stream_fills.py -v                       # Show individual fills
  python stream_fills.py -vvv                     # Debug mode

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
        description="Stream fills from Hyperliquid L1 gRPC API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Stream from latest
  %(prog)s --minutes-ago 10         # Stream from 10 minutes ago
  %(prog)s -m 10                    # Short form: 10 minutes ago
  %(prog)s --timestamp 1702800000000  # Stream from specific timestamp (ms)
  %(prog)s --count 20               # Receive 20 block fills then stop
  %(prog)s -v                       # Show individual fill details
  %(prog)s -vv                      # Show all fills with more details
  %(prog)s -vvv                     # Debug mode (show raw JSON keys)
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
        default=5,
        help="Number of block fills to receive before stopping (default: 5)"
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

    print("Hyperliquid gRPC - Stream Fills Example (v1 API)")
    print("===============================================")
    print(f"Endpoint: {endpoint}")
    if api_key:
        print("Using API key authentication")
    print(f"Verbosity: {args.verbose}")

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
            print(f"Starting fills stream from timestamp {args.timestamp}")
            print(f"  ({ts_datetime.strftime('%Y-%m-%d %H:%M:%S UTC')})")
        elif args.minutes_ago:
            timestamp_ms = int((time.time() - args.minutes_ago * 60) * 1000)
            request = pb.Timestamp(timestamp=timestamp_ms)
            ts_datetime = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
            print(f"Starting fills stream from {args.minutes_ago} minutes ago...")
            print(f"  (timestamp: {timestamp_ms}, {ts_datetime.strftime('%Y-%m-%d %H:%M:%S UTC')})")
        else:
            request = pb.Timestamp(timestamp=0)
            print("Starting fills stream from latest...")

        print(f"Will receive {args.count} block fills then stop.")
        print("Press Ctrl+C to stop streaming\n")

        fills_count = 0
        total_fills = 0
        running = True

        def signal_handler(sig, frame):
            nonlocal running
            print("\nStopping stream...")
            running = False

        signal.signal(signal.SIGINT, signal_handler)

        try:
            for response in client.StreamBlockFills(request, metadata=metadata):
                if not running:
                    break

                receipt_time = datetime.now(timezone.utc)
                fills_count += 1
                num_fills = process_block_fills(response.data, fills_count, receipt_time, args.verbose)
                total_fills += num_fills

                if fills_count >= args.count:
                    print(f"\nReached {args.count} block fills, stopping...")
                    break

        except grpc.RpcError as e:
            print(f"Stream error: {e.code()}: {e.details()}")

        print(f"\nTotal block fills received: {fills_count}")
        print(f"Total individual fills: {total_fills}")


def process_block_fills(data: bytes, block_num: int, receipt_time: datetime, verbosity: int) -> int:
    """Process and display block fills data."""
    try:
        block_fills = json.loads(data.decode("utf-8"))
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        return 0

    # Debug: show raw keys at highest verbosity
    if verbosity >= 3:
        print(f"\n[DEBUG] Raw JSON keys: {list(block_fills.keys())}")
        for key, value in block_fills.items():
            if isinstance(value, list):
                print(f"  {key}: list with {len(value)} items")
            elif isinstance(value, dict):
                print(f"  {key}: dict with keys {list(value.keys())}")
            else:
                print(f"  {key}: {type(value).__name__} = {value}")

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
    print(f"\n--- Block #{block_height} ({fill_count} fills) ---")

    # Basic info
    if block_time:
        latency = (receipt_time - block_time).total_seconds() * 1000
        print(f"Time: {block_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC | Latency: {latency:.0f}ms | Size: {len(data):,} bytes")
    else:
        print(f"Size: {len(data):,} bytes")

    if fill_count == 0:
        print("  (no fills in this block)")
        return 0

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
        print("Summary by market:")
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

    return fill_count


if __name__ == "__main__":
    main()
