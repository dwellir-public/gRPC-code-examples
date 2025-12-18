#!/usr/bin/env python3
"""
Stream TWAP Orders Example - Hyperliquid gRPC API v2

This example demonstrates how to stream and detect TWAP (Time-Weighted Average Price) orders
from Hyperliquid L1 blocks. TWAP orders are algorithmic orders that execute over a specified
time period to minimize market impact.

TWAP Action Types:
  - twapOrder: Creates a new TWAP order
  - twapCancel: Cancels an existing TWAP order

You can start streaming from:
  - Latest: No arguments (default)
  - Historical by timestamp: --timestamp <ms_since_epoch>
  - Historical by block height: --block <block_height>
  - Historical by relative time: --minutes-ago <minutes>

Verbosity levels:
  (default)  - TWAP events with basic info
  -v         - Add order details
  -vv        - Add user addresses
  -vvv       - Debug mode (show all actions)

Usage:
  python stream_twap.py                    # Stream from latest
  python stream_twap.py --minutes-ago 60   # Look back 1 hour
  python stream_twap.py --block 831000000  # From specific block
  python stream_twap.py -v                 # More details

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

# Asset ID to symbol mapping (common assets)
ASSET_MAP = {
    0: "BTC",
    1: "ETH",
    2: "ATOM",
    3: "MATIC",
    4: "DYDX",
    5: "SOL",
    6: "AVAX",
    7: "BNB",
    8: "APE",
    9: "OP",
    10: "LTC",
    11: "ARB",
    12: "DOGE",
    13: "INJ",
    14: "SUI",
    15: "kPEPE",
    16: "CRV",
    17: "LDO",
    18: "LINK",
    19: "STX",
    # Add more as needed
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Stream TWAP orders from Hyperliquid L1 gRPC API (v2)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Stream from latest
  %(prog)s --minutes-ago 60         # Look back 1 hour
  %(prog)s -m 60                    # Short form: 1 hour ago
  %(prog)s --timestamp 1702800000000  # From specific timestamp (ms)
  %(prog)s --block 831000000        # From specific block height
  %(prog)s -b 831000000             # Short form: block height
  %(prog)s --count 10               # Stop after 10 TWAP actions
  %(prog)s -v                       # Show more details
  %(prog)s -vv                      # Show user addresses
  %(prog)s -vvv                     # Debug mode
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
        default=0,
        help="Stop after N TWAP actions (0 = unlimited, default: 0)"
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


def get_asset_symbol(asset_id: int) -> str:
    """Get asset symbol from ID."""
    return ASSET_MAP.get(asset_id, f"Asset#{asset_id}")


def extract_twap_actions(data: bytes, verbosity: int) -> list:
    """Extract TWAP actions from block data."""
    twap_actions = []

    try:
        block = json.loads(data.decode("utf-8"))

        # Debug: show structure at highest verbosity
        if verbosity >= 3:
            print(f"\n[DEBUG] Block keys: {list(block.keys())}")

        abci_block = block.get("abci_block", {})
        block_height = abci_block.get("height", "?")
        block_time = abci_block.get("block_time")
        bundles = abci_block.get("signed_action_bundles", [])

        for bundle in bundles:
            if not isinstance(bundle, list) or len(bundle) < 2:
                continue

            user_address = bundle[0] if len(bundle) > 0 else ""
            bundle_data = bundle[1]

            if not isinstance(bundle_data, dict):
                continue

            for signed_action in bundle_data.get("signed_actions", []):
                if not isinstance(signed_action, dict):
                    continue

                action = signed_action.get("action", {})
                if not isinstance(action, dict):
                    continue

                action_type = action.get("type", "")

                # Check for TWAP-related actions
                if action_type in ("twapOrder", "twapCancel"):
                    twap_action = {
                        "type": action_type,
                        "user_address": user_address,
                        "block_height": block_height,
                        "block_time": block_time,
                        "raw_action": action,
                    }

                    # Parse twapOrder details
                    if action_type == "twapOrder":
                        twap_data = action.get("twap", {})
                        twap_action["asset_id"] = twap_data.get("a", 0)
                        twap_action["asset"] = get_asset_symbol(twap_data.get("a", 0))
                        twap_action["is_buy"] = twap_data.get("b", True)
                        twap_action["size"] = twap_data.get("s", "0")
                        twap_action["reduce_only"] = twap_data.get("r", False)
                        twap_action["minutes"] = twap_data.get("m", 0)
                        twap_action["randomize"] = twap_data.get("t", False)

                    # Parse twapCancel details
                    elif action_type == "twapCancel":
                        twap_action["asset_id"] = action.get("a", 0)
                        twap_action["asset"] = get_asset_symbol(action.get("a", 0))
                        twap_action["twap_id"] = action.get("t", 0)

                    twap_actions.append(twap_action)

                    if verbosity >= 3:
                        print(f"[DEBUG] Found {action_type}: {json.dumps(action)}")

    except json.JSONDecodeError as e:
        if verbosity >= 2:
            print(f"[DEBUG] JSON decode error: {e}")
    except Exception as e:
        if verbosity >= 2:
            print(f"[DEBUG] Error extracting TWAP actions: {e}")

    return twap_actions


def format_twap_action(action: dict, verbosity: int, action_num: int) -> str:
    """Format a TWAP action for display."""
    lines = []

    action_type = action["type"]
    asset = action.get("asset", "?")

    if action_type == "twapOrder":
        side = "BUY" if action.get("is_buy") else "SELL"
        size = action.get("size", "?")
        minutes = action.get("minutes", 0)
        reduce_only = action.get("reduce_only", False)

        lines.append(f"📈 TWAP ORDER #{action_num}: {asset} {side}")
        lines.append(f"   Size: {size} over {minutes} minutes")

        if verbosity >= 1:
            ro_str = " [Reduce Only]" if reduce_only else ""
            randomize = action.get("randomize", False)
            rand_str = " [Randomized]" if randomize else ""
            lines.append(f"   Options:{ro_str}{rand_str}")

            if action.get("block_height"):
                lines.append(f"   Block: #{action['block_height']}")

    elif action_type == "twapCancel":
        twap_id = action.get("twap_id", "?")
        lines.append(f"❌ TWAP CANCEL #{action_num}: {asset}")
        lines.append(f"   TWAP ID: {twap_id}")

        if verbosity >= 1 and action.get("block_height"):
            lines.append(f"   Block: #{action['block_height']}")

    # User address at verbosity >= 2
    if verbosity >= 2:
        addr = action.get("user_address", "")
        if addr:
            lines.append(f"   User: {addr[:10]}...{addr[-8:]}")

    return "\n".join(lines)


def main():
    args = parse_args()

    endpoint = os.getenv("HYPERLIQUID_ENDPOINT", DEFAULT_ENDPOINT)
    if ":" not in endpoint:
        endpoint = endpoint + ":443"

    api_key = os.getenv("API_KEY")

    print("Hyperliquid gRPC - Stream TWAP Orders Example (v2 API)")
    print("======================================================")
    print(f"Endpoint: {endpoint}")
    if api_key:
        print("Using API key authentication")
    print(f"Verbosity: {args.verbose}")
    if args.count > 0:
        print(f"Will stop after {args.count} TWAP actions")

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
        if args.timestamp:
            request = pb.Position(timestamp_ms=args.timestamp)
            ts_datetime = datetime.fromtimestamp(args.timestamp / 1000, tz=timezone.utc)
            print(f"Starting from timestamp {args.timestamp}")
            print(f"  ({ts_datetime.strftime('%Y-%m-%d %H:%M:%S UTC')})")
        elif args.block:
            request = pb.Position(block_height=args.block)
            print(f"Starting from block height {args.block:,}")
        elif args.minutes_ago:
            timestamp_ms = int((time.time() - args.minutes_ago * 60) * 1000)
            request = pb.Position(timestamp_ms=timestamp_ms)
            ts_datetime = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
            print(f"Starting from {args.minutes_ago} minutes ago...")
            print(f"  (timestamp: {timestamp_ms}, {ts_datetime.strftime('%Y-%m-%d %H:%M:%S UTC')})")
        else:
            request = pb.Position()
            print("Starting from latest...")

        print("Watching for TWAP orders...")
        print("Press Ctrl+C to stop\n")

        block_count = 0
        twap_count = 0
        start_time = time.time()
        running = True

        # Track TWAP actions by type and asset
        stats = {
            "twapOrder": defaultdict(int),
            "twapCancel": defaultdict(int),
        }

        def signal_handler(sig, frame):
            nonlocal running
            print("\n\nStopping stream...")
            running = False

        signal.signal(signal.SIGINT, signal_handler)

        try:
            for response in client.StreamBlocks(request, metadata=metadata):
                if not running:
                    break

                block_count += 1

                # Extract TWAP actions
                twap_actions = extract_twap_actions(response.data, args.verbose)

                for action in twap_actions:
                    twap_count += 1

                    # Track stats
                    action_type = action["type"]
                    asset = action.get("asset", "?")
                    stats[action_type][asset] += 1

                    # Display action
                    print(format_twap_action(action, args.verbose, twap_count))
                    print()

                    # Check if we've reached the count limit
                    if args.count > 0 and twap_count >= args.count:
                        print(f"Reached {args.count} TWAP actions, stopping...")
                        running = False
                        break

                # Print stats periodically
                if args.stats_interval > 0 and block_count % args.stats_interval == 0:
                    elapsed = time.time() - start_time
                    rate = block_count / elapsed if elapsed > 0 else 0
                    print(f"📊 Stats: {block_count:,} blocks | {twap_count} TWAP actions | {rate:.1f} blocks/sec")

        except grpc.RpcError as e:
            print(f"Stream error: {e.code()}: {e.details()}")

        # Final stats
        elapsed = time.time() - start_time
        print(f"\n{'='*50}")
        print(f"Session Summary")
        print(f"{'='*50}")
        print(f"Duration: {elapsed:.1f} seconds")
        print(f"Blocks processed: {block_count:,}")
        print(f"Total TWAP actions: {twap_count}")

        if any(stats["twapOrder"]) or any(stats["twapCancel"]):
            print(f"\nTWAP Orders by asset:")
            for asset in sorted(stats["twapOrder"].keys()):
                print(f"  {asset}: {stats['twapOrder'][asset]} orders")

            if any(stats["twapCancel"]):
                print(f"\nTWAP Cancels by asset:")
                for asset in sorted(stats["twapCancel"].keys()):
                    print(f"  {asset}: {stats['twapCancel'][asset]} cancels")


if __name__ == "__main__":
    main()
