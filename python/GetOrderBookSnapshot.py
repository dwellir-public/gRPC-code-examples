#!/usr/bin/env python3
"""
GetOrderBookSnapshot test implementation in Python
"""

import grpc
import json
from pathlib import Path
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the generated protobuf files to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import generated protobuf classes
try:
    import hyperliquid_pb2
    import hyperliquid_pb2_grpc
except ImportError:
    print("Error: Generated protobuf files not found. Run: python -m grpc_tools.protoc --proto_path=. --python_out=. --grpc_python_out=. hyperliquid.proto")
    sys.exit(1)


def test_get_orderbook_snapshot():
    """Test GetOrderBookSnapshot gRPC method"""

    endpoint = os.getenv('HYPERLIQUID_ENDPOINT')
    if not endpoint:
        print("Error: HYPERLIQUID_ENDPOINT environment variable is required.")
        print("Please create a .env file from .env.example and set your endpoint.")
        sys.exit(1)

    # Configure channel options for large messages (150MB)
    options = [
        ('grpc.max_receive_message_length', 150 * 1024 * 1024),  # 150MB
        ('grpc.max_send_message_length', 150 * 1024 * 1024),     # 150MB
    ]

    # Create secure channel
    with grpc.secure_channel(endpoint, grpc.ssl_channel_credentials(), options=options) as channel:
        # Create stub
        stub = hyperliquid_pb2_grpc.HyperLiquidL1GatewayStub(channel)

        print('Requesting OrderBook snapshot...\n')

        try:
            # Create request with timestamp 0 (current snapshot)
            request = hyperliquid_pb2.Timestamp(timestamp=0)

            # Make the gRPC call
            response = stub.GetOrderBookSnapshot(request)

            print('Received OrderBook snapshot response')

            # Parse the JSON data
            orderbook_data = json.loads(response.data)

            print('OrderBook Snapshot Data:')
            print('Keys:', list(orderbook_data.keys()))

            # Display sample of the data structure
            if 'levels' in orderbook_data and len(orderbook_data['levels']) > 0:
                print('\nSample levels (first 3):')
                print(json.dumps(orderbook_data['levels'][:3], indent=2))

            if 'time' in orderbook_data:
                print(f'\nSnapshot timestamp: {orderbook_data["time"]}')

            # Display data size info
            data_size_mb = len(response.data) / (1024 * 1024)
            print(f'\nResponse size: {data_size_mb:.2f} MB')

        except grpc.RpcError as e:
            print(f'gRPC Error: {e.code()}: {e.details()}')
        except json.JSONDecodeError as e:
            print(f'JSON Parse Error: {e}')
        except Exception as e:
            print(f'Unexpected error: {e}')


if __name__ == '__main__':
    test_get_orderbook_snapshot()