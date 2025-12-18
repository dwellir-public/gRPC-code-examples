# Python Examples - Hyperliquid gRPC API

This folder contains Python examples for connecting to Hyperliquid's gRPC API.

## Directory Structure

```
python/
├── v1/                          # v1 API examples (currently deployed)
│   ├── hyperliquid.proto
│   ├── hyperliquid_pb2.py
│   ├── hyperliquid_pb2_grpc.py
│   ├── stream_blocks.py         # Stream raw blocks
│   ├── stream_fills.py          # Stream trade fills
│   ├── stream_liquidations.py   # Detect liquidation events
│   ├── stream_twap.py           # Filter TWAP orders/cancels
│   ├── stream_transfers.py      # Asset transfers (USD, spot, withdrawals)
│   └── stream_account_mgmt.py   # Account management events
├── v2/                          # v2 API examples (future)
│   ├── hyperliquid.proto
│   ├── hyperliquid_pb2.py
│   ├── hyperliquid_pb2_grpc.py
│   ├── stream_blocks.py
│   ├── stream_fills.py
│   ├── stream_liquidations.py
│   ├── stream_twap.py
│   ├── stream_transfers.py
│   ├── stream_account_mgmt.py
│   ├── stream_orderbook_snapshots.py
│   └── get_orderbook_snapshot.py
├── .env.example
├── requirements.txt
└── README.md
```

## API Versions

### v1 API (Currently Deployed)
- Uses `Timestamp` message for positioning (timestamp only)
- Service: `HyperLiquidL1Gateway`
- Methods: `StreamBlocks`, `StreamBlockFills`, `StreamOrderBookSnapshots`, `GetOrderBookSnapshot`

### v2 API (Future)
- Uses `Position` message with `oneof { timestamp_ms, block_height }`
- Service: `HyperliquidL1Gateway`
- Methods: `StreamBlocks`, `StreamFills`, `StreamOrderbookSnapshots`, `GetOrderBookSnapshot`, `GetBlock`, `GetFills`
- **New feature**: Block height positioning

## Available Examples

### Trading Data
| Example | Description |
|---------|-------------|
| `stream_blocks.py` | Stream raw L1 blocks with action breakdown |
| `stream_fills.py` | Stream trade fills with market summaries |
| `stream_liquidations.py` | Detect liquidation events from fills stream |
| `stream_twap.py` | Filter TWAP (Time-Weighted Average Price) orders and cancels |

### Asset Transfers (`stream_transfers.py`)
Streams asset transfer events including:
- `usdSend` - Send USD to another address
- `spotSend` - Send spot tokens to another address
- `withdraw3` / `withdraw` - Withdraw funds from L1
- `usdClassTransfer` - Transfer between perp and spot
- `vaultTransfer` - Deposit/withdraw from vaults
- `subAccountTransfer` - Transfer between sub-accounts

### Account Management (`stream_account_mgmt.py`)
Streams account management events including:
- `updateLeverage` - Change leverage for a position
- `updateIsolatedMargin` - Adjust isolated margin
- `setReferrer` - Set referral code
- `approve` - Approve an agent to trade on your behalf
- `createSubAccount` - Create a new sub-account
- `vaultCreate` / `vaultModify` - Vault management
- `evmUserModify` - Link/modify EVM address
- `scheduleCancel` - Schedule order cancellation
- `cDeposit` / `cWithdraw` - Cross-chain deposits/withdrawals

## Setup

1. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env file and set your endpoint and API key
```

Example `.env` file:
```
HYPERLIQUID_ENDPOINT=api-hyperliquid-mainnet-grpc.n.dwellir.com
API_KEY=your-api-key-here
```

4. Generate protobuf files (if needed):
```bash
# For v1
cd v1 && python -m grpc_tools.protoc --proto_path=. --python_out=. --grpc_python_out=. hyperliquid.proto

# For v2
cd v2 && python -m grpc_tools.protoc --proto_path=. --python_out=. --grpc_python_out=. hyperliquid.proto
```

## Usage

### v1 Examples (Current Server)

```bash
cd v1

# Stream blocks
python stream_blocks.py                    # From latest
python stream_blocks.py --minutes-ago 10   # From 10 minutes ago
python stream_blocks.py -v                 # Show action breakdown

# Stream fills
python stream_fills.py                     # From latest
python stream_fills.py --minutes-ago 10    # From 10 minutes ago
python stream_fills.py -vv                 # Show all fills with details

