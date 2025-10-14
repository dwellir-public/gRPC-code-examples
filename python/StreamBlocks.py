import grpc
import json
import signal
import sys
import os
from datetime import datetime
from dotenv import load_dotenv
import hyperliquid_pb2
import hyperliquid_pb2_grpc
from pprint import pprint as pp

# Load environment variables
load_dotenv()


def stream_blocks():
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

    print('🚀 Hyperliquid Python gRPC Client - Stream Blocks')
    print('===============================================')
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
            # Start streaming blocks with metadata
            for response in client.StreamBlocks(request, metadata=metadata):
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


        # Count action types (counting individual orders within each action)
        action_type_counts = {}

        if 'abci_block' in block:
            abci_block = block['abci_block']
            if 'proposer' in abci_block:
                print(f'👤 Proposer: {abci_block["proposer"]}')
            if 'signed_action_bundles' in abci_block:
                if isinstance(abci_block['signed_action_bundles'], list):
                    for action_bundle in abci_block['signed_action_bundles']:
                        # Each action_bundle is [hash, data_object]
                        if isinstance(action_bundle, list) and len(action_bundle) > 1:
                            bundle_data = action_bundle[1]
                            if 'signed_actions' in bundle_data:
                                if isinstance(bundle_data['signed_actions'], list):
                                    for signed_action in bundle_data['signed_actions']:
                                        if 'action' in signed_action:
                                            action = signed_action['action']
                                            if isinstance(action, dict) and 'type' in action:
                                                action_type = action['type']
                                                # For order type, count the number of orders
                                                if action_type == 'order' and 'orders' in action:
                                                    if isinstance(action['orders'], list):
                                                        count = len(action['orders'])
                                                        action_type_counts[action_type] = action_type_counts.get(action_type, 0) + count
                                                    else:
                                                        action_type_counts[action_type] = action_type_counts.get(action_type, 0) + 1
                                                else:
                                                    # For other action types, count as 1
                                                    action_type_counts[action_type] = action_type_counts.get(action_type, 0) + 1

        total_actions = sum(action_type_counts.values())
        print(f'📋 Action types:')
        for action_type, count in action_type_counts.items():
            print(f'  • {action_type}: {count}')
        print(f'  Total actions: {total_actions}')

        # Count order statuses (success vs error) from resps.Full section
        success_count = 0
        error_count = 0

        if 'resps' in block:
            resps = block['resps']
            if isinstance(resps, dict) and 'Full' in resps:
                full_data = resps['Full']
                if isinstance(full_data, list):
                    for item in full_data:
                        # Each item is [hash, [entries...]]
                        if isinstance(item, list) and len(item) > 1:
                            entries = item[1]  # Skip the hash, get the second part
                            if isinstance(entries, list):
                                for entry in entries:
                                    if isinstance(entry, dict) and 'res' in entry:
                                        res = entry['res']
                                        if isinstance(res, dict) and 'response' in res:
                                            response = res['response']
                                            if isinstance(response, dict) and response.get('type') == 'order':
                                                if 'data' in response and 'statuses' in response['data']:
                                                    statuses = response['data']['statuses']
                                                    if isinstance(statuses, list):
                                                        for status in statuses:
                                                            if isinstance(status, dict):
                                                                if 'error' in status:
                                                                    error_count += 1
                                                                else:
                                                                    # Success status (resting, filled, etc.)
                                                                    success_count += 1

        total_statuses = success_count + error_count
        print(f'\n📊 Order Statuses:')
        print(f'  ✅ Success: {success_count}')
        print(f'  ❌ Error: {error_count}')
        print(f'  Total statuses: {total_statuses}')

        print(f'\n🔍 Match check: Actions={total_actions}, Statuses={total_statuses}, Match={total_actions == total_statuses}')

    except json.JSONDecodeError as e:
        print(f'❌ Failed to parse JSON: {e}')
        print(f'Raw data (first 200 bytes): {data[:200]}')
    except Exception as e:
        print(f'❌ Error processing block: {e}')


if __name__ == '__main__':
    stream_blocks()