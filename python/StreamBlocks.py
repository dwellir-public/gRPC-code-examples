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


def stream_blocks():
    endpoint = os.getenv('HYPERLIQUID_ENDPOINT')
    if not endpoint:
        print("Error: HYPERLIQUID_ENDPOINT environment variable is required.")
        print("Please create a .env file from .env.example and set your endpoint.")
        sys.exit(1)

    print('🚀 Hyperliquid Python gRPC Client - Stream Blocks')
    print('===============================================')
    print(f'📡 Endpoint: {endpoint}\n')

    # Create SSL credentials
    credentials = grpc.ssl_channel_credentials()

    # Create channel with options
    options = [
        ('grpc.max_receive_message_length', 150 * 1024 * 1024),  # 150MB max
    ]

    print('🔌 Connecting to gRPC server...')
    with grpc.secure_channel(endpoint, credentials, options=options) as channel:
        # Create client stub
        client = hyperliquid_pb2_grpc.HyperLiquidL1GatewayStub(channel)
        print('✅ Connected successfully!\n')

        # Create request - 0 means latest/current blocks
        request = hyperliquid_pb2.Timestamp(timestamp=0)

        print('📥 Starting block stream...')
        print('Press Ctrl+C to stop streaming\n')

        block_count = 0

        # Set up signal handler for graceful shutdown
        def signal_handler(sig, frame):
            print('\n🛑 Stopping stream...')
            print(f'📊 Total blocks received: {block_count}')
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)

        try:
            # Start streaming blocks
            for response in client.StreamBlocks(request):
                block_count += 1
                print(f'\n===== BLOCK #{block_count} =====')
                print(f'📦 Response size: {len(response.data)} bytes')

                # Process each block
                process_block(response.data, block_count)

                print('\n' + '─' * 50)

        except grpc.RpcError as e:
            print(f'❌ Stream error: {e}')
        except KeyboardInterrupt:
            print('\n🛑 Stopping stream...')

        print(f'\n📊 Total blocks received: {block_count}')


def process_block(data, block_num):
    try:
        # Parse JSON
        block = json.loads(data.decode('utf-8'))

        print(f'🧱 BLOCK #{block_num} DETAILS')
        print('===================')

        # Display block height
        if 'height' in block:
            print(f'📏 Height: {block["height"]}')

        # Display timestamp
        if 'time' in block:
            timestamp = block['time']
            if isinstance(timestamp, (int, float)):
                # Convert from milliseconds to seconds if needed
                if timestamp > 10**10:  # Likely milliseconds
                    timestamp = timestamp / 1000
                dt = datetime.fromtimestamp(timestamp)
                print(f'⏰ Time: {dt.strftime("%Y-%m-%d %H:%M:%S UTC")}')

        # Display hash if available
        if 'hash' in block:
            print(f'🔗 Hash: {block["hash"]}')

        # Display number of transactions
        if 'txs' in block and isinstance(block['txs'], list):
            txs = block['txs']
            print(f'📋 Transactions: {len(txs)}')

            # Show first few transaction details
            max_txs = min(3, len(txs))

            for i in range(max_txs):
                tx = txs[i]
                tx_info = f'  • TX {i + 1}: '

                if isinstance(tx, dict):
                    if 'type' in tx:
                        tx_info += f'Type: {tx["type"]}'
                    if 'hash' in tx:
                        tx_info += f', Hash: {tx["hash"][:12]}...'
                else:
                    tx_info += str(tx)

                print(tx_info)

            if len(txs) > max_txs:
                print(f'  ... and {len(txs) - max_txs} more transactions')

        # Display any other interesting fields
        print('\n📊 Block Summary:')
        for key, value in block.items():
            if key in ['height', 'time', 'hash', 'txs']:
                # Already displayed above
                continue

            # Display other fields
            if isinstance(value, (dict, list)):
                print(f'• {key}: {json.dumps(value, separators=(",", ":"))[:100]}...')
            else:
                print(f'• {key}: {value}')

    except json.JSONDecodeError as e:
        print(f'❌ Failed to parse JSON: {e}')
        print(f'Raw data (first 200 bytes): {data[:200]}')
    except Exception as e:
        print(f'❌ Error processing block: {e}')


if __name__ == '__main__':
    stream_blocks()