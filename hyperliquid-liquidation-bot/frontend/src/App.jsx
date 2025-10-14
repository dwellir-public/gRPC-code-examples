import { useState, useEffect, useRef } from 'react'
import { Activity, TrendingDown, DollarSign, Droplet, AlertCircle, Wifi, WifiOff } from 'lucide-react'
import LiquidationTable from './components/LiquidationTable'
import StatsPanel from './components/StatsPanel'
import './App.css'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8080/ws'

function App() {
  const [liquidations, setLiquidations] = useState([])
  const [connected, setConnected] = useState(false)
  const [stats, setStats] = useState({
    totalLiquidations: 0,
    totalVolume: 0,
    totalPnL: 0,
    averageSize: 0
  })
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)

  useEffect(() => {
    connectWebSocket()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [])

  const connectWebSocket = () => {
    try {
      const ws = new WebSocket(WS_URL)

      ws.onopen = () => {
        console.log('Connected to liquidation stream')
        setConnected(true)
      }

      ws.onmessage = (event) => {
        try {
          const liquidation = JSON.parse(event.data)

          // Check for duplicates before processing
          setLiquidations(prev => {
            // Deduplicate by hash + user address + size - unique combination
            const exists = prev.some(liq =>
              liq.hash === liquidation.hash &&
              liq.userAddress === liquidation.userAddress &&
              liq.size === liquidation.size
            )

            if (exists) {
              console.log('Duplicate liquidation filtered:', liquidation.hash)
              return prev
            }

            // Not a duplicate - update stats
            setStats(prevStats => {
              const size = parseFloat(liquidation.size) || 0
              const price = parseFloat(liquidation.price) || 0
              const pnl = parseFloat(liquidation.closedPnl) || 0
              const volume = size * price
              const newTotal = prevStats.totalLiquidations + 1

              return {
                totalLiquidations: newTotal,
                totalVolume: prevStats.totalVolume + volume,
                totalPnL: prevStats.totalPnL + pnl,
                averageSize: (prevStats.averageSize * prevStats.totalLiquidations + size) / newTotal
              }
            })

            const newLiquidations = [liquidation, ...prev].slice(0, 100)
            return newLiquidations
          })
        } catch (err) {
          console.error('Failed to parse liquidation data:', err)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }

      ws.onclose = () => {
        console.log('Disconnected from liquidation stream')
        setConnected(false)

        // Attempt to reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('Attempting to reconnect...')
          connectWebSocket()
        }, 3000)
      }

      wsRef.current = ws
    } catch (err) {
      console.error('Failed to connect:', err)
      setConnected(false)
    }
  }

  return (
    <div className="app">
      {/* Background gradient effects */}
      <div className="gradient-orb gradient-orb-1"></div>
      <div className="gradient-orb gradient-orb-2"></div>
      <div className="gradient-orb gradient-orb-3"></div>

      {/* Header */}
      <header className="header">
        <div className="header-content">
          <div className="header-left">
            <div className="logo">
              <Droplet size={32} className="logo-icon" />
              <h1>Hyperliquid Liquidations</h1>
            </div>
            <p className="subtitle">Real-time liquidation tracker</p>
          </div>
          <div className="connection-status">
            {connected ? (
              <>
                <Wifi size={20} />
                <span className="status-text connected">Live</span>
                <div className="status-indicator connected"></div>
              </>
            ) : (
              <>
                <WifiOff size={20} />
                <span className="status-text disconnected">Disconnected</span>
                <div className="status-indicator disconnected"></div>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Stats Panel */}
      <StatsPanel stats={stats} />

      {/* Main Content */}
      <main className="main-content">
        <div className="content-header">
          <h2>
            <Activity size={24} />
            Recent Liquidations
          </h2>
          <span className="liquidation-count">{liquidations.length} events</span>
        </div>

        {!connected && (
          <div className="alert">
            <AlertCircle size={20} />
            <span>Connecting to liquidation stream...</span>
          </div>
        )}

        {connected && liquidations.length === 0 && (
          <div className="empty-state">
            <TrendingDown size={48} className="empty-icon" />
            <h3>Waiting for liquidations...</h3>
            <p>No liquidation events yet. They will appear here as they happen.</p>
          </div>
        )}

        <LiquidationTable liquidations={liquidations} />
      </main>
    </div>
  )
}

export default App
