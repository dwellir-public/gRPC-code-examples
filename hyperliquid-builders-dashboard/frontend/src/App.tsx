/**
 * Main Application Component
 *
 * Root component that assembles the dashboard layout:
 * - Header: Title, connection status, theme toggle
 * - StatsCards: Key metrics (revenue, volume, users)
 * - RevenueChart: Bar chart of builder fees
 * - TopBuilders: Sidebar ranking with toggle
 * - Footer: Attribution
 *
 * Data flows from the useWebSocket hook which maintains
 * a live connection to the backend for real-time updates.
 */

import { Header, StatsCards, RevenueChart, TopBuilders } from './components';
import { useWebSocket } from './hooks/useWebSocket';
import styles from './App.module.css';

function App() {
  // Connect to backend WebSocket for real-time data
  const { chartData, isConnected, lastBlockNumber, error } = useWebSocket();

  return (
    <div className={styles.app}>
      {/* Header with connection status and streaming info */}
      <Header
        isConnected={isConnected}
        lastBlockNumber={lastBlockNumber}
        startedAt={chartData.startedAt}
      />

      <main className={styles.main}>
        {/* Connection error banner */}
        {error && <div className={styles.error}>{error}</div>}

        {/* Summary statistics cards */}
        <StatsCards data={chartData} />

        {/* Main content area: chart + sidebar */}
        <div className={styles.content}>
          <div className={styles.chartsSection}>
            <RevenueChart data={chartData} />
          </div>
          <aside className={styles.sidebar}>
            <TopBuilders data={chartData} />
          </aside>
        </div>
      </main>

      {/* Footer with attribution */}
      <footer className={styles.footer}>
        <span>Powered by</span>
        <a
          href="https://dwellir.com"
          target="_blank"
          rel="noopener noreferrer"
          className={styles.link}
        >
          Dwellir
        </a>
        <span className={styles.separator}>|</span>
        <span>Hyperliquid gRPC Stream</span>
      </footer>
    </div>
  );
}

export default App;
