import { motion, AnimatePresence } from 'framer-motion';

const side = (s) => (s === 'buy' ? 'var(--color-accent-primary)' : 'var(--color-accent-danger)');
const pnlColor = (v) => (v == null ? 'var(--color-text-muted)' : v >= 0 ? 'var(--color-pnl-positive, var(--color-accent-primary))' : 'var(--color-pnl-negative, var(--color-accent-danger))');

function fmt(n) {
  if (n == null) return '—';
  const abs = Math.abs(n);
  const s = abs >= 1000 ? `$${(abs / 1000).toFixed(1)}k` : `$${abs.toFixed(2)}`;
  return n < 0 ? `-${s}` : `+${s}`;
}

function timeStr(dt) {
  if (!dt) return '';
  const d = new Date(dt);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

const row = {
  display: 'grid',
  gridTemplateColumns: '48px 100px 1fr 80px 60px',
  gap: 'var(--space-3)',
  padding: 'var(--space-2) var(--space-3)',
  alignItems: 'center',
  borderBottom: '1px solid var(--color-border-subtle, var(--color-border))',
  fontFamily: 'var(--font-mono)',
  fontSize: 'var(--font-size-sm)',
};

export default function RecentTradesFeed({ trades }) {
  if (!trades || trades.length === 0) {
    return (
      <div style={{ padding: 'var(--space-4)', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)', fontFamily: 'var(--font-mono)' }}>
        No trades
      </div>
    );
  }

  return (
    <div>
      <div style={{ ...row, fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', letterSpacing: '0.08em', borderBottom: '1px solid var(--color-border)' }}>
        <div>SIDE</div>
        <div>SYMBOL</div>
        <div>AGENT</div>
        <div>P&L</div>
        <div>TIME</div>
      </div>
      <AnimatePresence initial={false}>
        {trades.slice(0, 15).map((t) => (
          <motion.div
            key={t.id}
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0, transition: { duration: 0.2 } }}
            style={row}
          >
            <div style={{ color: side(t.side), fontWeight: 700, fontSize: 'var(--font-size-xs)' }}>
              {t.side?.toUpperCase()}
            </div>
            <div style={{ color: 'var(--color-text-primary)' }}>{t.symbol}</div>
            <div style={{ color: 'var(--color-text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {t.agent_id}
            </div>
            <div style={{ color: pnlColor(t.pnl) }}>{fmt(t.pnl)}</div>
            <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)' }}>
              {timeStr(t.opened_at)}
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
