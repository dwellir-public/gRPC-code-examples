import { useState } from 'react'
import { ChevronDown, ChevronUp, User, DollarSign, TrendingDown, Layers, Copy, Check } from 'lucide-react'
import LiquidationCard from './LiquidationCard'
import './GroupedLiquidationCard.css'

function GroupedLiquidationCard({ group }) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [copied, setCopied] = useState(false)

  const formatAddress = (address) => {
    if (!address) return 'N/A'
    return `${address.slice(0, 6)}...${address.slice(-4)}`
  }

  const copyAddress = (e) => {
    e.stopPropagation() // Prevent expanding the card
    navigator.clipboard.writeText(group.userAddress)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const formatNumber = (num) => {
    return num.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    })
  }

  const formatPnL = (pnl) => {
    return pnl.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
      signDisplay: 'always'
    })
  }

  const isProfitable = group.totalPnL >= 0

  return (
    <div className="grouped-liquidation-card slide-in">
      {/* Header - Always visible */}
      <div
        className="grouped-card-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="header-left">
          <div className="user-badge">
            <User size={18} />
            <code className="address">{formatAddress(group.userAddress)}</code>
            <button
              className="copy-button"
              onClick={copyAddress}
              title="Copy address"
            >
              {copied ? <Check size={14} /> : <Copy size={14} />}
            </button>
          </div>
          <div className="liquidation-count">
            <Layers size={16} />
            <span>{group.count} liquidation{group.count > 1 ? 's' : ''}</span>
          </div>
        </div>

        <div className="header-right">
          <div className={`total-pnl ${isProfitable ? 'profit' : 'loss'}`}>
            <DollarSign size={18} />
            <span className="pnl-value">${formatPnL(group.totalPnL)}</span>
          </div>
          <button className="expand-button">
            {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
          </button>
        </div>
      </div>

      {/* Summary Stats - Always visible */}
      <div className="grouped-card-summary">
        <div className="summary-item">
          <span className="summary-label">Total Volume</span>
          <span className="summary-value">${formatNumber(group.totalVolume)}</span>
        </div>
        <div className="summary-item">
          <span className="summary-label">Avg P&L per Position</span>
          <span className={`summary-value ${isProfitable ? 'profit' : 'loss'}`}>
            ${formatNumber(group.totalPnL / group.count)}
          </span>
        </div>
      </div>

      {/* Expanded Content - Individual liquidations */}
      {isExpanded && (
        <div className="grouped-card-content">
          <div className="content-divider">
            <TrendingDown size={16} />
            <span>Individual Liquidations</span>
          </div>
          <div className="individual-liquidations">
            {group.liquidations.map((liquidation, index) => (
              <LiquidationCard
                key={`${liquidation.hash}-${index}`}
                liquidation={liquidation}
                compact={true}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default GroupedLiquidationCard
