import { useMemo, useState } from 'react';
import type { BuilderStats, SortDirection, SortKey } from '../types';
import styles from './BuildersTable.module.css';

interface BuildersTableProps {
  stats: BuilderStats[];
}

export function BuildersTable({ stats }: BuildersTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('totalVolumeUsd');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const sortedStats = useMemo(() => {
    return [...stats].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];

      if (aVal === null) return 1;
      if (bVal === null) return -1;

      let comparison = 0;
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        comparison = aVal - bVal;
      } else {
        comparison = String(aVal).localeCompare(String(bVal));
      }

      return sortDirection === 'desc' ? -comparison : comparison;
    });
  }, [stats, sortKey, sortDirection]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDirection((prev) => (prev === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortKey(key);
      setSortDirection('desc');
    }
  };

  const formatVolume = (value: number): string => {
    if (value >= 1_000_000) {
      return `$${(value / 1_000_000).toFixed(2)}M`;
    }
    if (value >= 1_000) {
      return `$${(value / 1_000).toFixed(2)}K`;
    }
    return `$${value.toFixed(2)}`;
  };

  const formatFees = (value: number): string => {
    if (value >= 1_000) {
      return `$${(value / 1_000).toFixed(2)}K`;
    }
    return `$${value.toFixed(4)}`;
  };

  const formatTime = (isoString: string | null): string => {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleTimeString();
  };

  const SortIcon = ({ active, direction }: { active: boolean; direction: SortDirection }) => (
    <span className={`${styles.sortIcon} ${active ? styles.active : ''}`}>
      {direction === 'desc' ? '\u25BC' : '\u25B2'}
    </span>
  );

  if (stats.length === 0) {
    return (
      <div className={styles.empty}>
        <p>No builder data yet.</p>
        <p className={styles.emptyHint}>Waiting for fills with builder codes...</p>
      </div>
    );
  }

  return (
    <div className={styles.tableWrapper}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th className={styles.rank}>#</th>
            <th className={styles.sortable} onClick={() => handleSort('name')}>
              Builder
              <SortIcon active={sortKey === 'name'} direction={sortDirection} />
            </th>
            <th className={`${styles.sortable} ${styles.numeric}`} onClick={() => handleSort('totalVolumeUsd')}>
              Volume
              <SortIcon active={sortKey === 'totalVolumeUsd'} direction={sortDirection} />
            </th>
            <th className={`${styles.sortable} ${styles.numeric}`} onClick={() => handleSort('tradeCount')}>
              Trades
              <SortIcon active={sortKey === 'tradeCount'} direction={sortDirection} />
            </th>
            <th className={`${styles.sortable} ${styles.numeric}`} onClick={() => handleSort('totalFeesUsd')}>
              Fees Earned
              <SortIcon active={sortKey === 'totalFeesUsd'} direction={sortDirection} />
            </th>
            <th className={`${styles.sortable} ${styles.numeric}`} onClick={() => handleSort('lastActive')}>
              Last Active
              <SortIcon active={sortKey === 'lastActive'} direction={sortDirection} />
            </th>
          </tr>
        </thead>
        <tbody>
          {sortedStats.map((builder, index) => (
            <tr key={builder.address}>
              <td className={styles.rank}>{index + 1}</td>
              <td>
                <div className={styles.builderCell}>
                  <span
                    className={styles.colorDot}
                    style={{ backgroundColor: builder.color }}
                  />
                  {builder.logo && (
                    <img
                      src={builder.logo}
                      alt={builder.name}
                      className={styles.builderLogo}
                    />
                  )}
                  <div className={styles.builderInfo}>
                    <span className={styles.builderName}>{builder.name}</span>
                    <span className={styles.builderAddress}>{builder.address}</span>
                  </div>
                </div>
              </td>
              <td className={styles.numeric}>{formatVolume(builder.totalVolumeUsd)}</td>
              <td className={styles.numeric}>{builder.tradeCount.toLocaleString()}</td>
              <td className={`${styles.numeric} ${styles.fees}`}>{formatFees(builder.totalFeesUsd)}</td>
              <td className={styles.numeric}>{formatTime(builder.lastActive)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
