import React, { useState } from 'react';
import useWizardStore from '../../stores/wizard.store';

const SLIDERS = [
  { key: 'dayTrading', label: 'Day Trading' },
  { key: 'swingTrading', label: 'Swing Trading' },
  { key: 'longTerm', label: 'Long-Term' },
];

export default function AllocationStep() {
  const { setFormData, nextStep } = useWizardStore((s) => ({ setFormData: s.setFormData, nextStep: s.nextStep }));
  const [values, setValues] = useState({ dayTrading: 33, swingTrading: 34, longTerm: 33 });

  const total = Object.values(values).reduce((a, b) => a + b, 0);
  const valid = total === 100;

  function set(key, val) {
    setValues((prev) => ({ ...prev, [key]: Number(val) }));
  }

  function handleNext() {
    if (!valid) return;
    setFormData('allocation', values);
    nextStep();
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      <div>
        <h2 style={{ color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)', marginBottom: 'var(--space-2)' }}>
          Capital Allocation
        </h2>
        <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
          Distribute capital across trading strategies.
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
        {SLIDERS.map(({ key, label }) => (
          <label key={key} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>{label}</span>
              <span style={{ color: 'var(--color-accent-primary)', fontWeight: 700 }}>{values[key]}%</span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              value={values[key]}
              onChange={(e) => set(key, e.target.value)}
              style={{ accentColor: 'var(--color-accent-primary)', width: '100%' }}
            />
          </label>
        ))}
      </div>

      <div style={{
        padding: 'var(--space-3)',
        background: 'var(--color-bg-tertiary)',
        borderRadius: 'var(--radius-md)',
        border: `1px solid ${valid ? 'var(--color-accent-primary)' : 'var(--color-accent-warning)'}`,
        fontFamily: 'var(--font-mono)',
        fontSize: 'var(--font-size-sm)',
        color: valid ? 'var(--color-accent-primary)' : 'var(--color-accent-warning)',
        display: 'flex',
        justifyContent: 'space-between',
      }}>
        <span>Total</span>
        <span>{total}% {valid ? '✓' : `— ${100 - total > 0 ? `+${100 - total}` : 100 - total} to reach 100`}</span>
      </div>

      <button
        onClick={handleNext}
        disabled={!valid}
        style={{
          padding: 'var(--space-3) var(--space-6)',
          background: valid ? 'var(--color-accent-primary)' : 'var(--color-border)',
          color: valid ? 'var(--color-bg-primary)' : 'var(--color-text-muted)',
          border: 'none',
          borderRadius: 'var(--radius-md)',
          fontFamily: 'var(--font-mono)',
          fontWeight: 700,
          cursor: valid ? 'pointer' : 'not-allowed',
          fontSize: 'var(--font-size-sm)',
          alignSelf: 'flex-end',
        }}
      >
        Next →
      </button>
    </div>
  );
}
