# 🤖 Hyperliquid Copy Trading Bot

Automatically mirror trades from any Hyperliquid wallet in real-time using gRPC block fills streaming.

## ⚠️ IMPORTANT WARNINGS

- **This bot trades with REAL money on MAINNET**
- **You can LOSE money** - crypto trading is risky
- **Not financial advice** - use at your own risk
- **Start with DRY RUN mode** - always test first
- **Never share your private keys** - keep them secure
- **Understand the code** before running it
- **Monitor your positions** - don't leave it unattended

## ✨ Features

- 🎯 **Mirror any wallet** - Copy trades from any Hyperliquid address
- 💰 **Percentage-based sizing** - Trade with a % of your account
- 🛡️ **Safety limits** - Min/max position size controls
- 🔵 **Dry run mode** - Test without risking real money
- 🎛️ **Coin filtering** - Only copy specific coins
- ⚡ **Real-time streaming** - Uses gRPC for instant updates
- 📊 **Simple & clean code** - Easy to understand and modify
- 🔴 **Live trading** - Integrated with Hyperliquid Python SDK for real order placement
- 💼 **Real account value** - Fetches live account balance for accurate position sizing

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Python 3.8 or higher
python3 --version

# Install dependencies
pip install -r requirements.txt
```

### 2. Copy gRPC Proto Files

```bash
# Copy these files from the python/ directory:
cp ../python/hyperliquid.proto .
cp ../python/hyperliquid_pb2.py .
cp ../python/hyperliquid_pb2_grpc.py .
```

### 3. Configure Settings

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your settings
nano .env  # or use your preferred editor
```

**Required settings:**
```env
# The wallet you want to copy
TARGET_WALLET_ADDRESS=0x...

# What % of your account to use
COPY_PERCENTAGE=10.0

# Start in dry-run mode for safety
DRY_RUN=true
```

**For live trading (after testing):**
```env
# Your Hyperliquid credentials
HYPERLIQUID_PRIVATE_KEY=your_private_key_here
HYPERLIQUID_WALLET_ADDRESS=your_wallet_address_here

# Enable live trading (USE WITH CAUTION)
DRY_RUN=false
```

### 4. Run the Bot

```bash
# Make it executable
chmod +x copy_trader.py

# Run in dry-run mode (safe, no real trades)
python3 copy_trader.py
```

## 📋 Configuration Options

### Environment Variables

| Variable | Description | Example | Default |
|----------|-------------|---------|---------|
| `TARGET_WALLET_ADDRESS` | Wallet to copy trade | `0x1234...` | **Required** |
| `COPY_PERCENTAGE` | % of your account to use | `10.0` | `10.0` |
| `DRY_RUN` | Enable dry-run mode | `true`/`false` | `true` |
| `MAX_POSITION_SIZE_USD` | Max position size | `100` | `100` |
| `MIN_POSITION_SIZE_USD` | Min position size | `10` | `10` |
| `ENABLED_COINS` | Coins to copy (comma-separated) | `BTC,ETH` | All coins |
| `HYPERLIQUID_ENDPOINT` | gRPC endpoint | `hl-cendars.n.dwellir.com:443` | Set in .env |

### Copy Percentage Explained

If `COPY_PERCENTAGE=10`:
- Target trades $1000 → You trade $100 (10% of your account)
- Target trades $500 → You trade $50
- Respects `MAX_POSITION_SIZE_USD` and `MIN_POSITION_SIZE_USD` limits

## 🔒 Safety Features

### 1. Dry Run Mode (Default)
```env
DRY_RUN=true
```
- Watches trades but doesn't execute them
- Shows what would happen
- Perfect for testing

### 2. Position Limits
```env
MAX_POSITION_SIZE_USD=100  # Never risk more than this
MIN_POSITION_SIZE_USD=10   # Skip tiny positions
```

### 3. Coin Filtering
```env
# Only copy BTC and ETH trades
ENABLED_COINS=BTC,ETH

# Or leave empty to copy all coins
ENABLED_COINS=
```

### 4. 5-Second Warning
When live trading is enabled, the bot gives you 5 seconds to cancel before starting.

## 📊 How It Works

1. **Connects to gRPC** - Streams block fills in real-time
2. **Watches target wallet** - Filters for your chosen address
3. **Calculates position size** - Based on your copy percentage and real account value
4. **Applies safety limits** - Checks min/max bounds
5. **Executes trade** - Places the same trade on your account via Hyperliquid SDK
6. **Tracks fills** - Prevents duplicate orders

### Live Trading Integration

