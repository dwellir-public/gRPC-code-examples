/**
 * TypeScript types for the Hyperliquid Builders Dashboard.
 *
 * These types mirror the backend API responses and are used throughout
 * the frontend for type-safe data handling.
 */

// =============================================================================
// Builder Statistics
// =============================================================================

/**
 * Detailed statistics for a single builder (from /api/stats).
 * Used for table view with full builder information.
 */
export interface BuilderStats {
  address: string;           // Builder's Ethereum address
  name: string;              // Display name
  color: string;             // Chart color (hex)
  logo: string;              // Logo URL
  isKnown: boolean;          // True if in builders.json config
  tradeCount: number;        // Total trades processed
  totalVolumeUsd: number;    // Cumulative trading volume
  totalFeesUsd: number;      // Cumulative builder fees (revenue)
  uniqueUsers: number;       // Count of unique user addresses
  lastActive: string | null; // ISO timestamp of last activity
}

/**
 * Aggregated builder data for charts (from /api/chart).
 * Simplified structure optimized for chart rendering.
 */
export interface ChartBuilder {
  name: string;
  color: string;
  logo: string;
  volume: number;
  trades: number;
  fees: number;   // Builder revenue in USD
  users: number;
}

/**
 * Dashboard totals across all builders.
 */
export interface ChartTotals {
  volume: number;
  fees: number;
  users: number;
  avgRevenuePerUser: number;
}

/**
 * Complete chart data response from /api/chart.
 */
export interface ChartData {
  builders: ChartBuilder[];
  totals?: ChartTotals;
  startedAt?: string;  // ISO timestamp when streaming started
}

// =============================================================================
// WebSocket Messages
// =============================================================================

/**
 * WebSocket message types from the backend.
 *
 * - initial_stats: Sent immediately on connection with current state
 * - stats_update: Sent when new fills are processed
 */
export type WebSocketMessage =
  | { type: 'initial_stats'; data: BuilderStats[]; chartData: ChartData }
  | { type: 'stats_update'; data: BuilderStats[]; chartData: ChartData; blockNumber?: number };

// =============================================================================
// UI State Types
// =============================================================================

/** Sort direction for table columns */
export type SortDirection = 'asc' | 'desc';

/** Sortable column keys in the builders table */
export type SortKey = keyof BuilderStats;
