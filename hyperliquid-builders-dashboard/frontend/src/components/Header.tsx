/**
 * Header - App header with title, connection status, and controls.
 */

import { ThemeToggle } from './ThemeToggle';
import { StatusIndicator } from './StatusIndicator';
import styles from './Header.module.css';

interface HeaderProps {
  isConnected: boolean;
  lastBlockNumber: number | null;
  startedAt?: string;  // ISO timestamp when streaming started
}

/** Format a duration in a human-readable way */
function formatDuration(startedAt: string): string {
  const start = new Date(startedAt);
  const now = new Date();
  const diffMs = now.getTime() - start.getTime();

  const minutes = Math.floor(diffMs / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) {
    return `${days}d ${hours % 24}h`;
  }
  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`;
  }
  return `${minutes}m`;
}

/** Format time as HH:MM */
function formatTime(startedAt: string): string {
  const date = new Date(startedAt);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function Header({ isConnected, lastBlockNumber, startedAt }: HeaderProps) {
  return (
    <header className={styles.header}>
      <div className={styles.titleSection}>
        <h1 className={styles.title}>Builder Codes</h1>
        <span className={styles.subtitle}>Hyperliquid L1 Live Stream</span>
      </div>

      <div className={styles.controls}>
        {startedAt && (
          <div className={styles.streamingInfo}>
            <span className={styles.streamingLabel}>Data since</span>
            <span className={styles.streamingTime}>
              {formatTime(startedAt)} ({formatDuration(startedAt)} ago)
            </span>
          </div>
        )}
        <StatusIndicator
          isConnected={isConnected}
          lastBlockNumber={lastBlockNumber}
        />
        <ThemeToggle />
      </div>
    </header>
  );
}
