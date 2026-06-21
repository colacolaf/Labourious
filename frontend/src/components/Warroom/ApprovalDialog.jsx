import { motion, AnimatePresence } from 'framer-motion';
import { useState, useEffect, useCallback } from 'react';

const DEFAULT_TIMEOUT = 30;

export default function ApprovalDialog({ approval, onDecide }) {
  const [remaining, setRemaining] = useState(DEFAULT_TIMEOUT);

  useEffect(() => {
    if (!approval) return;
    // Derive initial seconds from expires_at if available
    if (approval.expires_at) {
      const secs = Math.max(0, Math.round((new Date(approval.expires_at) - Date.now()) / 1000));
      setRemaining(secs || DEFAULT_TIMEOUT);
    } else {
      setRemaining(DEFAULT_TIMEOUT);
    }
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

  const maxSecs = remaining > 0 ? Math.max(DEFAULT_TIMEOUT, remaining) : DEFAULT_TIMEOUT;
  const urgentColor = remaining <= 5 ? 'var(--color-danger, #ff4444)' : 'var(--color-accent-primary, #00ff88)';

  return (
    <AnimatePresence>
      {approval && (
        <motion.div
          initial={{ opacity: 0, y: -60 }}
          animate={{ opacity: 1, y: 0, transition: { type: 'spring', stiffness: 300, damping: 25 } }}
          exit={{ opacity: 0, y: -60, transition: { duration: 0.2 } }}
          style={{
            position: 'fixed', inset: 0, zIndex: 1000,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'rgba(0,0,0,0.75)',
          }}
        >
          <div style={{
            background: 'var(--color-bg-secondary)', border: `1px solid ${urgentColor}`,
            borderRadius: 8, padding: '2rem', maxWidth: 420, width: '90%',
            fontFamily: 'var(--font-mono)',
          }}>
            <div style={{ color: 'var(--color-accent-primary)', fontSize: '0.7rem', marginBottom: 4 }}>
              TRADE APPROVAL REQUIRED
            </div>
            <div style={{ fontSize: '1.1rem', color: 'var(--color-text-primary)', marginBottom: '1.5rem' }}>
              {approval.agent_name ?? `Agent #${approval.agent_id}`}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem 1rem', fontSize: '0.8rem', marginBottom: '1.5rem' }}>
              {[
                ['Symbol', approval.symbol],
                ['Action', approval.action ?? approval.side],
                ['Size $', approval.position_size_dollars?.toFixed?.(2) ?? approval.quantity?.toFixed?.(4) ?? '—'],
                ['Confidence', approval.confidence != null ? `${(approval.confidence * 100).toFixed(0)}%` : '—'],
              ].map(([label, val]) => (
                <div key={label}>
                  <span style={{ color: 'var(--color-text-muted)' }}>{label}: </span>
                  <span style={{ color: 'var(--color-text-primary)' }}>{val}</span>
                </div>
              ))}
            </div>
            {approval.reasoning && (
              <div style={{
                fontSize: '0.75rem', color: 'var(--color-text-secondary)',
                background: 'var(--color-bg-tertiary)', padding: '0.75rem',
                borderRadius: 4, marginBottom: '1.5rem', lineHeight: 1.5,
              }}>
                {approval.reasoning}
              </div>
            )}
            <div style={{ marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--color-text-muted)', marginBottom: 4 }}>
                <span>Auto-reject in</span>
                <span style={{ color: remaining <= 5 ? 'var(--color-danger, #ff4444)' : 'inherit' }}>{remaining}s</span>
              </div>
              <div style={{ height: 3, background: 'var(--color-border)', borderRadius: 2 }}>
                <motion.div
                  style={{ height: '100%', borderRadius: 2, background: urgentColor }}
                  animate={{ width: `${(remaining / maxSecs) * 100}%` }}
                  transition={{ duration: 1, ease: 'linear' }}
                />
              </div>
            </div>
            <div style={{ display: 'flex', gap: '1rem' }}>
              <button onClick={handleApprove} style={{
                flex: 1, padding: '0.6rem', background: 'var(--color-accent-primary, #00ff88)',
                color: '#000', border: 'none', borderRadius: 4, fontFamily: 'inherit',
                fontWeight: 700, fontSize: '0.85rem', cursor: 'pointer',
              }}>APPROVE</button>
              <button onClick={handleReject} style={{
                flex: 1, padding: '0.6rem', background: 'transparent',
                color: 'var(--color-danger, #ff4444)', border: '1px solid var(--color-danger, #ff4444)',
                borderRadius: 4, fontFamily: 'inherit', fontWeight: 700, fontSize: '0.85rem', cursor: 'pointer',
              }}>REJECT</button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
