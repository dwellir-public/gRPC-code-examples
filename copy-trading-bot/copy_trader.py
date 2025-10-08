#!/usr/bin/env python3
"""
Hyperliquid Copy Trading Bot - Educational Example

⚠️  WARNING: This bot trades with REAL money on MAINNET
    - Always test in DRY_RUN mode first
    - Never share your private keys
    - You can lose money - use at your own risk
    - Not financial advice

This is a simple, educational example of copy trading on Hyperliquid.
The code is kept simple and well-commented to make it easy to understand.
"""

import os
import sys
import time
import json
import signal
from decimal import Decimal
from dotenv import load_dotenv
import grpc
import eth_account

# Import gRPC generated code
import hyperliquid_pb2
import hyperliquid_pb2_grpc

# Import Hyperliquid SDK
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants


class CopyTradingBot:
    """
    Copy trading bot for Hyperliquid

    HOW IT WORKS:
    1. Streams real-time trades via gRPC
    2. Detects trades from target wallet
    3. Calculates position size based on copy percentage
    4. Places IOC orders (immediate execution, no waiting)
    5. Syncs positions from exchange (not local tracker)

    KEY FEATURES:
    - IOC orders: Fills immediately or cancels (perfect for copy trading)
    - Direction detection: Uses 'dir' field ("Open Long", "Close Short", etc.)
    - Size precision: Rounds to correct decimals per coin (ZORA=0, BTC=5, ETH=4)
    - Position syncing: Fetches real positions from exchange before closing
    - Safety limits: Min/max position size, max open positions

    CONFIGURATION (.env):
    - TARGET_WALLET_ADDRESS: Wallet to copy
    - COPY_PERCENTAGE: % of account to use per trade (e.g., 5.0 = 5%)
    - DRY_RUN: true/false (simulate or trade)
    - MIN_POSITION_SIZE_USD: Skip trades smaller than this
    - MAX_POSITION_SIZE_USD: Cap position size
    - MAX_OPEN_POSITIONS: Maximum concurrent positions (default: 4)
    - SLIPPAGE_TOLERANCE_PCT: Allow paying X% more for better fills (default: 0.5%)
    - COIN_FILTER_MODE: ALL or ENABLED (default: ALL)
    - ENABLED_COINS: Comma-separated list (only used when mode=ENABLED)
    """

    def __init__(self):
        """Load configuration and set up the bot"""

        print("\n🤖 Hyperliquid Copy Trading Bot")

        load_dotenv()

        # === Configuration ===
        self.endpoint = os.getenv('HYPERLIQUID_ENDPOINT')
        self.target_wallet = os.getenv('TARGET_WALLET_ADDRESS', '').strip().lower()
        self.copy_percentage = float(os.getenv('COPY_PERCENTAGE', '5.0'))
        self.dry_run = os.getenv('DRY_RUN', 'true').lower() == 'true'
        self.max_position_usd = float(os.getenv('MAX_POSITION_SIZE_USD', '100'))
        self.min_position_usd = float(os.getenv('MIN_POSITION_SIZE_USD', '10'))
        self.max_open_positions = int(os.getenv('MAX_OPEN_POSITIONS', '4'))
        self.slippage_tolerance_pct = float(os.getenv('SLIPPAGE_TOLERANCE_PCT', '0.5'))  # Allow 0.5% higher price
        self.min_notional_usd = 10.0  # Hyperliquid exchange minimum

        # Coin filtering mode
        self.coin_filter_mode = os.getenv('COIN_FILTER_MODE', 'ALL').upper()  # ALL or ENABLED
        enabled_coins_str = os.getenv('ENABLED_COINS', '').strip()
        self.enabled_coins = set(c.strip() for c in enabled_coins_str.split(',')) if enabled_coins_str else None

        # Credentials for live trading
        self.private_key = os.getenv('HYPERLIQUID_PRIVATE_KEY', '')
        self.wallet_address = os.getenv('HYPERLIQUID_WALLET_ADDRESS', '')

        # === State Tracking ===
        self.processed_fills = set()  # Avoid duplicate fills
        self.open_positions = {}  # {coin: size} - positive=long, negative=short
        self.coin_metadata = {}  # Cached size precision per coin

        signal.signal(signal.SIGINT, self._signal_handler)

        # === Validation ===
        self._validate_config()

        # === Initialize Hyperliquid SDK ===
        self.info = None
        self.exchange = None

        if not self.dry_run:
            account = eth_account.Account.from_key(self.private_key)
            self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
            self.exchange = Exchange(account, constants.MAINNET_API_URL, account_address=self.wallet_address)

            # Fetch account value
            try:
                user_state = self.info.user_state(self.wallet_address)
                account_value = float(user_state["marginSummary"]["accountValue"])
                print(f"   Account: ${account_value:.2f}")
            except Exception as e:
                print(f"   ⚠️  Could not fetch account: {e}")

            # Load coin metadata and sync positions
            self._fetch_coin_metadata()
            self._sync_positions_from_exchange()

        # === Display Configuration ===
        print(f"   Target: {self.target_wallet[:8]}...{self.target_wallet[-6:]}")
        print(f"   Copy: {self.copy_percentage}% | Limits: ${self.min_position_usd}-${self.max_position_usd} | Max positions: {self.max_open_positions}")

        # Show coin filter mode
        if self.coin_filter_mode == 'ALL':
            print(f"   Coins: ALL (no filter)")
        elif self.enabled_coins:
            print(f"   Coins: {', '.join(sorted(self.enabled_coins))}")
        else:
            print(f"   Coins: ALL (ENABLED mode but no coins specified)")

        mode = "🔵 DRY RUN" if self.dry_run else "🔴 LIVE TRADING"
        print(f"   Mode: {mode}\n")

    def _validate_config(self):
        """Validate configuration from .env"""

        if not self.target_wallet:
            print("\n❌ TARGET_WALLET_ADDRESS not set in .env")
            sys.exit(1)

        if not self.target_wallet.startswith('0x'):
            print("\n❌ TARGET_WALLET_ADDRESS must start with '0x'")
            sys.exit(1)

        if not (0 < self.copy_percentage <= 100):
            print("\n❌ COPY_PERCENTAGE must be between 0 and 100")
            sys.exit(1)

        if not self.dry_run and (not self.private_key or not self.wallet_address):
            print("\n❌ Live trading requires HYPERLIQUID_PRIVATE_KEY and HYPERLIQUID_WALLET_ADDRESS")
            sys.exit(1)

    def _fetch_coin_metadata(self):
        """Fetch metadata for all coins (size decimals, price tick sizes, etc.)"""
        try:
            print("🔧 Fetching coin metadata...")
            meta = self.info.meta()
            universe = meta.get("universe", [])

            # Cache metadata for each coin (used for size and price rounding)
            for asset in universe:
                name = asset.get("name", "")
                sz_decimals = asset.get("szDecimals", 4)  # Default to 4 if missing

                # Get tick size for price rounding (in basis points, e.g., 100 = 1 cent)
                # Convert to actual decimal value
                tick_size_str = asset.get("tickSize", "100")  # Default to 1 cent
                tick_size = float(tick_size_str) / 10000  # Convert from basis points

                if name:
                    self.coin_metadata[name] = {
                        "szDecimals": sz_decimals,
                        "maxLeverage": asset.get("maxLeverage", 1),
                        "tickSize": tick_size,
                    }

            print(f"   ✅ Loaded {len(self.coin_metadata)} coins\n")

        except Exception as e:
            print(f"   ⚠️  Metadata fetch failed: {e} (using defaults)\n")

    def _round_size(self, coin, size):
        """Round size to the correct decimal precision for this coin"""
        if coin in self.coin_metadata:
            decimals = self.coin_metadata[coin]["szDecimals"]
            return round(size, decimals)
        else:
            # Default to 4 decimals if metadata not available
            return round(size, 4)

    def _round_price(self, coin, price):
        """Round price to the correct tick size for this coin"""
        if coin in self.coin_metadata:
            tick_size = self.coin_metadata[coin]["tickSize"]
            # Round to nearest tick
            # Example: price=$46.53150, tick=$0.01 → $46.53
            return round(price / tick_size) * tick_size
        else:
            # Default to 2 decimals (1 cent) if metadata not available
            return round(price, 2)

    def _sync_positions_from_exchange(self, verbose=True):
        """
        Fetch actual positions from exchange (not local tracker)

        This is critical because:
        - Opening orders may be "resting" (not filled yet)
        - We only want to track FILLED positions
        - Prevents reduce-only errors when closing
        """
        try:
            if verbose:
                print("🔄 Syncing positions...")

            user_state = self.info.user_state(self.wallet_address)
            asset_positions = user_state.get("assetPositions", [])

            # Clear and rebuild position tracker from exchange reality
            self.open_positions = {}

            synced_count = 0
            for asset_pos in asset_positions:
                position = asset_pos.get("position", {})
                coin = position.get("coin", "")
                szi = position.get("szi", "0")  # Positive=long, negative=short

                size = float(szi)

                if size != 0 and coin:
                    self.open_positions[coin] = size
                    synced_count += 1
                    if verbose:
                        direction = "LONG" if size > 0 else "SHORT"
                        print(f"   {coin}: {abs(size):.4f} ({direction})")

            if verbose:
                print(f"   📊 {synced_count} position(s)\n" if synced_count else "   No positions\n")

        except Exception as e:
            if verbose:
                print(f"   ⚠️  Sync failed: {e}\n")

    def _signal_handler(self, sig, frame):
        """Handle Ctrl+C gracefully"""
        print("\n\n🛑 Shutting down...")
        print(f"📊 Processed {len(self.processed_fills)} unique fills")
        print("\nGoodbye! 👋\n")
        sys.exit(0)

    def calculate_position_size(self, target_size, target_price, coin):
        """
        Calculate our position size based on copy percentage

        Returns our position size, or None if trade should be skipped
        """

        # Get real account value from exchange
        if self.info:
            try:
                user_state = self.info.user_state(self.wallet_address)
                account_value_usd = float(user_state["marginSummary"]["accountValue"])
            except Exception as e:
                print(f"      ⚠️  Account value fetch failed, using $1000: {e}")
                account_value_usd = 100.0
        else:
            account_value_usd = 100.0  # Dry-run default

        # Calculate our position value: account * copy_percentage
        our_value_usd = account_value_usd * (self.copy_percentage / 100.0)

        # Apply max/min limits
        if our_value_usd > self.max_position_usd:
            our_value_usd = self.max_position_usd

        if our_value_usd < self.min_position_usd:
            print(f"      ⏭️  SKIP: ${our_value_usd:.2f} < ${self.min_position_usd} min")
            return None

        # Convert USD value to coin size
        our_size_raw = our_value_usd / float(target_price)

        # Round to correct decimal precision (e.g., ZORA=0, BTC=5, ETH=4)
        our_size = self._round_size(coin, our_size_raw)

        # Log if significant rounding occurred
        if coin in self.coin_metadata:
            decimals = self.coin_metadata[coin]["szDecimals"]
            if abs(our_size - our_size_raw) > 0.0001:
                print(f"      🔧 Rounded: {our_size_raw:.6f} → {our_size} ({decimals} decimals)")

        # Final check: notional value must be >= $10 (Hyperliquid minimum)
        notional_value = our_size * float(target_price)
        if notional_value < self.min_notional_usd:
            print(f"      ⏭️  SKIP: Notional ${notional_value:.2f} < ${self.min_notional_usd} min (exchange rule)")
            return None

        return our_size

    def place_order(self, coin, side, size, price, is_closing=False):
        """
        Place order on Hyperliquid (or simulate in dry-run mode)

        Uses IOC (Immediate or Cancel) orders for instant execution
        """

        is_buy = (side == 'B')
        side_name = 'BUY' if is_buy else 'SELL'
        action = 'CLOSE' if is_closing else 'OPEN'
        notional = float(size) * float(price)

        print(f"\n   📝 {action}: {side_name} {size} {coin} @ ${price} (${notional:.2f})")

        if self.dry_run:
            # === DRY RUN MODE: Simulate only ===
            print(f"   🔵 DRY RUN (set DRY_RUN=false to enable real trading)\n")

            # Update position tracker (for dry-run simulation)
            if not is_closing:
                position_size = size if is_buy else -size
                self.open_positions[coin] = self.open_positions.get(coin, 0) + position_size
            else:
                if coin in self.open_positions:
                    del self.open_positions[coin]

        else:
            # === LIVE TRADING MODE ===

            # For closing orders, verify position exists on exchange first
            if is_closing:
                self._sync_positions_from_exchange(verbose=False)

                if coin not in self.open_positions:
                    print(f"      ⚠️  No {coin} position found on exchange (may not have filled yet)\n")
                    return

                # Verify direction matches (don't close LONG when you have SHORT)
                our_position = self.open_positions[coin]
                closing_long = our_position > 0 and not is_buy
                closing_short = our_position < 0 and is_buy

                if not (closing_long or closing_short):
                    print(f"      ⚠️  Direction mismatch: {our_position:.4f} vs {side_name}\n")
                    return

            try:
                # Apply slippage tolerance for opening orders
                # Improves fill rate by accepting slightly worse entry prices
                order_price = float(price)
                if not is_closing and self.slippage_tolerance_pct > 0:
                    if is_buy:
                        # Opening LONG (buying): Pay UP TO X% more
                        # Target bought at $100 → We pay up to $100.50 (chase asks up)
                        order_price = order_price * (1 + self.slippage_tolerance_pct / 100)
                    else:
                        # Opening SHORT (selling): Accept DOWN TO X% less
                        # Target sold at $100 → We accept down to $99.50 (chase bids down)
                        #
                        # Why subtract: SELL limit at $99.50 means "I'll sell at $99.50 or HIGHER"
                        # If market moved down to $99.50, this catches the remaining bids
                        # If we set SELL at $100.50, nobody will match (bids are below)
                        order_price = order_price * (1 - self.slippage_tolerance_pct / 100)

                # Round price to valid tick size
                # Each coin has a minimum price increment (tick size)
                # Example: HYPE tick=$0.001, so $46.53150 → $46.532
                order_price = self._round_price(coin, order_price)

                if order_price != float(price):
                    action = "pay up to" if is_buy else "accept down to"
                    print(f"      💡 Slippage: {action} ${order_price} (vs target's ${price})")

                # Place IOC order (Immediate or Cancel)
                # - Fills immediately at limit price or better
                # - Unfilled portion auto-cancels
                # - Perfect for copy trading (fail fast, no waiting)
                order_result = self.exchange.order(
                    coin,
                    is_buy,
                    size,
                    order_price,
                    {"limit": {"tif": "Ioc"}},  # IOC = Immediate or Cancel
                    reduce_only=is_closing
                )

                # Process order response
                if order_result["status"] == "ok":
                    response = order_result["response"]["data"]
                    statuses = response.get("statuses", [])

                    if statuses:
                        status = statuses[0]

                        # IOC orders: either "filled" or error (no "resting")
                        if "filled" in status:
                            filled = status["filled"]
                            total_sz = filled.get("totalSz", size)
                            avg_px = filled.get("avgPx", price)

                            # Check if partially filled
                            partial = float(total_sz) < float(size)
                            partial_str = f" ({(float(total_sz)/float(size)*100):.1f}%)" if partial else ""

                            print(f"      ✅ Filled: {total_sz} @ ${avg_px}{partial_str}")

                            # Update position tracker
                            if not is_closing:
                                position_size = float(total_sz) if is_buy else -float(total_sz)
                                self.open_positions[coin] = self.open_positions.get(coin, 0) + position_size
                            else:
                                if coin in self.open_positions:
                                    del self.open_positions[coin]

                        else:
                            # Error or unknown status
                            if "error" in status:
                                error_msg = status["error"]
                                print(f"      ❌ Error: {error_msg}")

                                # Helpful tips for common errors
                                error_lower = error_msg.lower()
                                if "invalid size" in error_lower and coin in self.coin_metadata:
                                    decimals = self.coin_metadata[coin]["szDecimals"]
                                    print(f"      💡 {coin} requires {decimals} decimal places")
                                elif "reduce only" in error_lower:
                                    print(f"      💡 Position doesn't exist or hasn't filled yet")
                            else:
                                print(f"      ⚠️  Unknown status: {status}")

                    # Sync positions after opening orders
                    if not is_closing:
                        self._sync_positions_from_exchange(verbose=False)

                    # Show current positions
                    if self.open_positions:
                        positions_str = ", ".join([f"{c}: {abs(s):.4f} ({'LONG' if s > 0 else 'SHORT'})"
                                                   for c, s in self.open_positions.items()])
                        print(f"      📊 Positions ({len(self.open_positions)}/{self.max_open_positions}): {positions_str}\n")
                    else:
                        print(f"      📊 No positions\n")

                else:
                    # Order failed at API level
                    error_msg = order_result.get("response", order_result)
                    print(f"      ❌ Failed: {error_msg}")

                    # Helpful tips for common failures
                    error_str = str(error_msg).lower()
                    if "notional" in error_str or "minimum" in error_str:
                        print(f"      💡 Increase COPY_PERCENTAGE or MIN_POSITION_SIZE_USD\n")
                    elif "reduce" in error_str or "position" in error_str:
                        print(f"      💡 Position sync issue\n")

            except Exception as e:
                print(f"      ❌ Exception: {e}\n")

                # Debug on exceptions
                error_str = str(e).lower()
                if "notional" in error_str or "minimum" in error_str:
                    print(f"      💡 Hyperliquid minimum: $10 per order\n")

    def process_fill(self, wallet_address, fill_data):
        """
        Process a trade from the block fills stream

        Flow:
        1. Check if from target wallet
        2. Check for duplicates
        3. Extract trade info
        4. Determine open vs close
        5. Apply filters and limits
        6. Calculate position size
        7. Place order
        """

        # === Filter: Only target wallet ===
        if wallet_address.lower() != self.target_wallet:
            return

        # === Filter: No duplicates ===
        fill_id = f"{fill_data.get('hash', '')}_{fill_data.get('tid', '')}"
        if fill_id in self.processed_fills:
            return
        self.processed_fills.add(fill_id)

        # === Extract trade data ===
        coin = fill_data.get('coin', '')
        side = fill_data.get('side', '')  # 'B'=Buy, 'A'=Sell
        size = fill_data.get('sz', '0')
        price = fill_data.get('px', '0')
        closed_pnl = fill_data.get('closedPnl', '0')
        direction = fill_data.get('dir', '')  # "Open Long", "Close Short", etc.

        # === Determine action: Open or Close ===
        # Use 'dir' field (most reliable): "Open Long", "Close Long", "Open Short", "Close Short"
        is_closing = direction.startswith('Close') if direction else (closed_pnl and float(closed_pnl) != 0)
        is_opening = direction.startswith('Open') if direction else not is_closing

        # === Filter: Coin whitelist (only if ENABLED mode) ===
        if self.coin_filter_mode == 'ENABLED':
            if self.enabled_coins and coin not in self.enabled_coins:
                return  # Skip coins not in the enabled list

        # === Filter: Position limit (opening only) ===
        if not is_closing:
            if coin not in self.open_positions and len(self.open_positions) >= self.max_open_positions:
                print(f"\n⏭️  SKIP: Max positions ({len(self.open_positions)}/{self.max_open_positions})")
                return

        # === Log detected trade ===
        action = "CLOSE" if is_closing else "OPEN"
        side_name = 'BUY' if side == 'B' else 'SELL'
        notional = float(size) * float(price)
        pnl_str = f" | PnL: ${closed_pnl}" if is_closing else ""

        print(f"\n{'='*70}")
        print(f"🎯 TARGET: {action} {direction}")
        print(f"   {coin}: {side_name} {size} @ ${price} (${notional:.2f}){pnl_str}")
        print(f"{'='*70}")

        # === Calculate our position size ===
        if is_closing:
            # For closes: use our actual position size
            if coin not in self.open_positions:
                print(f"   ⏭️  SKIP: No {coin} position (bot may have started after open)")
                print("=" * 70)
                return

            our_size = abs(self.open_positions[coin])
            our_position_value = self.open_positions[coin]
            is_long = our_position_value > 0
            is_short = our_position_value < 0

            # Validate direction matches (don't close LONG when you have SHORT)
            if direction:
                if "Close Long" in direction and is_short:
                    print(f"   ⏭️  SKIP: Direction mismatch (we have SHORT, target closing LONG)")
                    print("=" * 70)
                    return
                elif "Close Short" in direction and is_long:
                    print(f"   ⏭️  SKIP: Direction mismatch (we have LONG, target closing SHORT)")
                    print("=" * 70)
                    return

            # Check notional minimum
            notional_value = our_size * float(price)
            if notional_value < self.min_notional_usd:
                print(f"   ⏭️  SKIP: Notional ${notional_value:.2f} < ${self.min_notional_usd} min")
                print("=" * 70)
                return

            print(f"   📊 Our close: {our_size} ({'LONG' if is_long else 'SHORT'})")

        else:
            # For opens: calculate based on copy percentage
            our_size = self.calculate_position_size(size, price, coin)

            if our_size is None:
                print("=" * 70)
                return  # Filtered out (too small, etc.)

            notional_value = our_size * float(price)
            print(f"   📊 Our open: {our_size} (${notional_value:.2f}, {self.copy_percentage}% of account)")

        # === Place the order ===
        self.place_order(coin, side, our_size, price, is_closing)
        print("=" * 70)

    def stream_block_fills(self):
        """
        Stream real-time trades from Hyperliquid via gRPC

        Monitors all trades on Hyperliquid and processes
        trades from the target wallet
        """

        # Setup gRPC connection
        endpoint = self.endpoint if ':' in self.endpoint else f'{self.endpoint}:443'
        credentials = grpc.ssl_channel_credentials()
        options = [
            ('grpc.max_receive_message_length', 150 * 1024 * 1024),  # 150MB
            ('grpc.keepalive_time_ms', 10000),
            ('grpc.keepalive_timeout_ms', 5000),
        ]

        print(f"👀 Watching {self.target_wallet[:8]}...{self.target_wallet[-6:]}")
        print(f"⏳ Waiting for trades...\n")

        # Connect and stream
        with grpc.secure_channel(endpoint, credentials, options=options) as channel:
            client = hyperliquid_pb2_grpc.HyperLiquidL1GatewayStub(channel)
            request = hyperliquid_pb2.Timestamp(timestamp=0)  # Start from latest

            try:
                # Stream block fills (infinite loop until error or Ctrl+C)
                for response in client.StreamBlockFills(request):
                    try:
                        block_data = json.loads(response.data.decode('utf-8'))
                    except json.JSONDecodeError as e:
                        print(f"⚠️  Parse error: {e}")
                        continue

                    # Process each trade in this block
                    events = block_data.get('events', [])
                    for event in events:
                        if not isinstance(event, list) or len(event) < 2:
                            continue

                        wallet_address = event[0]
                        fill_data = event[1]

                        self.process_fill(wallet_address, fill_data)

            except grpc.RpcError as e:
                print(f"\n❌ gRPC error: {e.code()} - {e.details()}")
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")
                import traceback
                traceback.print_exc()

    def run(self):
        """Start the copy trading bot"""
        self.stream_block_fills()


def main():
    """Entry point"""

    if not os.path.exists('.env'):
        print("\n❌ No .env file found")
        print("📝 Setup: cp .env.example .env")
        print("   Then edit .env and set TARGET_WALLET_ADDRESS\n")
        sys.exit(1)

    bot = CopyTradingBot()
    bot.run()


if __name__ == '__main__':
    main()
