export function Modal({ open, onClose, title, children }) {
  if (!open) return null;
  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'var(--color-bg-elevated)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-md)',
          padding: 'var(--space-6)',
          minWidth: 320,
          maxWidth: '90vw',
        }}
      >
        {title && (
          <h3 style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-text-primary)', marginBottom: 'var(--space-4)' }}>
            {title}
          </h3>
        )}
        {children}
      </div>
    </div>
  );
}
