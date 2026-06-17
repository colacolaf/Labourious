export function Button({ children, onClick, variant = 'primary', disabled = false, style: extraStyle = {} }) {
  const base = {
    padding: 'var(--space-2) var(--space-4)',
    border: '1px solid',
    borderRadius: 'var(--radius-sm)',
    fontFamily: 'var(--font-mono)',
    fontSize: 'var(--font-size-sm)',
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
    transition: 'all var(--transition-fast)',
    background: 'transparent',
  };

  const variants = {
    primary: { borderColor: 'var(--color-accent-primary)', color: 'var(--color-accent-primary)' },
    danger: { borderColor: 'var(--color-accent-danger)', color: 'var(--color-accent-danger)' },
    ghost: { borderColor: 'var(--color-border)', color: 'var(--color-text-secondary)' },
  };

  return (
    <button onClick={onClick} disabled={disabled} style={{ ...base, ...variants[variant], ...extraStyle }}>
      {children}
    </button>
  );
}
