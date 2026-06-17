export function PlaceholderPage({ title }) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100%',
      gap: 'var(--space-4)',
      color: 'var(--color-text-secondary)',
      fontFamily: 'var(--font-mono)',
    }}>
      <span style={{ fontSize: '2rem', color: 'var(--color-accent-primary)' }}>⬡</span>
      <h2 style={{ color: 'var(--color-text-primary)', fontSize: 'var(--font-size-xl)' }}>{title}</h2>
      <p style={{ fontSize: 'var(--font-size-sm)' }}>Phase 2 implementation pending</p>
    </div>
  );
}
