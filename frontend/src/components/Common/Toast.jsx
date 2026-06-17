export function Toast({ message, type = 'info', onClose }) {
  const colors = {
    info: 'var(--color-accent-secondary)',
    success: 'var(--color-accent-success)',
    warning: 'var(--color-accent-warning)',
    error: 'var(--color-accent-danger)',
  };

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 'var(--space-3)',
      padding: 'var(--space-3) var(--space-4)',
      background: 'var(--color-bg-elevated)',
      border: `1px solid ${colors[type]}`,
      borderRadius: 'var(--radius-sm)',
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--font-size-sm)',
      color: 'var(--color-text-primary)',
    }}>
      <span style={{ color: colors[type] }}>■</span>
      <span style={{ flex: 1 }}>{message}</span>
      {onClose && (
        <button
          onClick={onClose}
          style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer' }}
        >
          ✕
        </button>
      )}
    </div>
  );
}
