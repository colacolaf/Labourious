const dot = (ok) => ({
  display: 'inline-block',
  width: 8,
  height: 8,
  borderRadius: '50%',
  marginRight: 'var(--space-2)',
  background: ok ? 'var(--color-accent-primary)' : 'var(--color-accent-danger)',
});

const row = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: 'var(--space-2) 0',
  borderBottom: '1px solid var(--color-border-subtle, var(--color-border))',
  fontFamily: 'var(--font-mono)',
  fontSize: 'var(--font-size-sm)',
};

function uptimeStr(s) {
  if (s == null) return '—';
  if (s < 60) return `${Math.round(s)}s`;
  if (s < 3600) return `${Math.round(s / 60)}m`;
  return `${Math.round(s / 3600)}h`;
}

export default function SystemHealthPanel({ backendStatus, dbStatus, backendVersion, backendUptime, llmConfig }) {
  const backendOk = backendStatus === 'connected';
  const dbOk = dbStatus === 'ok';
  const llmOk = llmConfig != null;

  return (
    <div style={{ fontFamily: 'var(--font-mono)' }}>
      <div style={{ ...row, borderBottom: '1px solid var(--color-border)' }}>
        <span style={{ color: 'var(--color-text-secondary)' }}>
          <span style={dot(backendOk)} />
          Backend
        </span>
        <span style={{ color: backendOk ? 'var(--color-accent-primary)' : 'var(--color-accent-danger)', fontSize: 'var(--font-size-xs)' }}>
          {backendStatus?.toUpperCase()}
        </span>
      </div>

      <div style={{ ...row }}>
        <span style={{ color: 'var(--color-text-secondary)' }}>
          <span style={dot(dbOk)} />
          Database
        </span>
        <span style={{ color: dbOk ? 'var(--color-accent-primary)' : 'var(--color-accent-danger)', fontSize: 'var(--font-size-xs)' }}>
          {dbStatus?.toUpperCase()}
        </span>
      </div>

      <div style={{ ...row }}>
        <span style={{ color: 'var(--color-text-secondary)' }}>
          <span style={dot(llmOk)} />
          LLM
        </span>
        <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)' }}>
          {llmConfig ? `${llmConfig.provider}/${llmConfig.model}` : 'unconfigured'}
        </span>
      </div>

      {backendVersion && (
        <div style={{ ...row, borderBottom: 'none' }}>
          <span style={{ color: 'var(--color-text-secondary)' }}>Uptime</span>
          <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)' }}>
            {uptimeStr(backendUptime)} · v{backendVersion}
          </span>
        </div>
      )}
    </div>
  );
}
