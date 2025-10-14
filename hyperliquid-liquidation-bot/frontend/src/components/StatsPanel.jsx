import { TrendingDown, DollarSign, Activity, BarChart3 } from 'lucide-react'
import './StatsPanel.css'

function StatsPanel({ stats }) {
  const formatNumber = (num) => {
    return num.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    })
  }

  const formatVolume = (num) => {
    if (num >= 1000000) {
      return `$${(num / 1000000).toFixed(2)}M`
    } else if (num >= 1000) {
      return `$${(num / 1000).toFixed(2)}K`
    }
    return `$${num.toFixed(2)}`
  }

  return (
    <div className="stats-panel">
      <div className="stat-card">
        <div className="stat-icon liquidations">
          <TrendingDown size={24} />
        </div>
        <div className="stat-content">
          <div className="stat-label">Total Liquidations</div>
          <div className="stat-number">{stats.totalLiquidations}</div>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon volume">
          <BarChart3 size={24} />
        </div>
        <div className="stat-content">
          <div className="stat-label">Total Volume</div>
          <div className="stat-number">{formatVolume(stats.totalVolume)}</div>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon pnl">
          <DollarSign size={24} />
        </div>
        <div className="stat-content">
          <div className="stat-label">Total P&L</div>
          <div className={`stat-number ${stats.totalPnL >= 0 ? 'positive' : 'negative'}`}>
            ${formatNumber(stats.totalPnL)}
          </div>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon average">
          <Activity size={24} />
        </div>
        <div className="stat-content">
          <div className="stat-label">Avg Size</div>
          <div className="stat-number">{formatNumber(stats.averageSize)}</div>
        </div>
      </div>
    </div>
  )
}

export default StatsPanel
