import { useState } from 'react'
import { Copy, Check, Eye, ExternalLink } from 'lucide-react'
import JsonViewerModal from './JsonViewerModal'
import './LiquidationTable.css'

function LiquidationTable({ liquidations }) {
  const [copiedAddress, setCopiedAddress] = useState(null)
  const [selectedLiquidation, setSelectedLiquidation] = useState(null)

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'N/A'
    const date = new Date(timestamp)
    return date.toLocaleString('en-US', {
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const formatAddress = (address) => {
    if (!address) return 'N/A'
    return `${address.slice(0, 6)}...${address.slice(-4)}`
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

  const copyAddress = (address) => {
    navigator.clipboard.writeText(address)
    setCopiedAddress(address)
    setTimeout(() => setCopiedAddress(null), 2000)
  }

  const openJsonViewer = (liquidation) => {
    setSelectedLiquidation(liquidation)
  }

  const closeJsonViewer = () => {
    setSelectedLiquidation(null)
  }

  if (liquidations.length === 0) {
    return null
  }

  return (
    <>
      <div className="liquidation-table-container">
        <table className="liquidation-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>User</th>
              <th>Coin</th>
              <th>Direction</th>
              <th>Size</th>
              <th>Price</th>
              <th>P&L</th>
              <th>Fee</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {liquidations.map((liquidation, index) => {
              const isProfitable = parseFloat(liquidation.closedPnl || 0) >= 0
              const isLongLiquidation = liquidation.direction?.toLowerCase().includes('long')

              return (
                <tr key={`${liquidation.hash}-${index}`} className="liquidation-row slide-in">
                  <td className="time-cell">{formatTimestamp(liquidation.timestamp)}</td>

                  <td className="address-cell">
                    <div className="address-container">
                      <code className="address">{formatAddress(liquidation.userAddress)}</code>
                      <button
                        className="icon-button copy-btn"
                        onClick={() => copyAddress(liquidation.userAddress)}
                        title="Copy address"
                      >
                        {copiedAddress === liquidation.userAddress ?
                          <Check size={14} /> :
                          <Copy size={14} />
                        }
                      </button>
                    </div>
                  </td>

                  <td className="coin-cell">
                    <span className="coin-badge">{liquidation.coin || 'N/A'}</span>
                  </td>

                  <td className="direction-cell">
                    <span className={`direction-badge ${isLongLiquidation ? 'long' : 'short'}`}>
                      {liquidation.direction || 'N/A'}
                    </span>
                  </td>

                  <td className="size-cell">{formatNumber(liquidation.size)}</td>

                  <td className="price-cell">${formatNumber(liquidation.price)}</td>

                  <td className={`pnl-cell ${isProfitable ? 'profit' : 'loss'}`}>
                    ${formatPnL(liquidation.closedPnl)}
                  </td>

                  <td className="fee-cell">
                    {formatNumber(liquidation.fee)} {liquidation.feeToken || 'USDC'}
                  </td>

                  <td className="actions-cell">
                    <button
                      className="icon-button view-btn"
                      onClick={() => openJsonViewer(liquidation)}
                      title="View JSON"
                    >
                      <Eye size={16} />
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {selectedLiquidation && (
        <JsonViewerModal
          liquidation={selectedLiquidation}
          onClose={closeJsonViewer}
        />
      )}
    </>
  )
}

export default LiquidationTable
