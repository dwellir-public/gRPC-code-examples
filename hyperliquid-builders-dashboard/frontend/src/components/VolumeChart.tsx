import { useMemo } from 'react';
import type { ChartData } from '../types';
import styles from './VolumeChart.module.css';

interface VolumeChartProps {
  data: ChartData;
}

export function VolumeChart({ data }: VolumeChartProps) {
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

  const formatPercent = (value: number, total: number): string => {
    if (total === 0) return '0%';
    return `${((value / total) * 100).toFixed(1)}%`;
  };

  if (builders.length === 0) {
    return (
      <div className={styles.container}>
        <h3 className={styles.title}>Volume by Builder</h3>
        <div className={styles.empty}>Waiting for data...</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3 className={styles.title}>Volume by Builder</h3>
        <span className={styles.total}>Total: {formatVolume(totalVolume)}</span>
      </div>

      <div className={styles.chart}>
        {builders.map((builder) => {
          const percentage = (builder.volume / maxVolume) * 100;
          return (
            <div key={builder.name} className={styles.row}>
              <div className={styles.labelContainer}>
                {builder.logo && (
                  <img
                    src={builder.logo}
                    alt={builder.name}
                    className={styles.logo}
                  />
                )}
                <span className={styles.label}>{builder.name}</span>
              </div>
              <div className={styles.barContainer}>
                <div
                  className={styles.bar}
                  style={{
                    width: `${percentage}%`,
                    backgroundColor: builder.color,
                  }}
                />
              </div>
              <div className={styles.values}>
                <span className={styles.volume}>{formatVolume(builder.volume)}</span>
                <span className={styles.percent}>{formatPercent(builder.volume, totalVolume)}</span>
              </div>
            </div>
          );
        })}
      </div>

      <div className={styles.legend}>
        {builders.map((builder) => (
          <div key={builder.name} className={styles.legendItem}>
            <span
              className={styles.legendColor}
              style={{ backgroundColor: builder.color }}
            />
            <span className={styles.legendLabel}>{builder.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