When `DRY_RUN=false`, the bot:
- Initializes the Hyperliquid Python SDK with your credentials
- Fetches your real account balance from the API
- Places actual limit orders using `exchange.order()`
- Reports order status (resting/filled)
- Uses GTC (Good Til Canceled) time-in-force

**Order Types:**
- All orders are limit orders at the same price as the target wallet
- Time-in-force: GTC (Good Til Canceled)
- Orders will rest on the book until filled or manually canceled

## 💡 Example Usage

### Example 1: Copy 10% of a whale's BTC/ETH trades

```env
TARGET_WALLET_ADDRESS=0x1234567890abcdef1234567890abcdef12345678
COPY_PERCENTAGE=10.0
ENABLED_COINS=BTC,ETH
MAX_POSITION_SIZE_USD=500
MIN_POSITION_SIZE_USD=50
DRY_RUN=true
```

**Output:**
```
🎯 Target wallet trade detected:
   Coin: BTC
   Side: B
   Size: 1.5
   Price: $60000

📋 Copy Trade Signal:
   Coin: BTC
   Side: BUY
   Target size: 1.5
   Our size: 0.15
   Price: $60000
   Estimated cost: $9000

🔵 DRY RUN: Would place B order for 0.15 BTC @ $60000
```

### Example 2: Live trading with small positions

```env
TARGET_WALLET_ADDRESS=0xabcdef...
COPY_PERCENTAGE=5.0
MAX_POSITION_SIZE_USD=100
MIN_POSITION_SIZE_USD=20
DRY_RUN=false  # ⚠️ REAL TRADING
```

## 🛠️ Troubleshooting

### "No .env file found"
```bash
cp .env.example .env
# Then edit .env with your settings
```

### "HYPERLIQUID_PRIVATE_KEY is required"
- You need your private key for live trading
- Get it from your Hyperliquid account settings
- **Never share this with anyone**
- Only needed when `DRY_RUN=false`

### "Failed to initialize Hyperliquid SDK"
- Check your internet connection
- Verify your private key is correct
- Make sure you have enough balance

### Not seeing any trades
- Verify `TARGET_WALLET_ADDRESS` is correct
- Make sure the target wallet is actively trading
- Check that you're watching the right coins (ENABLED_COINS)

## 🔐 Security Best Practices

1. **Use a dedicated trading account** - Don't use your main wallet
2. **Start with small amounts** - Test with minimal funds first
3. **Keep private keys secure** - Never commit .env to git
4. **Monitor regularly** - Don't leave it running unattended for long
5. **Use API keys if possible** - Some exchanges support read-only keys
6. **Review the code** - Understand what it does before running

## 📝 Code Structure

```
copy-trading-bot/
├── copy_trader.py       # Main bot script
├── requirements.txt     # Python dependencies
├── .env.example         # Example configuration
├── .env                 # Your configuration (create this)
├── hyperliquid.proto    # gRPC protocol definition
├── hyperliquid_pb2.py   # Generated gRPC code
└── README.md            # This file
```

### Key Functions

- `CopyTradingBot.__init__()` - Initialize bot and validate config
- `stream_block_fills()` - Connect to gRPC and stream fills
- `process_fill()` - Check if fill is from target wallet
- `calculate_order_size()` - Calculate position size based on %
- `execute_copy_trade()` - Place the mirror trade

## ⚡ Advanced Usage

### Custom Order Modifications

Edit `execute_copy_trade()` to customize:
- Order type (limit vs market)
- Price adjustments (e.g., 0.1% better price)
- Stop loss / take profit
- Time-based filters

### Multiple Wallets

Run multiple instances with different .env files:
```bash
DRY_RUN=true TARGET_WALLET_ADDRESS=0x123... python3 copy_trader.py &
DRY_RUN=true TARGET_WALLET_ADDRESS=0xabc... python3 copy_trader.py &
```

## 📚 Resources

- [Hyperliquid API Docs](https://hyperliquid.gitbook.io/)
- [Hyperliquid Python SDK](https://github.com/hyperliquid-dex/hyperliquid-python-sdk)
- [gRPC Documentation](https://grpc.io/docs/)

## ⚖️ Legal Disclaimer

This software is provided "as is", without warranty of any kind. Use at your own risk. The authors are not responsible for any losses incurred. This is not financial advice. Crypto trading is risky and you can lose money.

## 📄 License

MIT License - Feel free to modify and use as you wish.

---

**Ready to start?**

1. Copy `.env.example` to `.env`
2. Set your `TARGET_WALLET_ADDRESS`
3. Keep `DRY_RUN=true` while testing
4. Run: `python3 copy_trader.py`
5. Watch it work in dry-run mode
6. Once confident, switch to live trading

Good luck! 🍀
