import grpc
import json
import asyncio
import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv
from aiohttp import web
import aiohttp
import hyperliquid_pb2
import hyperliquid_pb2_grpc

# Load environment variables
load_dotenv()

# Store connected WebSocket clients
connected_clients = set()

async def handle_websocket(request):
    """Handle WebSocket connections from frontend clients"""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    connected_clients.add(ws)
    print(f'✅ New client connected. Total clients: {len(connected_clients)}')

    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data == 'ping':
                    await ws.send_str('pong')
            elif msg.type == aiohttp.WSMsgType.ERROR:
                print(f'❌ WebSocket error: {ws.exception()}')
    finally:
        connected_clients.discard(ws)
        print(f'👋 Client disconnected. Total clients: {len(connected_clients)}')

    return ws

async def broadcast_liquidation(liquidation_data):
    """Broadcast liquidation event to all connected clients"""
    if not connected_clients:
        return

    message = json.dumps(liquidation_data)
    disconnected = set()

    for ws in connected_clients:
        try:
            await ws.send_str(message)
        except Exception as e:
            print(f'❌ Error sending to client: {e}')
            disconnected.add(ws)

    # Remove disconnected clients
    connected_clients.difference_update(disconnected)

def extract_liquidations(block_fills_data):
    """Extract liquidation events from block fills data"""
    liquidations = []

    try:
        # Parse the incoming data
        block_fills = json.loads(block_fills_data.decode('utf-8'))

        # Stream sends fills as [user_address, fill_data] pairs
        if isinstance(block_fills, list) and len(block_fills) == 2:
            user_address, fill_data = block_fills

            # Check if this fill has a liquidation
            if 'liquidation' in fill_data:
                liquidation_info = fill_data.get('liquidation', {})
                liquidated_user = liquidation_info.get('liquidatedUser', '')
                direction = fill_data.get('dir', '')

                # Only include closing positions where user matches liquidated user
                is_closing = 'close' in direction.lower()
                is_liquidated_user = user_address.lower() == liquidated_user.lower()

                if is_closing and is_liquidated_user:
                    liquidation_event = {
                        'userAddress': user_address,
                        'coin': fill_data.get('coin'),
                        'price': fill_data.get('px'),
                        'size': fill_data.get('sz'),
                        'side': fill_data.get('side'),
                        'timestamp': fill_data.get('time'),
                        'direction': direction,
                        'closedPnl': fill_data.get('closedPnl', '0'),
                        'liquidation': liquidation_info
                    }
                    liquidations.append(liquidation_event)

    except Exception as e:
        print(f'❌ Error extracting liquidations: {e}')

    return liquidations

async def stream_liquidations():
    """Connect to gRPC stream and broadcast liquidations"""
    endpoint = os.getenv('HYPERLIQUID_ENDPOINT')
    api_key = os.getenv('API_KEY')

    if not endpoint or not api_key:
        print("❌ Error: HYPERLIQUID_ENDPOINT and API_KEY required in .env file")
        sys.exit(1)

    print('🚀 Hyperliquid Liquidation Tracker')
    print(f'📡 Endpoint: {endpoint}\n')

    # Setup gRPC connection
    credentials = grpc.ssl_channel_credentials()
    options = [('grpc.max_receive_message_length', 150 * 1024 * 1024)]
    metadata = [('x-api-key', api_key)]

    liquidation_count = 0
    block_count = 0
    start_time = time.time()

    while True:
        try:
            print('🔌 Connecting to gRPC server...')
            with grpc.secure_channel(endpoint, credentials, options=options) as channel:
                client = hyperliquid_pb2_grpc.HyperLiquidL1GatewayStub(channel)
                print('✅ Connected! Streaming block fills...\n')

                request = hyperliquid_pb2.Timestamp(timestamp=0)

                for response in client.StreamBlockFills(request, metadata=metadata):
                    block_count += 1

                    # Check for liquidations
                    liquidations = extract_liquidations(response.data)

                    if liquidations:
                        liquidation_count += len(liquidations)
                        for liq in liquidations:
                            print(f'🔥 LIQUIDATION #{liquidation_count}')
                            print(f'   {liq["coin"]}: {liq["size"]} @ ${liq["price"]}')
                            print(f'   P&L: ${liq["closedPnl"]} | {liq["direction"]}')
                            print(f'   User: {liq["userAddress"][:8]}...{liq["userAddress"][-6:]}\n')
                            await broadcast_liquidation(liq)

                    # Print stats every 10 seconds
                    if block_count % 800 == 0:
                        elapsed = time.time() - start_time
                        print(f'📊 {block_count:,} blocks | {liquidation_count} liquidations | {int(elapsed)}s')

                    await asyncio.sleep(0.01)

        except grpc.RpcError as e:
            print(f'❌ Connection error: {e}')
            print('🔄 Reconnecting in 5 seconds...\n')
            await asyncio.sleep(5)
        except Exception as e:
            print(f'❌ Error: {e}\n')
            await asyncio.sleep(5)

async def start_background_tasks(app):
    """Start the gRPC streaming task"""
    app['grpc_task'] = asyncio.create_task(stream_liquidations())

async def cleanup_background_tasks(app):
    """Cleanup tasks on shutdown"""
    app['grpc_task'].cancel()
    await app['grpc_task']

async def health_check(request):
    """Health check endpoint"""
    return web.json_response({
        'status': 'healthy',
        'clients': len(connected_clients),
        'timestamp': datetime.utcnow().isoformat()
    })

def main():
    app = web.Application()

    # Add routes
    app.router.add_get('/ws', handle_websocket)
    app.router.add_get('/health', health_check)

    # Add startup/cleanup handlers
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)

    port = int(os.getenv('PORT', 8080))
    print(f'\n🌐 Starting WebSocket server on port {port}...')

    web.run_app(app, host='0.0.0.0', port=port)

if __name__ == '__main__':
    main()
