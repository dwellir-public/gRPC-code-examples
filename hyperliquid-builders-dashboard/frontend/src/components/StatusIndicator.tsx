import styles from './StatusIndicator.module.css';

interface StatusIndicatorProps {
  isConnected: boolean;
  lastBlockNumber: number | null;
}

export function StatusIndicator({ isConnected, lastBlockNumber }: StatusIndicatorProps) {
  return (
    <div className={styles.container}>
      <div className={`${styles.indicator} ${isConnected ? styles.connected : styles.disconnected}`} />
      <span className={styles.text}>
        {isConnected ? (
          lastBlockNumber ? `Block ${lastBlockNumber.toLocaleString()}` : 'Connected'
        ) : (
          'Connecting...'
        )}
      </span>
    </div>
  );
}
