import React from 'react';
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

const slideVariants = {
  initial: { x: 40, opacity: 0 },
  animate: { x: 0, opacity: 1, transition: { duration: 0.3, ease: 'easeOut' } },
  exit: { x: -40, opacity: 0, transition: { duration: 0.2, ease: 'easeIn' } },
};

export default function WizardShell() {
  const { currentStep, prevStep } = useWizardStore((s) => ({ currentStep: s.currentStep, prevStep: s.prevStep }));
  const StepComponent = STEPS[currentStep].component;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(10,10,15,0.92)',
        backdropFilter: 'blur(4px)',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: 520,
          background: 'var(--color-bg-secondary)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-xl)',
          boxShadow: 'var(--shadow-elevated)',
          overflow: 'hidden',
        }}
      >
        {/* Progress bar */}
        <div style={{ padding: 'var(--space-6) var(--space-8) var(--space-4)', borderBottom: '1px solid var(--color-border-subtle)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 'var(--space-2)' }}>
            {STEPS.map((s, i) => (
              <React.Fragment key={s.label}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--space-1)' }}>
                  <div style={{
                    width: 28,
                    height: 28,
                    borderRadius: '50%',
                    border: `2px solid ${i <= currentStep ? 'var(--color-accent-primary)' : 'var(--color-border)'}`,
                    background: i < currentStep ? 'var(--color-accent-primary)' : i === currentStep ? 'var(--color-bg-elevated)' : 'transparent',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 'var(--font-size-xs)',
                    color: i <= currentStep ? 'var(--color-accent-primary)' : 'var(--color-text-muted)',
                    fontWeight: 700,
                  }}>
                    {i < currentStep ? '✓' : i + 1}
                  </div>
                  <span style={{ fontSize: 'var(--font-size-xs)', color: i === currentStep ? 'var(--color-text-primary)' : 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {s.label}
                  </span>
                </div>
                {i < STEPS.length - 1 && (
                  <div style={{ flex: 1, height: 2, background: i < currentStep ? 'var(--color-accent-primary)' : 'var(--color-border)', marginBottom: 'var(--space-4)' }} />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Step content — all steps own their own Next/Skip buttons */}
        <div style={{ padding: 'var(--space-8)', minHeight: 360, overflow: 'hidden', position: 'relative' }}>
          <AnimatePresence mode="wait">
            <motion.div key={currentStep} variants={slideVariants} initial="initial" animate="animate" exit="exit">
              <StepComponent />
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Back button (shared) */}
        {currentStep > 0 && (
          <div style={{ padding: 'var(--space-2) var(--space-8) var(--space-4)', borderTop: '1px solid var(--color-border-subtle)' }}>
            <button
              onClick={prevStep}
              style={{
                padding: 'var(--space-2) var(--space-4)',
                background: 'transparent',
                color: 'var(--color-text-muted)',
                border: 'none',
                fontFamily: 'var(--font-mono)',
                fontSize: 'var(--font-size-sm)',
                cursor: 'pointer',
              }}
            >
              ← Back
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