# Stream liquidations
python stream_liquidations.py              # From latest
python stream_liquidations.py -m 60        # Look back 1 hour
python stream_liquidations.py -c 10        # Stop after 10 liquidations

# Stream TWAP orders
python stream_twap.py                      # From latest
python stream_twap.py --minutes-ago 120    # Look back 2 hours
python stream_twap.py -v                   # Show order details

# Stream asset transfers
python stream_transfers.py                 # From latest
python stream_transfers.py -m 30           # Look back 30 minutes
python stream_transfers.py -vv             # Show full addresses

# Stream account management
python stream_account_mgmt.py              # From latest
python stream_account_mgmt.py -m 60        # Look back 1 hour
python stream_account_mgmt.py -v           # Show more details
```

### v2 Examples (When Server Updated)

```bash
cd v2

# All v1 features plus block height positioning:
python stream_fills.py --block 831000000   # From specific block height
python stream_blocks.py -b 831000000       # Short form

# Stream orderbook snapshots
python stream_orderbook_snapshots.py --minutes-ago 5

# Get single orderbook snapshot
python get_orderbook_snapshot.py --timestamp 1702800000000
```

## Command Line Options

All streaming examples support:
- `-t, --timestamp` - Start from specific timestamp (ms since epoch)
- `-m, --minutes-ago` - Start from X minutes ago
- `-c, --count` - Number of items to receive before stopping
- `-v` - Increase verbosity (can stack: -v, -vv, -vvv)
- `--stats-interval` - Print stats every N blocks (default: 100)

v2 examples additionally support:
- `-b, --block` - Start from specific block height

## Verbosity Levels

| Level | Flag | Output |
|-------|------|--------|
| 0 | (none) | Basic event info |
| 1 | `-v` | + Additional details (amounts, directions) |
| 2 | `-vv` | + Full addresses and metadata |
| 3 | `-vvv` | + Raw JSON keys for debugging |

## Example Output

### stream_blocks.py
```
--- Block #831,234,567 (156 actions) ---
Time: 2024-12-17 10:30:45.123 UTC | Latency: 52ms | Size: 45.2 KB
Actions:
  order: 142
  cancel: 8
  updateLeverage: 4
  usdSend: 2
```

### stream_liquidations.py
```
🔥 LIQUIDATION #1: BTC LONG
   Size: 0.0234 @ $104,250.50
   P&L: $-1,234.56 | Close Long
   Block: #831,234,567
```

### stream_transfers.py
```
💵 USD SEND #1
   Amount: $10000.00
   To: 0x1234abcd...5678efgh
   Block: #831,234,567

🏦 WITHDRAWAL #2
   Amount: $5000.00
   To: 0xabcd1234...efgh5678
```

### stream_twap.py
```
📈 TWAP ORDER #1: ETH BUY
   Size: 10.5 over 60 minutes
   Options: [Randomized]
   Block: #831,234,567
```

### stream_account_mgmt.py
```
⚙️ LEVERAGE UPDATE #1: BTC
   Leverage: 20x (Cross)
   Block: #831,234,567

✅ AGENT APPROVAL #2
   Max fee rate: 0.001
   Builder: 0x1234abcd...5678efgh
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `HYPERLIQUID_ENDPOINT` | gRPC server endpoint | `api-hyperliquid-mainnet-grpc.n.dwellir.com:443` |
| `API_KEY` | API key for authentication | (none) |

## Dependencies

- `grpcio>=1.60.0` - gRPC client library
- `grpcio-tools>=1.60.0` - Protocol buffer compiler tools
- `python-dotenv>=1.0.0` - Environment variable loading

## Troubleshooting

### Import errors for protobuf files
Regenerate the protobuf files in the appropriate directory (v1/ or v2/).

### "unknown service" errors
Make sure you're using the correct API version for the server:
- If server returns "unknown service hyperliquid_l1_gateway.v2", use v1 examples
- The v2 API will be available when the server is updated

### 403 Forbidden errors
Ensure your `API_KEY` is set correctly in the `.env` file.

### No events found
Some events (liquidations, TWAP orders) are relatively rare. Use `--minutes-ago` to look back through historical data:
```bash
python stream_liquidations.py --minutes-ago 120  # Look back 2 hours
python stream_twap.py -m 60                      # Look back 1 hour
```

### RESOURCE_EXHAUSTED errors
For orderbook snapshots, the message size limit may need to be increased. The examples already set a large limit (150MB), but if you encounter issues, check the `MAX_MESSAGE_SIZE` constant.
