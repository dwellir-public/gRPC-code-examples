import { useMemo } from 'react';
import type { ChartData } from '../types';
import styles from './FeesChart.module.css';

interface FeesChartProps {
  data: ChartData;
}

export function FeesChart({ data }: FeesChartProps) {
  const { builders, totalFees, maxFees } = useMemo(() => {
    const total = data.builders.reduce((sum, b) => sum + b.fees, 0);
    const max = Math.max(...data.builders.map((b) => b.fees), 1);
    // Sort by fees descending
    const sorted = [...data.builders].sort((a, b) => b.fees - a.fees);
    return { builders: sorted, totalFees: total, maxFees: max };
  }, [data]);

  const formatFees = (value: number): string => {
    if (value >= 1_000_000) {
      return `$${(value / 1_000_000).toFixed(2)}M`;
    }
    if (value >= 1_000) {
      return `$${(value / 1_000).toFixed(2)}K`;
    }
    return `$${value.toFixed(2)}`;
  };

  const formatPercent = (value: number): string => {
    if (totalFees === 0) return '0%';
    return `${((value / totalFees) * 100).toFixed(1)}%`;
  };

  if (builders.length === 0) {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <h2 className={styles.title}>Fees by Builder</h2>
        </div>
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
            </svg>
          </div>
          <p>Waiting for fee data...</p>
          <p className={styles.emptyHint}>Chart will populate as trades come in</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>Fees by Builder</h2>
        <span className={styles.total}>Total: {formatFees(totalFees)}</span>
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
                <span className={styles.fees}>{formatFees(builder.fees)}</span>
                <span className={styles.percent}>{formatPercent(builder.fees)}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
