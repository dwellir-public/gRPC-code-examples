import grpc
import json
import signal
import sys
import os
from datetime import datetime
from dotenv import load_dotenv
import hyperliquid_pb2
import hyperliquid_pb2_grpc

# Load environment variables
load_dotenv()


def stream_block_fills():
    endpoint = os.getenv('HYPERLIQUID_ENDPOINT')
    api_key = os.getenv('API_KEY')

    if not endpoint:
        print("Error: HYPERLIQUID_ENDPOINT environment variable is required.")
        print("Please create a .env file from .env.example and set your endpoint.")
        sys.exit(1)

    if not api_key:
        print("Error: API_KEY environment variable is required.")
        print("Please set your API key in the .env file.")
        sys.exit(1)

    print('🚀 Hyperliquid Python gRPC Client - Stream Block Fills')
    print('===================================================')
    print(f'📡 Endpoint: {endpoint}\n')

    # Create SSL credentials
    credentials = grpc.ssl_channel_credentials()

    # Create channel with options
    options = [
        ('grpc.max_receive_message_length', 150 * 1024 * 1024),  # 150MB max
    ]

    # Prepare metadata with API key
    metadata = [('x-api-key', api_key)]

    print('🔌 Connecting to gRPC server...')
    with grpc.secure_channel(endpoint, credentials, options=options) as channel:
        # Create client stub
        client = hyperliquid_pb2_grpc.HyperLiquidL1GatewayStub(channel)
        print('✅ Connected successfully!\n')

        # Create request - 0 means latest/current block fills
        request = hyperliquid_pb2.Timestamp(timestamp=0)

        print('📥 Starting block fills stream...')
        print('Press Ctrl+C to stop streaming\n')

        block_fills_count = 0

        # Set up signal handler for graceful shutdown
        def signal_handler(sig, frame):
            print('\n🛑 Stopping stream...')
            print(f'📊 Total block fills received: {block_fills_count}')
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)

        try:
            # Start streaming block fills with metadata
            for response in client.StreamBlockFills(request, metadata=metadata):
                block_fills_count += 1
                print(f'\n===== BLOCK FILLS #{block_fills_count} =====')
                print(f'📦 Response size: {len(response.data)} bytes')

                # Process each block fills response
                process_block_fills(response.data, block_fills_count)

                print('\n' + '─' * 50)

        except grpc.RpcError as e:
            print(f'❌ Stream error: {e}')
        except KeyboardInterrupt:
            print('\n🛑 Stopping stream...')

        print(f'\n📊 Total block fills received: {block_fills_count}')


def process_block_fills(data, block_fills_num):
    try:
        # Parse JSON
        block_fills = json.loads(data.decode('utf-8'))

        print(f'💰 BLOCK FILLS #{block_fills_num} DETAILS')
        print('========================')

        # Display block height if available
        if 'height' in block_fills:
            print(f'📏 Block Height: {block_fills["height"]}')

        # Display timestamp
        if 'time' in block_fills:
            timestamp = block_fills['time']
            if isinstance(timestamp, (int, float)):
                # Convert from milliseconds to seconds if needed
                if timestamp > 10**10:  # Likely milliseconds
                    timestamp = timestamp / 1000
                dt = datetime.fromtimestamp(timestamp)
                print(f'⏰ Time: {dt.strftime("%Y-%m-%d %H:%M:%S UTC")}')

        # Display fills data
        if 'fills' in block_fills and isinstance(block_fills['fills'], list):
            fills = block_fills['fills']
            print(f'📋 Total Fills: {len(fills)}')

            # Show first few fill details
            max_fills = min(3, len(fills))

            for i in range(max_fills):
                fill = fills[i]
                fill_info = f'  • FILL {i + 1}: '

                if isinstance(fill, dict):
                    if 'symbol' in fill:
                        fill_info += f'Symbol: {fill["symbol"]}'
                    if 'side' in fill:
                        fill_info += f', Side: {fill["side"]}'
                    if 'price' in fill:
                        fill_info += f', Price: {fill["price"]}'
                    if 'size' in fill:
                        fill_info += f', Size: {fill["size"]}'
                    if 'hash' in fill:
                        fill_info += f', Hash: {fill["hash"][:12]}...'
                else:
                    fill_info += str(fill)

                print(fill_info)

            if len(fills) > max_fills:
                print(f'  ... and {len(fills) - max_fills} more fills')

        # Display any other interesting fields
        print('\n📊 Block Fills Summary:')
        if isinstance(block_fills, dict):
            for key, value in block_fills.items():
                if key in ['height', 'time', 'fills']:
                    # Already displayed above
                    continue

                # Display other fields
                if isinstance(value, (dict, list)):
                    print(f'• {key}: {json.dumps(value, separators=(",", ":"))[:100]}...')
                else:
                    print(f'• {key}: {value}')
        elif isinstance(block_fills, list):
            print(f'• Block fills is a list with {len(block_fills)} items')
            # Display first few items if it's a simple list
            if len(block_fills) > 0:
                print(f'• First item type: {type(block_fills[0]).__name__}')

    except json.JSONDecodeError as e:
        print(f'❌ Failed to parse JSON: {e}')
        print(f'Raw data (first 200 bytes): {data[:200]}')
    except Exception as e:
        print(f'❌ Error processing block fills: {e}')


if __name__ == '__main__':
    stream_block_fills()