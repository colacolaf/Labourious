import React, { useState } from 'react';
import useWizardStore from '../../stores/wizard.store';

function strength(pwd) {
  return [
    pwd.length >= 12,
    /[A-Z]/.test(pwd),
    /[a-z]/.test(pwd),
    /\d/.test(pwd),
    /[^A-Za-z0-9]/.test(pwd),
  ];
}

const LABELS = ['12+ chars', 'Uppercase', 'Lowercase', 'Digit', 'Special'];

export default function WelcomeStep() {
  const setFormData = useWizardStore((s) => s.setFormData);
  const nextStep = useWizardStore((s) => s.nextStep);
  const [pwd, setPwd] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');

  const checks = strength(pwd);
  const score = checks.filter(Boolean).length;
  const meterColor =
    score <= 2 ? 'var(--color-accent-danger)' :
    score <= 3 ? 'var(--color-accent-warning)' :
    'var(--color-accent-primary)';

  function handleNext() {
    if (!checks.every(Boolean)) { setError('Password does not meet all requirements'); return; }
    if (pwd !== confirm) { setError('Passwords do not match'); return; }
    setFormData('welcome', { vaultPassword: pwd });
    nextStep();
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      <div>
        <h2 style={{ color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)', marginBottom: 'var(--space-2)' }}>
          Welcome to Labourious
        </h2>
        <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
          Set a vault password to encrypt your API keys.
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
        <label style={labelStyle}>
          Vault Password
          <input
            type="password"
            value={pwd}
            onChange={(e) => { setPwd(e.target.value); setError(''); }}
            style={inputStyle}
          />
        </label>

        {pwd && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            <div style={{ display: 'flex', gap: 'var(--space-1)' }}>
              {checks.map((ok, i) => (
                <div key={i} style={{ flex: 1, height: 4, borderRadius: 2, background: ok ? meterColor : 'var(--color-border)' }} />
              ))}
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
              {LABELS.map((l, i) => (
                <span key={l} style={{ fontSize: 'var(--font-size-xs)', color: checks[i] ? 'var(--color-accent-primary)' : 'var(--color-text-muted)' }}>
                  {checks[i] ? '✓' : '○'} {l}
                </span>
              ))}
            </div>
          </div>
        )}

        <label style={labelStyle}>
          Confirm Password
          <input
            type="password"
            value={confirm}
            onChange={(e) => { setConfirm(e.target.value); setError(''); }}
            style={inputStyle}
          />
        </label>
      </div>

      {error && <p style={{ color: 'var(--color-accent-danger)', fontSize: 'var(--font-size-sm)', fontFamily: 'var(--font-mono)' }}>{error}</p>}

      <button onClick={handleNext} style={btnPrimary}>Next →</button>
    </div>
  );
}

const labelStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: 'var(--space-2)',
  color: 'var(--color-text-secondary)',
  fontSize: 'var(--font-size-sm)',
  fontFamily: 'var(--font-mono)',
};

const inputStyle = {
  display: 'block',
  width: '100%',
  marginTop: 'var(--space-2)',
  padding: 'var(--space-3)',
  background: 'var(--color-bg-tertiary)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  color: 'var(--color-text-primary)',
  fontFamily: 'var(--font-mono)',
  fontSize: 'var(--font-size-base)',
  outline: 'none',
  boxSizing: 'border-box',
};

const btnPrimary = {
  padding: 'var(--space-3) var(--space-6)',
  background: 'var(--color-accent-primary)',
  color: 'var(--color-bg-primary)',
  border: 'none',
  borderRadius: 'var(--radius-md)',
  fontFamily: 'var(--font-mono)',
  fontWeight: 700,
  cursor: 'pointer',
  fontSize: 'var(--font-size-sm)',
  alignSelf: 'flex-end',
};
