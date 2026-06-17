export function Spinner({ size = 20 }) {
  return (
    <div style={{
      width: size,
      height: size,
      border: '2px solid var(--color-border)',
      borderTop: '2px solid var(--color-accent-primary)',
      borderRadius: '50%',
      animation: 'spin 0.8s linear infinite',
    }} />
  );
}
