import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import useWizardStore from '../../stores/wizard.store';
import WelcomeStep from './WelcomeStep';
import BrokerStep from './BrokerStep';
import LLMStep from './LLMStep';
import AllocationStep from './AllocationStep';
import AgentsStep from './AgentsStep';

const STEPS = [
  { label: 'Welcome', component: WelcomeStep },
  { label: 'Broker', component: BrokerStep },
  { label: 'LLM', component: LLMStep },
  { label: 'Allocation', component: AllocationStep },
  { label: 'Agents', component: AgentsStep },
];

const WIZARD_COMPLETE_KEY = 'labourious-setup-complete';

const slideVariants = {
  initial: { x: 40, opacity: 0 },
  animate: { x: 0, opacity: 1, transition: { duration: 0.3, ease: 'easeOut' } },
  exit: { x: -40, opacity: 0, transition: { duration: 0.2, ease: 'easeIn' } },
};

function handleSkip() {
  try {
    localStorage.setItem(WIZARD_COMPLETE_KEY, 'true');
  } catch { /* ignore */ }
}

function handleComplete() {
  try {
    localStorage.setItem(WIZARD_COMPLETE_KEY, 'true');
  } catch { /* ignore */ }
}

export default function WizardShell() {
  const navigate = useNavigate();
  const currentStep = useWizardStore((s) => s.currentStep);
  const prevStep = useWizardStore((s) => s.prevStep);
  const StepComponent = STEPS[currentStep].component;

  // If wizard was already completed, redirect to lobby
  useEffect(() => {
    try {
      if (localStorage.getItem(WIZARD_COMPLETE_KEY) === 'true') {
        navigate('/lobby', { replace: true });
      }
    } catch { /* ignore */ }
  }, [navigate]);

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg-primary)',
        padding: '2rem',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: 520,
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-primary)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-md)',
          overflow: 'hidden',
        }}
      >
        {/* Progress bar */}
        <div style={{ padding: '1.5rem 2rem 1rem', borderBottom: '1px solid var(--border-primary)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.5rem' }}>
            {STEPS.map((s, i) => (
              <React.Fragment key={s.label}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.25rem' }}>
                  <div style={{
                    width: 28, height: 28, borderRadius: '50%',
                    border: `2px solid ${i <= currentStep ? 'var(--accent-primary)' : 'var(--border-primary)'}`,
                    background: i < currentStep ? 'var(--accent-primary)' : i === currentStep ? 'var(--bg-secondary)' : 'transparent',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontFamily: 'var(--font-mono)', fontSize: '11px',
                    color: i <= currentStep ? 'var(--accent-primary)' : 'var(--text-muted)',
                    fontWeight: 700,
                  }}>
                    {i < currentStep ? '✓' : i + 1}
                  </div>
                  <span style={{ fontSize: '10px', color: i === currentStep ? 'var(--text-primary)' : 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {s.label}
                  </span>
                </div>
                {i < STEPS.length - 1 && (
                  <div style={{ flex: 1, height: 2, background: i < currentStep ? 'var(--accent-primary)' : 'var(--border-primary)', marginBottom: '1rem' }} />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Step content */}
        <div style={{ padding: '2rem', minHeight: 360, overflow: 'hidden', position: 'relative' }}>
          <AnimatePresence mode="wait">
            <motion.div key={currentStep} variants={slideVariants} initial="initial" animate="animate" exit="exit">
              <StepComponent onComplete={handleComplete} />
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Bottom bar: Back + Skip */}
        <div style={{
          padding: '0.5rem 2rem 1rem',
          borderTop: '1px solid var(--border-primary)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          {currentStep > 0 ? (
            <button
              onClick={prevStep}
              style={{
                padding: '0.5rem 1rem',
                background: 'transparent',
                color: 'var(--text-muted)',
                border: 'none',
                fontFamily: 'var(--font-mono)',
                fontSize: '12px',
                cursor: 'pointer',
              }}
            >
              ← Back
            </button>
          ) : <span />}

          <button
            onClick={() => {
              handleSkip();
              navigate('/lobby', { replace: true });
            }}
            style={{
              padding: '0.4rem 1rem',
              background: 'transparent',
              color: 'var(--text-muted)',
              border: '1px solid var(--border-primary)',
              borderRadius: 'var(--radius-sm)',
              fontFamily: 'var(--font-mono)',
              fontSize: '11px',
              cursor: 'pointer',
            }}
          >
            Skip for now
          </button>
        </div>
      </div>
    </div>
  );
}