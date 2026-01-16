/**
 * StatsCards - Summary metrics displayed as cards at top of dashboard.
 *
 * Displays:
 * - Total Revenue (sum of all builder fees)
 * - Total Volume (sum of all trading volume)
 * - Unique Users (count of distinct wallet addresses)
 * - Avg Revenue / User (fees divided by user count)
 */

import type { ChartData } from '../types';
import styles from './StatsCards.module.css';

interface StatsCardsProps {
  data: ChartData;
}

export function StatsCards({ data }: StatsCardsProps) {
  // Default to zeros if totals not yet available
  const totals = data.totals || { volume: 0, fees: 0, users: 0, avgRevenuePerUser: 0 };

  /** Format currency with K/M suffixes */
  const formatCurrency = (value: number): string => {
    if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
    if (value >= 1_000) return `$${(value / 1_000).toFixed(2)}K`;
    return `$${value.toFixed(2)}`;
  };

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <span className={styles.label}>Total Revenue</span>
        <span className={`${styles.value} ${styles.revenue}`}>{formatCurrency(totals.fees)}</span>
      </div>

      <div className={styles.card}>
        <span className={styles.label}>Total Volume</span>
        <span className={styles.value}>{formatCurrency(totals.volume)}</span>
      </div>

      <div className={styles.card}>
        <span className={styles.label}>Unique Users</span>
        <span className={styles.value}>{totals.users.toLocaleString()}</span>
      </div>

      <div className={styles.card}>
        <span className={styles.label}>Avg Revenue / User</span>
        <span className={`${styles.value} ${styles.revenue}`}>{formatCurrency(totals.avgRevenuePerUser)}</span>
      </div>
    </div>
  );
}
