# Quick Setup Guide 🚀

## Step 1: Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials:
# HYPERLIQUID_ENDPOINT=your-endpoint:443
# API_KEY=your-api-key
```

## Step 2: Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Optional: Configure WebSocket URL
cp .env.example .env
```

## Step 3: Start the Application

### Option A: Manual Start (Recommended)

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
python server.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### Option B: Using start script (Unix/Mac only)

```bash
chmod +x start.sh
./start.sh
```

## Step 4: Access the Application

Open your browser and navigate to:
```
http://localhost:3000
```

## Troubleshooting

### Backend Issues
- Verify `.env` file has correct credentials
- Check Python version: `python --version` (requires 3.8+)
- Try reinstalling dependencies: `pip install -r requirements.txt --force-reinstall`

### Frontend Issues
- Clear node_modules: `rm -rf node_modules && npm install`
- Check Node version: `node --version` (requires 16+)
- Verify backend is running on port 8080

### No Liquidations Appearing
- This is normal! Liquidations appear only when they occur on-chain
- Check backend console for "Connected to Hyperliquid gRPC stream" message
- Verify your API key has proper permissions

## What You'll See

1. **Connection Status**: Top-right indicator showing live connection
2. **Stats Panel**: Four cards showing:
   - Total liquidations count
   - Total volume liquidated
   - Total P&L from liquidations
   - Average position size
3. **Liquidation Feed**: Real-time cards displaying each liquidation with:
   - Coin/token symbol
   - Direction (Long/Short liquidation)
   - Price and size
   - P&L and fees
   - User address and transaction hash
   - Timestamp

## Next Steps

- Monitor liquidations in real-time
- Analyze patterns in liquidation events
- Track volume and P&L statistics
- Customize the UI to your preferences

Enjoy tracking liquidations! 🔥
