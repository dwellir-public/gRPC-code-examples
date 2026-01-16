import { useMemo } from 'react';
import type { ChartData } from '../types';
import styles from './BuilderChart.module.css';

interface BuilderChartProps {
  data: ChartData;
}

export function BuilderChart({ data }: BuilderChartProps) {
  const { builders, totalVolume, maxVolume } = useMemo(() => {
    const total = data.builders.reduce((sum, b) => sum + b.volume, 0);
    const max = Math.max(...data.builders.map((b) => b.volume), 1);
    return { builders: data.builders, totalVolume: total, maxVolume: max };
  }, [data]);

  const formatVolume = (value: number): string => {
    if (value >= 1_000_000) {
      return `$${(value / 1_000_000).toFixed(2)}M`;
    }
    if (value >= 1_000) {
      return `$${(value / 1_000).toFixed(2)}K`;
    }
    return `$${value.toFixed(2)}`;
  };

  const formatPercent = (value: number): string => {
    if (totalVolume === 0) return '0%';
    return `${((value / totalVolume) * 100).toFixed(1)}%`;
  };

  if (builders.length === 0) {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <h2 className={styles.title}>Volume by Builder</h2>
        </div>
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M3 3v18h18" />
              <path d="M18 17V9" />
              <path d="M13 17V5" />
              <path d="M8 17v-3" />
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
        <h2 className={styles.title}>Volume by Builder</h2>
        <span className={styles.total}>Total: {formatVolume(totalVolume)}</span>
      </div>

      <div className={styles.chart}>
        {builders.map((builder, index) => {
          const percentage = (builder.volume / maxVolume) * 100;
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
                <span className={styles.volume}>{formatVolume(builder.volume)}</span>
                <span className={styles.percent}>{formatPercent(builder.volume)}</span>
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
