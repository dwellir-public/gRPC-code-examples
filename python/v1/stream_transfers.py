#!/usr/bin/env python3
"""
Stream Asset Transfers Example - Hyperliquid gRPC API v1

This example demonstrates how to stream and detect asset transfer events from Hyperliquid L1.
Asset transfers include USD sends, spot token sends, withdrawals, and other fund movements.

Transfer Action Types:
  - usdSend: Send USD to another address
  - spotSend: Send spot tokens to another address
  - withdraw3: Withdraw funds from L1
  - usdClassTransfer: Transfer between USD classes (perp <-> spot)
  - vaultTransfer: Transfer to/from vaults
  - subAccountTransfer: Transfer between sub-accounts

You can start streaming from:
  - Latest: No arguments (default)
  - Historical by timestamp: --timestamp <ms_since_epoch>
  - Historical by relative time: --minutes-ago <minutes>

Verbosity levels:
  (default)  - Transfer events with basic info
  -v         - Add more details (amounts, destinations)
  -vv        - Add full user addresses
  -vvv       - Debug mode (show all matched actions)

Usage:
  python stream_transfers.py                    # Stream from latest
  python stream_transfers.py --minutes-ago 60   # Look back 1 hour
  python stream_transfers.py -v                 # More details

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

# Transfer action types to watch for
TRANSFER_ACTIONS = {
    "usdSend",
    "spotSend",
    "withdraw3",
    "usdClassTransfer",
    "vaultTransfer",
    "subAccountTransfer",
    "internalTransfer",
    "withdraw",  # Legacy
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Stream asset transfers from Hyperliquid L1 gRPC API (v1)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Stream from latest
  %(prog)s --minutes-ago 60         # Look back 1 hour
  %(prog)s -m 60                    # Short form: 1 hour ago
  %(prog)s --timestamp 1702800000000  # From specific timestamp (ms)
  %(prog)s --count 10               # Stop after 10 transfers
  %(prog)s -v                       # Show more details
  %(prog)s -vv                      # Show full addresses
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
        "-m", "--minutes-ago",
        type=float,
        help="Start streaming from X minutes ago"
    )

    parser.add_argument(
        "-c", "--count",
        type=int,
        default=0,
        help="Stop after N transfers (0 = unlimited, default: 0)"
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


def extract_transfers(data: bytes, verbosity: int) -> list:
    """Extract transfer actions from block data."""
    transfers = []

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

                # Check for transfer-related actions
                if action_type in TRANSFER_ACTIONS:
                    transfer = {
                        "type": action_type,
                        "user_address": user_address,
                        "block_height": block_height,
                        "block_time": block_time,
                        "raw_action": action,
                    }

                    # Parse specific transfer types
                    if action_type == "usdSend":
                        transfer["destination"] = action.get("destination", "")
                        transfer["amount"] = action.get("amount", "0")
                        transfer["asset"] = "USD"

                    elif action_type == "spotSend":
                        transfer["destination"] = action.get("destination", "")
                        transfer["amount"] = action.get("amount", "0")
                        transfer["token"] = action.get("token", "?")
                        transfer["asset"] = transfer["token"]

                    elif action_type in ("withdraw3", "withdraw"):
                        transfer["destination"] = action.get("destination", "")
                        transfer["amount"] = action.get("amount", "0")
                        transfer["asset"] = "USD"

                    elif action_type == "usdClassTransfer":
                        transfer["amount"] = action.get("amount", "0")
                        transfer["to_perp"] = action.get("toPerp", True)
                        transfer["asset"] = "USD"
                        transfer["direction"] = "spot->perp" if transfer["to_perp"] else "perp->spot"

                    elif action_type == "vaultTransfer":
                        transfer["vault_address"] = action.get("vaultAddress", "")
                        transfer["is_deposit"] = action.get("isDeposit", True)
                        transfer["usd"] = action.get("usd", "0")
                        transfer["amount"] = transfer["usd"]
                        transfer["asset"] = "USD"

                    elif action_type == "subAccountTransfer":
                        transfer["sub_account_user"] = action.get("subAccountUser", "")
                        transfer["is_deposit"] = action.get("isDeposit", True)
                        transfer["usd"] = action.get("usd", "0")
                        transfer["amount"] = transfer["usd"]
                        transfer["asset"] = "USD"

                    transfers.append(transfer)

                    if verbosity >= 3:
                        print(f"[DEBUG] Found {action_type}: {json.dumps(action)}")

    except json.JSONDecodeError as e:
        if verbosity >= 2:
            print(f"[DEBUG] JSON decode error: {e}")
    except Exception as e:
        if verbosity >= 2:
            print(f"[DEBUG] Error extracting transfers: {e}")

    return transfers


def format_transfer(transfer: dict, verbosity: int, transfer_num: int) -> str:
    """Format a transfer for display."""
    lines = []

    action_type = transfer["type"]
    amount = transfer.get("amount", "?")

    if action_type == "usdSend":
        lines.append(f"💵 USD SEND #{transfer_num}")
        lines.append(f"   Amount: ${amount}")
        if verbosity >= 1:
            dest = transfer.get("destination", "")
            if dest:
                if verbosity >= 2:
                    lines.append(f"   To: {dest}")
                else:
                    lines.append(f"   To: {dest[:10]}...{dest[-8:]}")

    elif action_type == "spotSend":
        token = transfer.get("token", "?")
        lines.append(f"🪙 SPOT SEND #{transfer_num}: {token}")
        lines.append(f"   Amount: {amount}")
        if verbosity >= 1:
            dest = transfer.get("destination", "")
            if dest:
                if verbosity >= 2:
                    lines.append(f"   To: {dest}")
                else:
                    lines.append(f"   To: {dest[:10]}...{dest[-8:]}")

    elif action_type in ("withdraw3", "withdraw"):
        lines.append(f"🏦 WITHDRAWAL #{transfer_num}")
        lines.append(f"   Amount: ${amount}")
        if verbosity >= 1:
            dest = transfer.get("destination", "")
            if dest:
                if verbosity >= 2:
                    lines.append(f"   To: {dest}")
                else:
                    lines.append(f"   To: {dest[:10]}...{dest[-8:]}")

    elif action_type == "usdClassTransfer":
        direction = transfer.get("direction", "?")
        lines.append(f"🔄 USD CLASS TRANSFER #{transfer_num}")
        lines.append(f"   Amount: ${amount} ({direction})")

    elif action_type == "vaultTransfer":
        is_deposit = transfer.get("is_deposit", True)
        action_str = "DEPOSIT" if is_deposit else "WITHDRAW"
        lines.append(f"🏛️ VAULT {action_str} #{transfer_num}")
        lines.append(f"   Amount: ${amount}")
        if verbosity >= 1:
            vault = transfer.get("vault_address", "")
            if vault:
                if verbosity >= 2:
                    lines.append(f"   Vault: {vault}")
                else:
                    lines.append(f"   Vault: {vault[:10]}...{vault[-8:]}")

    elif action_type == "subAccountTransfer":
        is_deposit = transfer.get("is_deposit", True)
        action_str = "TO SUB" if is_deposit else "FROM SUB"
        lines.append(f"👤 SUB-ACCOUNT TRANSFER #{transfer_num} ({action_str})")
        lines.append(f"   Amount: ${amount}")
        if verbosity >= 1:
            sub = transfer.get("sub_account_user", "")
            if sub:
                if verbosity >= 2:
                    lines.append(f"   Sub-account: {sub}")
                else:
                    lines.append(f"   Sub-account: {sub[:10]}...{sub[-8:]}")

    else:
        lines.append(f"📤 {action_type.upper()} #{transfer_num}")
        lines.append(f"   Amount: {amount}")

    # Block info at verbosity >= 1
    if verbosity >= 1:
        block_height = transfer.get("block_height")
        if block_height and block_height != "?":
            if isinstance(block_height, int):
                lines.append(f"   Block: #{block_height:,}")
            else:
                lines.append(f"   Block: #{block_height}")

    # User address at verbosity >= 2
    if verbosity >= 2:
        addr = transfer.get("user_address", "")
        if addr:
            lines.append(f"   From: {addr}")

    return "\n".join(lines)


def main():
    args = parse_args()

    endpoint = os.getenv("HYPERLIQUID_ENDPOINT", DEFAULT_ENDPOINT)
    if ":" not in endpoint:
        endpoint = endpoint + ":443"

    api_key = os.getenv("API_KEY")

    print("Hyperliquid gRPC - Stream Asset Transfers Example (v1 API)")
    print("===========================================================")
    print(f"Endpoint: {endpoint}")
    if api_key:
        print("Using API key authentication")
    print(f"Verbosity: {args.verbose}")
    if args.count > 0:
        print(f"Will stop after {args.count} transfers")

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

        print("Watching for asset transfers...")
        print("Press Ctrl+C to stop\n")

        block_count = 0
        transfer_count = 0
        start_time = time.time()
        running = True

        # Track transfers by type
        stats = defaultdict(lambda: {"count": 0, "volume": 0.0})

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

                # Extract transfers
                transfers = extract_transfers(response.data, args.verbose)

                for transfer in transfers:
                    transfer_count += 1

                    # Track stats
                    action_type = transfer["type"]
                    try:
                        amount = float(transfer.get("amount", 0))
                        stats[action_type]["count"] += 1
                        stats[action_type]["volume"] += amount
                    except (ValueError, TypeError):
                        stats[action_type]["count"] += 1

                    # Display transfer
                    print(format_transfer(transfer, args.verbose, transfer_count))
                    print()

                    # Check if we've reached the count limit
                    if args.count > 0 and transfer_count >= args.count:
                        print(f"Reached {args.count} transfers, stopping...")
                        running = False
                        break

                # Print stats periodically
                if args.stats_interval > 0 and block_count % args.stats_interval == 0:
                    elapsed = time.time() - start_time
                    rate = block_count / elapsed if elapsed > 0 else 0
                    print(f"📊 Stats: {block_count:,} blocks | {transfer_count} transfers | {rate:.1f} blocks/sec")

        except grpc.RpcError as e:
            print(f"Stream error: {e.code()}: {e.details()}")

        # Final stats
        elapsed = time.time() - start_time
        print(f"\n{'='*50}")
        print(f"Session Summary")
        print(f"{'='*50}")
        print(f"Duration: {elapsed:.1f} seconds")
        print(f"Blocks processed: {block_count:,}")
        print(f"Total transfers: {transfer_count}")

        if stats:
            print(f"\nTransfers by type:")
            for action_type in sorted(stats.keys()):
                s = stats[action_type]
                if s["volume"] > 0:
                    print(f"  {action_type}: {s['count']} transfers, ${s['volume']:,.2f} total")
                else:
                    print(f"  {action_type}: {s['count']} transfers")


if __name__ == "__main__":
    main()
