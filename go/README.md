# Hyperliquid gRPC Go Examples

Simple Go examples for streaming data from Hyperliquid's gRPC API.

## What's Included

Three working examples:

- **Stream Blocks** - Real-time blockchain blocks with transaction details
- **Stream Block Fills** - Real-time trade fills and execution data
- **Get OrderBook Snapshot** - Retrieve a single orderbook snapshot (requires dedicated endpoint)

## Quick Start

```bash
# 1. Setup (one-time)
make setup

# 2. Configure endpoint
cp .env.example .env
# Edit .env and set HYPERLIQUID_ENDPOINT

# 3. Run examples
make run-blocks       # Stream blocks
make run-fills        # Stream fills
make run-orderbook    # Get orderbook snapshot (dedicated endpoints only)
```

## Requirements

- Go 1.21+
- protoc (Protocol Buffers compiler)

## Configuration

Create a `.env` file:

```bash
# Required: Your gRPC endpoint with port
HYPERLIQUID_ENDPOINT=your-endpoint:443

# Optional: API key (only if your endpoint requires authentication)
# API_KEY=your-api-key-here
```

**Note**: The API key is optional. Public endpoints work without authentication.

## Examples

### Stream Blocks

```bash
make run-blocks
# or
go run stream_blocks.go
```

Displays:
- Block proposer
- Action types (orders, cancels, etc.)
- Action counts
- Order statuses (success/error)

### Stream Block Fills

```bash
make run-fills
# or
go run stream_block_fills.go
```

Displays:
- Block height and timestamp
- Fill details (symbol, side, price, size)
- Trade execution data

### Get OrderBook Snapshot

```bash
make run-orderbook
# or
go run get_orderbook_snapshot.go
```

Displays:
- Timestamp of snapshot
- Total number of price levels
- Sample bid/ask levels
- Response size

**Important**: This method requires a **dedicated endpoint** that supports large messages. Public endpoints may have a 64MB message size limit which can cause this method to fail if the orderbook is large. This method works best with dedicated/private endpoints configured for larger message sizes.

## Setup Details

### First Time Setup

```bash
# Install protobuf compiler plugins
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

# Ensure GOPATH/bin is in your PATH
export PATH="$PATH:$(go env GOPATH)/bin"

# Generate protobuf code and install dependencies
make setup
```

### Make Commands

- `make setup` - One-time setup (install tools, generate proto, install deps)
- `make run-blocks` - Stream blockchain blocks
- `make run-fills` - Stream trade fills
- `make run-orderbook` - Get orderbook snapshot (dedicated endpoints only)
- `make build` - Build standalone binaries
- `make clean` - Remove build artifacts

## Building Binaries

```bash
make build
```

This creates three executables:
- `./stream_blocks`
- `./stream_block_fills`
- `./get_orderbook_snapshot`

## Project Structure

```
.
├── stream_blocks.go           # Stream blockchain blocks
├── stream_block_fills.go      # Stream trade fills
├── get_orderbook_snapshot.go  # Get orderbook snapshot
├── hyperliquid.proto          # Protocol definition
├── internal/api/              # Generated gRPC code
├── .env.example               # Configuration template
└── Makefile                   # Build automation
```

## Troubleshooting

**"missing port in address"**
```bash
# Wrong
HYPERLIQUID_ENDPOINT=api.example.com

# Correct
HYPERLIQUID_ENDPOINT=api.example.com:443
```

**"no required module provides package"**
```bash
make setup  # Generates missing protobuf code
```

**"protoc-gen-go: program not found"**
```bash
export PATH="$PATH:$(go env GOPATH)/bin"
```

## API Methods

The examples use these gRPC methods:

- `StreamBlocks(Timestamp) → stream Block` - ✅ Works on all endpoints
- `StreamBlockFills(Timestamp) → stream BlockFills` - ✅ Works on all endpoints
- `GetOrderBookSnapshot(Timestamp) → OrderBookSnapshot` - ⚠️ Requires dedicated endpoint

### Method Details

**Streaming methods** (`StreamBlocks`, `StreamBlockFills`):
- Accept a timestamp parameter (use `0` for latest/live data)
- Return a stream of messages
- Support graceful shutdown with Ctrl+C
- Handle large messages (150MB+)
- Work on both public and authenticated endpoints

**Snapshot method** (`GetOrderBookSnapshot`):
- Returns a single snapshot of the orderbook
- May fail on public endpoints with 64MB limit
- Best used with dedicated endpoints configured for large messages
- Useful for getting point-in-time orderbook state

## License

See repository root for license information.
