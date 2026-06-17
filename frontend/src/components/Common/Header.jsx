export function Header() {
  return (
    <header style={{
      display: 'flex',
      alignItems: 'center',
      padding: '0 var(--space-6)',
      borderBottom: '1px solid var(--color-border)',
      background: 'var(--color-bg-secondary)',
      height: 'var(--topbar-height)',
    }}>
      <span style={{ color: 'var(--color-accent-primary)', fontFamily: 'var(--font-mono)', fontWeight: 700, letterSpacing: '0.1em' }}>
        ⬡ LABOURIOUS
      </span>
    </header>
  );
}
