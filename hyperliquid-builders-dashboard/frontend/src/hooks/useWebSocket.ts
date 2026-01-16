/**
 * WebSocket hook for real-time builder statistics.
 *
 * Manages the WebSocket connection to the backend, handling:
 * - Automatic connection on mount
 * - Reconnection on disconnect (3 second delay)
 * - State updates from incoming messages
 * - Cleanup on unmount
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { BuilderStats, ChartData, WebSocketMessage } from '../types';

/** Return type for the useWebSocket hook */
interface UseWebSocketResult {
  stats: BuilderStats[];          // Detailed builder stats (for tables)
  chartData: ChartData;           // Aggregated data (for charts)
  isConnected: boolean;           // WebSocket connection status
  lastBlockNumber: number | null; // Most recent Hyperliquid block
  error: string | null;           // Connection error message
}

/** Empty state for initial render */
const EMPTY_CHART_DATA: ChartData = { builders: [] };

/** Reconnection delay in milliseconds */
const RECONNECT_DELAY = 3000;

export function useWebSocket(): UseWebSocketResult {
  // State
  const [stats, setStats] = useState<BuilderStats[]>([]);
  const [chartData, setChartData] = useState<ChartData>(EMPTY_CHART_DATA);
  const [isConnected, setIsConnected] = useState(false);
  const [lastBlockNumber, setLastBlockNumber] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Refs for cleanup
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  /**
   * Establish WebSocket connection to backend.
   * Uses same host as the page, with ws:// or wss:// based on page protocol.
   */
  const connect = useCallback(() => {
    // Skip if already connected
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    // Build WebSocket URL from current page location
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);

        // Update state from both initial and update messages
        if (message.type === 'initial_stats' || message.type === 'stats_update') {
          setStats(message.data);
          if (message.chartData) {
            setChartData(message.chartData);
          }
        }

        // Track block number for status indicator
        if (message.type === 'stats_update' && message.blockNumber) {
          setLastBlockNumber(message.blockNumber);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      wsRef.current = null;

      // Schedule reconnection attempt
      reconnectTimeoutRef.current = window.setTimeout(() => {
        connect();
      }, RECONNECT_DELAY);
    };

    ws.onerror = () => {
      setError('Connection error');
    };

    wsRef.current = ws;
  }, []);

  // Connect on mount, cleanup on unmount
  useEffect(() => {
    connect();

    return () => {
      // Clear pending reconnect
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      // Close active connection
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return { stats, chartData, isConnected, lastBlockNumber, error };
}
