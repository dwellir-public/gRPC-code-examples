# Python Examples - HyperLiquid gRPC Client

This folder contains Python implementations for connecting to HyperLiquid's gRPC API.

## Files

- `GetOrderBookSnapshot.py` - Get a single order book snapshot
- `StreamBlocks.py` - Stream real-time blocks data
- `StreamBlockFills.py` - Stream real-time block fills data
- `.env.example` - Environment configuration template
- `requirements.txt` - Python dependencies
- `hyperliquid.proto` - Protocol buffer definition

## Setup

1. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env file and set your HYPERLIQUID_ENDPOINT
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Generate protobuf files:
```bash
python -m grpc_tools.protoc --proto_path=. --python_out=. --grpc_python_out=. hyperliquid.proto
```

This will create:
- `hyperliquid_pb2.py` - Generated message classes
- `hyperliquid_pb2_grpc.py` - Generated service stubs

## Usage

### Get Order Book Snapshot
```bash
python GetOrderBookSnapshot.py
```
This will fetch a current order book snapshot (~95MB response) and display:
- Response size in MB
- JSON structure keys
- Sample data from the response

### Stream Blocks
```bash
python StreamBlocks.py
```
This will start streaming real-time block data from HyperLiquid.

### Stream Block Fills
```bash
python StreamBlockFills.py
```
This will start streaming real-time block fills data from HyperLiquid.

## Key Features

- **Large Message Support**: Configured for 150MB message limits to handle large responses
- **SSL/TLS Connection**: Secure connection to HyperLiquid endpoints
- **JSON Parsing**: Automatic parsing of protobuf bytes data to JSON
- **Error Handling**: Comprehensive error handling for gRPC, JSON, and network issues
- **Response Analytics**: Built-in response size reporting and data structure analysis

## Configuration

The examples connect to your configured endpoint (set via environment variable)

All clients are configured with:
```python
options = [
    ('grpc.max_receive_message_length', 150 * 1024 * 1024),  # 150MB
    ('grpc.max_send_message_length', 150 * 1024 * 1024),     # 150MB
]
```

## Dependencies

- `grpcio` - gRPC client library
- `grpcio-tools` - Protocol buffer compiler tools
- `python-dotenv` - Environment variable loading

## Troubleshooting

If you encounter import errors for the generated protobuf files, make sure you've run the protoc command to generate `hyperliquid_pb2.py` and `hyperliquid_pb2_grpc.py` files.