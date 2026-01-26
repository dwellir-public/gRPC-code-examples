#!/usr/bin/env python3
"""
Get Block Example - Hyperliquid gRPC API v2

This example demonstrates how to get a single block from Hyperliquid L1 using the gRPC API.
You can request:
  - Latest block: No arguments (default)
  - Historical block by timestamp: --timestamp <ms_since_epoch>
  - Historical block by block height: --block <block_height>
  - Historical block by relative time: --minutes-ago <minutes>

Verbosity levels:
  (default)  - Block number, time, actions count
  -v         - Add action type breakdown
  -vv        - Add proposer and more details
  -vvv       - Add raw JSON keys for debugging

Usage:
  python get_block.py                          # Get latest block
  python get_block.py --minutes-ago 10         # Get block from 10 minutes ago
  python get_block.py --timestamp 1702800000000  # Get block at specific timestamp
  python get_block.py --block 12345678         # Get block at specific height
  python get_block.py -v                       # Show action breakdown

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
        description="Get a single block from Hyperliquid L1 gRPC API (v2)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Get latest block
  %(prog)s --minutes-ago 10         # Get block from 10 minutes ago
  %(prog)s -m 10                    # Short form: 10 minutes ago
  %(prog)s --timestamp 1702800000000  # Get block at specific timestamp (ms)
  %(prog)s --block 12345678         # Get block at specific height
  %(prog)s -b 12345678              # Short form: block height
  %(prog)s -v                       # Show action type breakdown
  %(prog)s -vv                      # Show more details
  %(prog)s -vvv                     # Debug mode (show raw JSON keys)
        """
    )

    position_group = parser.add_mutually_exclusive_group()
    position_group.add_argument(
        "-t", "--timestamp",
        type=int,
        help="Get block at specific timestamp (milliseconds since epoch)"
    )
    position_group.add_argument(
        "-b", "--block",
        type=int,
        help="Get block at specific block height"
    )
    position_group.add_argument(
        "-m", "--minutes-ago",
        type=float,
        help="Get block from X minutes ago"
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

    print("Hyperliquid gRPC - Get Block Example (v2 API)")
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
            print(f"Requesting block at timestamp {args.timestamp}")
            print(f"  ({ts_datetime.strftime('%Y-%m-%d %H:%M:%S UTC')})")
        elif args.block:
            request = pb.Position(block_height=args.block)
            print(f"Requesting block at height {args.block:,}")
        elif args.minutes_ago:
            timestamp_ms = int((time.time() - args.minutes_ago * 60) * 1000)
            request = pb.Position(timestamp_ms=timestamp_ms)
            ts_datetime = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
            print(f"Requesting block from {args.minutes_ago} minutes ago...")
            print(f"  (timestamp: {timestamp_ms}, {ts_datetime.strftime('%Y-%m-%d %H:%M:%S UTC')})")
        else:
            # Empty Position targets latest data
            request = pb.Position()
            print("Requesting latest block...")

        print()
        start_time = time.time()

        try:
            response = client.GetBlock(request, metadata=metadata, timeout=60)
            elapsed = time.time() - start_time
            print(f"Received block in {elapsed:.2f} seconds!\n")

            # Process the block
            process_block(response.data, args.verbose)

        except grpc.RpcError as e:
            print(f"gRPC Error: {e.code()}: {e.details()}")
            if "RESOURCE_EXHAUSTED" in str(e.code()):
                print("\nTip: The message size exceeded the limit. This may be a server-side limit.")
            sys.exit(1)


def process_block(data: bytes, verbosity: int):
    """Process and display block data."""
    try:
        block = json.loads(data.decode("utf-8"))
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        return

    # Debug: show raw keys at highest verbosity
    if verbosity >= 3:
        print(f"[DEBUG] Raw JSON keys: {list(block.keys())}")
        for key, value in block.items():
            if isinstance(value, list):
                print(f"  {key}: list with {len(value)} items")
            elif isinstance(value, dict):
                print(f"  {key}: dict with keys {list(value.keys())[:5]}...")
            else:
                print(f"  {key}: {type(value).__name__} = {str(value)[:50]}")
        print()

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
    print(f"--- Block #{height_str} ({total_actions:,} actions) ---")

    # Basic info line
    if block_time:
        print(f"Time: {block_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC | Size: {size_str}")
    else:
        print(f"Size: {size_str}")

    # Show proposer at verbosity >= 2
    if verbosity >= 2 and proposer != "?":
        print(f"Proposer: {proposer}")

    # Show action breakdown at verbosity >= 1
    if verbosity >= 1 and action_counts:
        print("\nActions breakdown:")
        for action_type, count in sorted(action_counts.items(), key=lambda x: -x[1]):
            print(f"  {action_type}: {count:,}")

    # Summary
    print(f"\nTotal actions: {total_actions:,}")


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
