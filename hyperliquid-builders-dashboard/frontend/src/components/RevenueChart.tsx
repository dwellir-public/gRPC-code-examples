/**
 * RevenueChart - Horizontal bar chart showing builder fees (revenue).
 *
 * Features:
 * - Ranked list with visual progress bars
 * - Shows fees, volume, and fee ratio (in basis points)
 * - Builder logos and colors
 * - "Other" category always displayed last
 * - Color-coded legend at bottom
 */

import { useMemo } from 'react';
import type { ChartData } from '../types';
import styles from './RevenueChart.module.css';

interface RevenueChartProps {
  data: ChartData;
}

export function RevenueChart({ data }: RevenueChartProps) {
  // Sort builders by fees, keeping "Other" at the bottom
  const { builders, totalFees, maxFees } = useMemo(() => {
    const total = data.builders.reduce((sum, b) => sum + b.fees, 0);
    const max = Math.max(...data.builders.map((b) => b.fees), 1);

    // Separate "Other" to keep at bottom of list
    const other = data.builders.find((b) => b.name === 'Other');
    const rest = data.builders.filter((b) => b.name !== 'Other').sort((a, b) => b.fees - a.fees);
    const sorted = other ? [...rest, other] : rest;

    return { builders: sorted, totalFees: total, maxFees: max };
  }, [data]);

  /** Format currency with K/M suffixes */
  const formatCurrency = (value: number): string => {
    if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
    if (value >= 1_000) return `$${(value / 1_000).toFixed(2)}K`;
    return `$${value.toFixed(2)}`;
  };

  /** Calculate fee as basis points of volume (1 bps = 0.01%) */
  const formatFeeRatio = (fees: number, volume: number): string => {
    if (volume === 0) return '0 bps';
    const bps = (fees / volume) * 10000;
    return `${bps.toFixed(1)} bps`;
  };

  if (builders.length === 0) {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <h2 className={styles.title}>Revenue by Builder</h2>
        </div>
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
            </svg>
          </div>
          <p>Waiting for builder data...</p>
          <p className={styles.emptyHint}>Chart will populate as trades come in</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>Revenue by Builder</h2>
        <span className={styles.total}>Total: {formatCurrency(totalFees)}</span>
      </div>

      <div className={styles.chart}>
        {builders.map((builder, index) => {
          const percentage = (builder.fees / maxFees) * 100;
          const isOther = builder.name === 'Other';

          return (
            <div key={builder.name} className={styles.row}>
              <div className={styles.rankBadge}>
                <span className={isOther ? styles.rankOther : ''}>{isOther ? '-' : index + 1}</span>
              </div>

              <div className={styles.builderInfo}>
                {builder.logo ? (
                  <img src={builder.logo} alt={builder.name} className={styles.logo} />
                ) : (
                  <div className={styles.logoPlaceholder} style={{ backgroundColor: builder.color }}>
                    {builder.name.charAt(0)}
                  </div>
                )}
                <span className={styles.name}>{builder.name}</span>
              </div>

              <div className={styles.barSection}>
                <div className={styles.barBackground}>
                  <div
                    className={styles.bar}
                    style={{
                      width: `${percentage}%`,
                      backgroundColor: builder.color,
                    }}
                  />
                </div>
              </div>

              <div className={styles.stats}>
                <span className={styles.fees}>{formatCurrency(builder.fees)}</span>
                <span className={styles.volume}>{formatCurrency(builder.volume)} vol</span>
                <span className={styles.ratio}>{formatFeeRatio(builder.fees, builder.volume)}</span>
              </div>
            </div>
          );
        })}
      </div>

      <div className={styles.legend}>
        {builders.slice(0, 8).map((builder) => (
          <div key={builder.name} className={styles.legendItem}>
            <span className={styles.legendColor} style={{ backgroundColor: builder.color }} />
            <span className={styles.legendLabel}>{builder.name}</span>
          </div>
        ))}
        {builders.length > 8 && (
          <span className={styles.legendMore}>+{builders.length - 8} more</span>
        )}
      </div>
    </div>
  );
}
