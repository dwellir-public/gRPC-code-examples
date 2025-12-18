#!/usr/bin/env python3
"""
Stream Account Management Example - Hyperliquid gRPC API v1

This example demonstrates how to stream and detect account management events from Hyperliquid L1.
Account management includes leverage changes, margin updates, referrals, approvals, and more.

Account Management Action Types:
  - updateLeverage: Change leverage for a position
  - updateIsolatedMargin: Adjust isolated margin
  - setReferrer: Set referral code
  - approve: Approve an agent to trade on your behalf
  - createSubAccount: Create a new sub-account
  - vaultCreate: Create a new vault
  - vaultModify: Modify vault settings
  - evmUserModify: Link/modify EVM address
  - scheduleCancel: Schedule order cancellation
  - cDeposit / cWithdraw: Cross-chain deposits/withdrawals

You can start streaming from:
  - Latest: No arguments (default)
  - Historical by timestamp: --timestamp <ms_since_epoch>
  - Historical by relative time: --minutes-ago <minutes>

Verbosity levels:
  (default)  - Account events with basic info
  -v         - Add more details
  -vv        - Add full user addresses
  -vvv       - Debug mode (show all matched actions)

Usage:
  python stream_account_mgmt.py                    # Stream from latest
  python stream_account_mgmt.py --minutes-ago 60   # Look back 1 hour
  python stream_account_mgmt.py -v                 # More details

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

# Account management action types to watch for
ACCOUNT_MGMT_ACTIONS = {
    "updateLeverage",
    "updateIsolatedMargin",
    "setReferrer",
    "approve",
    "createSubAccount",
    "vaultCreate",
    "vaultModify",
    "evmUserModify",
    "scheduleCancel",
    "cDeposit",
    "cWithdraw",
    "vaultDistribute",
    "vaultRegisterPerpLp",
    "vaultLeaderCommission",
    "spotUser",
    "vaultFollowerClose",
    "vaultLiquidationOpt",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Stream account management events from Hyperliquid L1 gRPC API (v1)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Stream from latest
  %(prog)s --minutes-ago 60         # Look back 1 hour
  %(prog)s -m 60                    # Short form: 1 hour ago
  %(prog)s --timestamp 1702800000000  # From specific timestamp (ms)
  %(prog)s --count 10               # Stop after 10 events
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
        help="Stop after N events (0 = unlimited, default: 0)"
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


def extract_account_events(data: bytes, verbosity: int) -> list:
    """Extract account management events from block data."""
    events = []

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

                # Check for account management actions
                if action_type in ACCOUNT_MGMT_ACTIONS:
                    event = {
                        "type": action_type,
                        "user_address": user_address,
                        "block_height": block_height,
                        "block_time": block_time,
                        "raw_action": action,
                    }

                    # Parse specific action types
                    if action_type == "updateLeverage":
                        event["asset_id"] = action.get("asset", 0)
                        event["asset"] = get_asset_symbol(action.get("asset", 0))
                        event["is_cross"] = action.get("isCross", True)
                        event["leverage"] = action.get("leverage", 1)

                    elif action_type == "updateIsolatedMargin":
                        event["asset_id"] = action.get("asset", 0)
                        event["asset"] = get_asset_symbol(action.get("asset", 0))
                        event["is_buy"] = action.get("isBuy", True)
                        event["ntli"] = action.get("ntli", 0)

                    elif action_type == "setReferrer":
                        event["code"] = action.get("code", "")

                    elif action_type == "approve":
                        event["max_fee_rate"] = action.get("maxFeeRate", "")
                        event["builder_address"] = action.get("builderAddress", "")
                        event["nonce"] = action.get("nonce", 0)

                    elif action_type == "createSubAccount":
                        event["name"] = action.get("name", "")

                    elif action_type == "vaultCreate":
                        event["vault_config"] = action.get("vaultConfig", {})
                        vault_name = event["vault_config"].get("name", "")
                        event["vault_name"] = vault_name

                    elif action_type == "vaultModify":
                        event["vault_address"] = action.get("vaultAddress", "")
                        event["modifications"] = action.get("modifications", [])

                    elif action_type == "evmUserModify":
                        event["evm_address"] = action.get("evmAddress", "")
                        event["allow_list"] = action.get("allowList", [])

                    elif action_type == "scheduleCancel":
                        event["schedule_time"] = action.get("time", 0)

                    elif action_type in ("cDeposit", "cWithdraw"):
                        event["amount"] = action.get("amount", "0")
                        event["chain"] = action.get("chain", "?")

                    events.append(event)

                    if verbosity >= 3:
                        print(f"[DEBUG] Found {action_type}: {json.dumps(action)}")

    except json.JSONDecodeError as e:
        if verbosity >= 2:
            print(f"[DEBUG] JSON decode error: {e}")
    except Exception as e:
        if verbosity >= 2:
            print(f"[DEBUG] Error extracting account events: {e}")

    return events


def format_account_event(event: dict, verbosity: int, event_num: int) -> str:
    """Format an account management event for display."""
    lines = []

    action_type = event["type"]

    if action_type == "updateLeverage":
        asset = event.get("asset", "?")
        leverage = event.get("leverage", "?")
        is_cross = event.get("is_cross", True)
        mode = "Cross" if is_cross else "Isolated"
        lines.append(f"⚙️ LEVERAGE UPDATE #{event_num}: {asset}")
        lines.append(f"   Leverage: {leverage}x ({mode})")

    elif action_type == "updateIsolatedMargin":
        asset = event.get("asset", "?")
        ntli = event.get("ntli", 0)
        is_buy = event.get("is_buy", True)
        side = "Long" if is_buy else "Short"
        lines.append(f"💰 MARGIN UPDATE #{event_num}: {asset} {side}")
        lines.append(f"   Margin change: {ntli}")

    elif action_type == "setReferrer":
        code = event.get("code", "?")
        lines.append(f"🔗 SET REFERRER #{event_num}")
        lines.append(f"   Code: {code}")

    elif action_type == "approve":
        lines.append(f"✅ AGENT APPROVAL #{event_num}")
        if verbosity >= 1:
            max_fee = event.get("max_fee_rate", "?")
            builder = event.get("builder_address", "")
            lines.append(f"   Max fee rate: {max_fee}")
            if builder:
                if verbosity >= 2:
                    lines.append(f"   Builder: {builder}")
                else:
                    lines.append(f"   Builder: {builder[:10]}...{builder[-8:]}")

    elif action_type == "createSubAccount":
        name = event.get("name", "?")
        lines.append(f"👤 CREATE SUB-ACCOUNT #{event_num}")
        lines.append(f"   Name: {name}")

    elif action_type == "vaultCreate":
        vault_name = event.get("vault_name", "?")
        lines.append(f"🏛️ VAULT CREATE #{event_num}")
        lines.append(f"   Name: {vault_name}")

    elif action_type == "vaultModify":
        lines.append(f"🔧 VAULT MODIFY #{event_num}")
        if verbosity >= 1:
            vault = event.get("vault_address", "")
            if vault:
                if verbosity >= 2:
                    lines.append(f"   Vault: {vault}")
                else:
                    lines.append(f"   Vault: {vault[:10]}...{vault[-8:]}")
            mods = event.get("modifications", [])
            if mods:
                lines.append(f"   Modifications: {len(mods)}")

    elif action_type == "evmUserModify":
        lines.append(f"🔐 EVM USER MODIFY #{event_num}")
        if verbosity >= 1:
            evm = event.get("evm_address", "")
            if evm:
                if verbosity >= 2:
                    lines.append(f"   EVM Address: {evm}")
                else:
                    lines.append(f"   EVM Address: {evm[:10]}...{evm[-8:]}")

    elif action_type == "scheduleCancel":
        schedule_time = event.get("schedule_time", 0)
        lines.append(f"⏰ SCHEDULE CANCEL #{event_num}")
        if schedule_time:
            try:
                dt = datetime.fromtimestamp(schedule_time / 1000, tz=timezone.utc)
                lines.append(f"   Scheduled for: {dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            except:
                lines.append(f"   Scheduled for: {schedule_time}")

    elif action_type == "cDeposit":
        amount = event.get("amount", "?")
        chain = event.get("chain", "?")
        lines.append(f"📥 CROSS-CHAIN DEPOSIT #{event_num}")
        lines.append(f"   Amount: ${amount} from {chain}")

    elif action_type == "cWithdraw":
        amount = event.get("amount", "?")
        chain = event.get("chain", "?")
        lines.append(f"📤 CROSS-CHAIN WITHDRAW #{event_num}")
        lines.append(f"   Amount: ${amount} to {chain}")

    else:
        lines.append(f"📋 {action_type.upper()} #{event_num}")

    # Block info at verbosity >= 1
    if verbosity >= 1:
        block_height = event.get("block_height")
        if block_height and block_height != "?":
            if isinstance(block_height, int):
                lines.append(f"   Block: #{block_height:,}")
            else:
                lines.append(f"   Block: #{block_height}")

    # User address at verbosity >= 2
    if verbosity >= 2:
        addr = event.get("user_address", "")
        if addr:
            lines.append(f"   User: {addr}")

    return "\n".join(lines)


def main():
    args = parse_args()

    endpoint = os.getenv("HYPERLIQUID_ENDPOINT", DEFAULT_ENDPOINT)
    if ":" not in endpoint:
        endpoint = endpoint + ":443"

    api_key = os.getenv("API_KEY")

    print("Hyperliquid gRPC - Stream Account Management Example (v1 API)")
    print("===============================================================")
    print(f"Endpoint: {endpoint}")
    if api_key:
        print("Using API key authentication")
    print(f"Verbosity: {args.verbose}")
    if args.count > 0:
        print(f"Will stop after {args.count} events")

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

        print("Watching for account management events...")
        print("Press Ctrl+C to stop\n")

        block_count = 0
        event_count = 0
        start_time = time.time()
        running = True

        # Track events by type
        stats = defaultdict(int)

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

                # Extract account events
                account_events = extract_account_events(response.data, args.verbose)

                for event in account_events:
                    event_count += 1

                    # Track stats
                    action_type = event["type"]
                    stats[action_type] += 1

                    # Display event
                    print(format_account_event(event, args.verbose, event_count))
                    print()

                    # Check if we've reached the count limit
                    if args.count > 0 and event_count >= args.count:
                        print(f"Reached {args.count} events, stopping...")
                        running = False
                        break

                # Print stats periodically
                if args.stats_interval > 0 and block_count % args.stats_interval == 0:
                    elapsed = time.time() - start_time
                    rate = block_count / elapsed if elapsed > 0 else 0
                    print(f"📊 Stats: {block_count:,} blocks | {event_count} account events | {rate:.1f} blocks/sec")

        except grpc.RpcError as e:
            print(f"Stream error: {e.code()}: {e.details()}")

        # Final stats
        elapsed = time.time() - start_time
        print(f"\n{'='*50}")
        print(f"Session Summary")
        print(f"{'='*50}")
        print(f"Duration: {elapsed:.1f} seconds")
        print(f"Blocks processed: {block_count:,}")
        print(f"Total account events: {event_count}")

        if stats:
            print(f"\nEvents by type:")
            for action_type in sorted(stats.keys(), key=lambda x: -stats[x]):
                print(f"  {action_type}: {stats[action_type]}")


if __name__ == "__main__":
    main()
