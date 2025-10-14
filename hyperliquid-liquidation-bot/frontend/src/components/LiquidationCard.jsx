import { TrendingDown, DollarSign, Clock, User, Hash } from 'lucide-react'
import './LiquidationCard.css'

function LiquidationCard({ liquidation }) {
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'N/A'
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const formatAddress = (address) => {
    if (!address) return 'N/A'
    return `${address.slice(0, 6)}...${address.slice(-4)}`
  }

  const formatHash = (hash) => {
    if (!hash) return 'N/A'
    return `${hash.slice(0, 10)}...${hash.slice(-8)}`
  }

  const formatNumber = (num) => {
    if (!num) return '0'
    const n = parseFloat(num)
    return n.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 4
    })
  }

  const formatPnL = (pnl) => {
    if (!pnl) return '0.00'
    const n = parseFloat(pnl)
    return n.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
      signDisplay: 'always'
    })
  }

  const isProfitable = parseFloat(liquidation.closedPnl || 0) >= 0
  const isLongLiquidation = liquidation.direction?.toLowerCase().includes('long')

  return (
    <div className={`liquidation-card ${isLongLiquidation ? 'long-liq' : 'short-liq'} slide-in`}>
      {/* Header */}
      <div className="card-header">
        <div className="coin-badge">
          <TrendingDown size={18} />
          <span className="coin-symbol">{liquidation.coin || 'UNKNOWN'}</span>
        </div>
        <div className={`direction-badge ${isLongLiquidation ? 'long' : 'short'}`}>
          {liquidation.direction || 'N/A'}
        </div>
      </div>

      {/* Main Stats */}
      <div className="card-body">
        <div className="stat-row">
          <div className="stat-item">
            <span className="stat-label">Price</span>
            <span className="stat-value price">${formatNumber(liquidation.price)}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Size</span>
            <span className="stat-value size">{formatNumber(liquidation.size)}</span>
          </div>
        </div>

        <div className="stat-row">
          <div className="stat-item">
            <span className="stat-label">Start Position</span>
            <span className="stat-value">{formatNumber(liquidation.startPosition)}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Mark Price</span>
            <span className="stat-value">${formatNumber(liquidation.liquidation?.markPx)}</span>
          </div>
        </div>

        {/* PnL */}
        <div className={`pnl-container ${isProfitable ? 'profit' : 'loss'}`}>
          <DollarSign size={18} />
          <span className="pnl-label">Closed P&L:</span>
          <span className="pnl-value">${formatPnL(liquidation.closedPnl)}</span>
        </div>

        {/* Fee */}
        <div className="fee-row">
          <span className="fee-label">Fee:</span>
          <span className="fee-value">
            {formatNumber(liquidation.fee)} {liquidation.feeToken || 'USDC'}
          </span>
        </div>
      </div>

      {/* Footer */}
      <div className="card-footer">
        <div className="footer-item">
          <User size={14} />
          <code className="address">{formatAddress(liquidation.userAddress)}</code>
        </div>
        <div className="footer-item">
          <Clock size={14} />
          <span>{formatTimestamp(liquidation.timestamp)}</span>
        </div>
      </div>

      {liquidation.hash && (
        <div className="card-hash">
          <Hash size={12} />
          <code>{formatHash(liquidation.hash)}</code>
        </div>
      )}
    </div>
  )
}

export default LiquidationCard
