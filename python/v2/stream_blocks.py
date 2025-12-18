#!/usr/bin/env python3
"""
Stream Blocks Example - Hyperliquid gRPC API v2

This example demonstrates how to stream blocks from Hyperliquid L1 using the gRPC API.
You can start streaming from:
  - Latest blocks: No arguments (default)
  - Historical blocks by timestamp: --timestamp <ms_since_epoch>
  - Historical blocks by block height: --block <block_height>
  - Historical blocks by relative time: --minutes-ago <minutes>

Verbosity levels:
  (default)  - Block number, time, actions count
  -v         - Add action type breakdown
  -vv        - Add proposer and more details
  -vvv       - Add raw JSON keys for debugging

Usage:
  python stream_blocks.py                          # Stream from latest
  python stream_blocks.py --minutes-ago 10         # Stream from 10 minutes ago
  python stream_blocks.py --timestamp 1702800000000  # Stream from specific timestamp
  python stream_blocks.py --block 12345678         # Stream from specific block height
  python stream_blocks.py -v                       # Show action breakdown

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
        description="Stream blocks from Hyperliquid L1 gRPC API (v2)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Stream from latest
  %(prog)s --minutes-ago 10         # Stream from 10 minutes ago
  %(prog)s -m 10                    # Short form: 10 minutes ago
  %(prog)s --timestamp 1702800000000  # Stream from specific timestamp (ms)
  %(prog)s --block 12345678         # Stream from specific block height
  %(prog)s -b 12345678              # Short form: block height
  %(prog)s --count 20               # Receive 20 blocks then stop
  %(prog)s -v                       # Show action type breakdown
  %(prog)s -vv                      # Show more details
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
        "-b", "--block",
        type=int,
        help="Start streaming from specific block height"
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
        help="Number of blocks to receive before stopping (default: 5)"
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

    print("Hyperliquid gRPC - Stream Blocks Example (v2 API)")
    print("==================================================")
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
        client = pb_grpc.HyperliquidL1GatewayStub(channel)
        print("Connected successfully!\n")

        # Create request based on arguments
        # v2 API uses Position with oneof { timestamp_ms, block_height }
        if args.timestamp:
            request = pb.Position(timestamp_ms=args.timestamp)
            ts_datetime = datetime.fromtimestamp(args.timestamp / 1000, tz=timezone.utc)
            print(f"Starting block stream from timestamp {args.timestamp}")
            print(f"  ({ts_datetime.strftime('%Y-%m-%d %H:%M:%S UTC')})")
        elif args.block:
            request = pb.Position(block_height=args.block)
            print(f"Starting block stream from block height {args.block:,}")
        elif args.minutes_ago:
            timestamp_ms = int((time.time() - args.minutes_ago * 60) * 1000)
            request = pb.Position(timestamp_ms=timestamp_ms)
            ts_datetime = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
            print(f"Starting block stream from {args.minutes_ago} minutes ago...")
            print(f"  (timestamp: {timestamp_ms}, {ts_datetime.strftime('%Y-%m-%d %H:%M:%S UTC')})")
        else:
            # Empty Position targets latest data
            request = pb.Position()
            print("Starting block stream from latest...")

        print(f"Will receive {args.count} blocks then stop.")
        print("Press Ctrl+C to stop streaming\n")

        block_count = 0
        total_actions = 0
        running = True

        def signal_handler(sig, frame):
            nonlocal running
            print("\nStopping stream...")
            running = False

        signal.signal(signal.SIGINT, signal_handler)

        try:
            for response in client.StreamBlocks(request, metadata=metadata):
                if not running:
                    break

                receipt_time = datetime.now(timezone.utc)
                block_count += 1
                actions = process_block(response.data, receipt_time, args.verbose)
                total_actions += actions

                if block_count >= args.count:
                    print(f"\nReached {args.count} blocks, stopping...")
                    break

        except grpc.RpcError as e:
            print(f"Stream error: {e.code()}: {e.details()}")

        print(f"\nTotal blocks received: {block_count}")
        print(f"Total actions: {total_actions:,}")


def process_block(data: bytes, receipt_time: datetime, verbosity: int) -> int:
    """Process and display block data."""
    try:
        block = json.loads(data.decode("utf-8"))
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        return 0

    # Debug: show raw keys at highest verbosity
    if verbosity >= 3:
        print(f"\n[DEBUG] Raw JSON keys: {list(block.keys())}")
        for key, value in block.items():
            if isinstance(value, list):
                print(f"  {key}: list with {len(value)} items")
            elif isinstance(value, dict):
                print(f"  {key}: dict with keys {list(value.keys())[:5]}...")
            else:
                print(f"  {key}: {type(value).__name__} = {str(value)[:50]}")

    # Extract block info from abci_block
    abci_block = block.get("abci_block", {})

    # Get block height
    block_height = abci_block.get("height", "?")

    # Get proposer
    proposer = abci_block.get("proposer", "?")

    # Parse block time
    block_time = None
    block_time_str = abci_block.get("block_time")
    if block_time_str:
        try:
            block_time = datetime.fromisoformat(block_time_str.replace("Z", "+00:00"))
            if block_time.tzinfo is None:
                block_time = block_time.replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    # Count actions and get breakdown
    action_counts = count_actions_by_type(abci_block.get("signed_action_bundles", []))
    total_actions = sum(action_counts.values())

    # Format size
    size_kb = len(data) / 1024
    if size_kb >= 1024:
        size_str = f"{size_kb/1024:.1f} MB"
    else:
        size_str = f"{size_kb:.1f} KB"

    # Print header with block number
    height_str = f"{block_height:,}" if isinstance(block_height, int) else str(block_height)
    print(f"\n--- Block #{height_str} ({total_actions:,} actions) ---")

    # Basic info line
    if block_time:
        latency = (receipt_time - block_time).total_seconds() * 1000
        print(f"Time: {block_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC | Latency: {latency:.0f}ms | Size: {size_str}")
    else:
        print(f"Size: {size_str}")

    # Show proposer at verbosity >= 2
    if verbosity >= 2 and proposer != "?":
        print(f"Proposer: {proposer}")

    # Show action breakdown at verbosity >= 1
    if verbosity >= 1 and action_counts:
        print("Actions:")
        for action_type, count in sorted(action_counts.items(), key=lambda x: -x[1]):
            print(f"  {action_type}: {count:,}")

    return total_actions


def count_actions_by_type(bundles: list) -> dict:
    """Count actions by type in the block."""
    counts = defaultdict(int)

    for bundle in bundles:
        if not isinstance(bundle, list) or len(bundle) < 2:
            continue
        bundle_data = bundle[1]
        if not isinstance(bundle_data, dict):
            continue
        signed_actions = bundle_data.get("signed_actions", [])
        if not isinstance(signed_actions, list):
            continue

        for action in signed_actions:
            if not isinstance(action, dict):
                continue
            action_data = action.get("action", {})
            if not isinstance(action_data, dict):
                continue

            action_type = action_data.get("type", "unknown")

            if action_type == "order":
                orders = action_data.get("orders", [])
                if isinstance(orders, list):
                    counts["order"] += len(orders)
                else:
                    counts["order"] += 1
            else:
                counts[action_type] += 1

    return dict(counts)


if __name__ == "__main__":
    main()
