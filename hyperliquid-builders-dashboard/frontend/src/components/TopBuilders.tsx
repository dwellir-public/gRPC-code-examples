/**
 * TopBuilders - Sidebar component showing builder rankings.
 *
 * Features:
 * - Toggle between sorting by Fees (revenue) or Volume
 * - Visual progress bars showing relative values
 * - Builder logos and names
 * - "Other" category displayed at bottom without rank
 */

import { useMemo, useState } from 'react';
import type { ChartData } from '../types';
import styles from './TopBuilders.module.css';

type SortMetric = 'fees' | 'volume';

interface TopBuildersProps {
  data: ChartData;
}

export function TopBuilders({ data }: TopBuildersProps) {
  const [sortBy, setSortBy] = useState<SortMetric>('fees');

  // Sort builders by selected metric and calculate max for bar scaling
  const { sortedBuilders, maxValue } = useMemo(() => {
    const sorted = [...data.builders].sort((a, b) => {
      const aVal = sortBy === 'fees' ? a.fees : a.volume;
      const bVal = sortBy === 'fees' ? b.fees : b.volume;
      return bVal - aVal;
    });
    const max = Math.max(...sorted.map((b) => (sortBy === 'fees' ? b.fees : b.volume)), 1);
    return { sortedBuilders: sorted, maxValue: max };
  }, [data, sortBy]);

  /** Format currency values with K/M suffixes */
  const formatCurrency = (value: number): string => {
    if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
    if (value >= 1_000) return `$${(value / 1_000).toFixed(2)}K`;
    return `$${value.toFixed(2)}`;
  };

  if (sortedBuilders.length === 0) {
    return (
      <div className={styles.container}>
        <h3 className={styles.title}>Top Builders</h3>
        <div className={styles.empty}>Waiting for data...</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3 className={styles.title}>Top Builders</h3>
        <div className={styles.toggle}>
          <button
            className={`${styles.toggleBtn} ${sortBy === 'fees' ? styles.active : ''}`}
            onClick={() => setSortBy('fees')}
          >
            Fees
          </button>
          <button
            className={`${styles.toggleBtn} ${sortBy === 'volume' ? styles.active : ''}`}
            onClick={() => setSortBy('volume')}
          >
            Volume
          </button>
        </div>
      </div>

      <div className={styles.list}>
        {sortedBuilders.map((builder, index) => {
          const value = sortBy === 'fees' ? builder.fees : builder.volume;
          const percentage = (value / maxValue) * 100;
          const isOther = builder.name === 'Other';

          return (
            <div key={builder.name} className={styles.item}>
              <div className={styles.rank}>
                <span className={isOther ? styles.rankOther : ''}>{isOther ? '-' : index + 1}</span>
              </div>

              <div className={styles.builderInfo}>
                {builder.logo ? (
                  <img
                    src={builder.logo}
                    alt={builder.name}
                    className={styles.logo}
                  />
                ) : (
                  <div
                    className={styles.logoPlaceholder}
                    style={{ backgroundColor: builder.color }}
                  >
                    {builder.name.charAt(0)}
                  </div>
                )}
                <span className={styles.name}>{builder.name}</span>
              </div>

              <div className={styles.volumeSection}>
                <span className={styles.volume}>{formatCurrency(value)}</span>
                <div className={styles.barContainer}>
                  <div
                    className={styles.bar}
                    style={{
                      width: `${percentage}%`,
                      backgroundColor: builder.color,
                    }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
