import { motion, AnimatePresence } from 'framer-motion';
import { useState, useEffect, useCallback } from 'react';

const TIMEOUT_SECS = 30;

// ponytail: inline styles match retro terminal theme via CSS vars
export default function ApprovalDialog({ approval, onDecide }) {
  const [remaining, setRemaining] = useState(TIMEOUT_SECS);

  // Countdown → auto-reject at 0
  useEffect(() => {
    if (!approval) return;
    setRemaining(TIMEOUT_SECS);
    const interval = setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) {
          onDecide(approval.trade_id, false);
          return 0;
        }
        return r - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [approval, onDecide]);

  const handleApprove = useCallback(() => onDecide(approval.trade_id, true), [approval, onDecide]);
  const handleReject = useCallback(() => onDecide(approval.trade_id, false), [approval, onDecide]);

  return (
    <AnimatePresence>
      {approval && (
        <motion.div
          initial={{ opacity: 0, y: -60 }}
          animate={{ opacity: 1, y: 0, transition: { type: 'spring', stiffness: 300, damping: 25 } }}
          exit={{ opacity: 0, y: -60, transition: { duration: 0.2 } }}
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'rgba(0,0,0,0.75)',
          }}
        >
          <div
            style={{
              background: 'var(--color-bg-secondary, #0d1117)',
              border: '1px solid var(--color-accent-primary, #00ff88)',
              borderRadius: 8,
              padding: '2rem',
              maxWidth: 420,
              width: '90%',
              fontFamily: 'var(--font-mono, monospace)',
            }}
          >
            <div style={{ color: 'var(--color-accent-primary, #00ff88)', fontSize: '0.7rem', marginBottom: 4 }}>
              TRADE APPROVAL REQUIRED
            </div>
            <div style={{ fontSize: '1.1rem', color: 'var(--color-text-primary, #e0e0e0)', marginBottom: '1.5rem' }}>
              {approval.agent_name ?? `Agent #${approval.agent_id}`}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem 1rem', fontSize: '0.8rem', marginBottom: '1.5rem' }}>
              {[
                ['Symbol', approval.symbol],
                ['Side', approval.side],
                ['Qty', approval.quantity?.toFixed?.(4) ?? approval.quantity],
                ['Confidence', approval.confidence != null ? `${(approval.confidence * 100).toFixed(0)}%` : '—'],
              ].map(([label, val]) => (
                <div key={label}>
                  <span style={{ color: 'var(--color-text-muted, #666)' }}>{label}: </span>
                  <span style={{ color: 'var(--color-text-primary, #e0e0e0)' }}>{val}</span>
                </div>
              ))}
            </div>

            {approval.reasoning && (
              <div style={{
                fontSize: '0.75rem',
                color: 'var(--color-text-secondary, #aaa)',
                background: 'var(--color-bg-tertiary, #161b22)',
                padding: '0.75rem',
                borderRadius: 4,
                marginBottom: '1.5rem',
                lineHeight: 1.5,
              }}>
                {approval.reasoning}
              </div>
            )}

            {/* Countdown bar */}
            <div style={{ marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--color-text-muted, #666)', marginBottom: 4 }}>
                <span>Auto-reject in</span>
                <span style={{ color: remaining <= 5 ? '#ff4444' : 'inherit' }}>{remaining}s</span>
              </div>
              <div style={{ height: 3, background: 'var(--color-border, #1e1e3a)', borderRadius: 2 }}>
                <motion.div
                  style={{ height: '100%', borderRadius: 2, background: remaining <= 5 ? '#ff4444' : 'var(--color-accent-primary, #00ff88)' }}
                  animate={{ width: `${(remaining / TIMEOUT_SECS) * 100}%` }}
                  transition={{ duration: 1, ease: 'linear' }}
                />
              </div>
            </div>

            <div style={{ display: 'flex', gap: '1rem' }}>
              <button
                onClick={handleApprove}
                style={{
                  flex: 1,
                  padding: '0.6rem',
                  background: 'var(--color-accent-primary, #00ff88)',
                  color: '#000',
                  border: 'none',
                  borderRadius: 4,
                  fontFamily: 'inherit',
                  fontWeight: 700,
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                }}
              >
                ✅ APPROVE
              </button>
              <button
                onClick={handleReject}
                style={{
                  flex: 1,
                  padding: '0.6rem',
                  background: 'transparent',
                  color: '#ff4444',
                  border: '1px solid #ff4444',
                  borderRadius: 4,
                  fontFamily: 'inherit',
                  fontWeight: 700,
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                }}
              >
                ❌ REJECT
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
