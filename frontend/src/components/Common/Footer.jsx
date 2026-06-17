export function Footer() {
  return (
    <footer style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 var(--space-6)',
      borderTop: '1px solid var(--color-border)',
      background: 'var(--color-bg-secondary)',
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--font-size-xs)',
      color: 'var(--color-text-muted)',
      height: '32px',
    }}>
      <span>Labourious v1.0.0</span>
      <span>Phase 1</span>
    </footer>
  );
}
