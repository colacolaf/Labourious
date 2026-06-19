import { useState, useCallback } from 'react';
import useAgentsStore from '../../stores/agents.store';

const VARS = [
  '${RSI_14}', '${MA_20}', '${MA_50}', '${PRICE}', '${VOLUME}',
  '${MACD}', '${BB_UPPER}', '${BB_LOWER}', '${ATR}',
];

const ROOMS = ['day_trading', 'swing_trading', 'long_term'];
const BROKERS = ['alpaca', 'binance'];

export default function ContextBuilder({ onCreated }) {
  const { createAgent, loading, error } = useAgentsStore();
  const [form, setForm] = useState({
    name: '',
    symbol: 'AAPL',
    room: 'day_trading',
    broker: 'alpaca',
    context: '',
    use_local_llm: true,
    is_paper_trading: true,
  });
  const [showVars, setShowVars] = useState(false);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    if (!form.name.trim() || !form.context.trim()) return;
    const agent = await createAgent({
      name: form.name,
      symbol: form.symbol,
      room: form.room,
      broker: form.broker,
      use_local_llm: form.use_local_llm,
      is_paper_trading: form.is_paper_trading,
      strategy_config: { context: form.context },
    });
    onCreated?.(agent);
    setForm((f) => ({ ...f, name: '', context: '' }));
  }, [form, createAgent, onCreated]);

  const inp = {
    background: 'var(--color-bg-tertiary)',
    border: '1px solid var(--color-border)',
    borderRadius: 4,
    padding: '0.5rem',
    color: 'var(--color-text-primary)',
    fontFamily: 'var(--font-mono)',
    fontSize: '0.8rem',
    width: '100%',
    boxSizing: 'border-box',
  };

  const lbl = { fontSize: '0.65rem', color: 'var(--color-text-muted)', letterSpacing: '0.08em', display: 'block', marginBottom: 4 };

  return (
    <form onSubmit={handleSubmit} style={{ fontFamily: 'var(--font-mono)', maxWidth: 500 }}>
      <div style={{ fontSize: '0.65rem', color: 'var(--color-accent-primary)', letterSpacing: '0.15em', marginBottom: '1.25rem' }}>
        CREATE AGENT
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
        <div>
          <label style={lbl}>AGENT NAME *</label>
          <input style={inp} value={form.name} onChange={(e) => set('name', e.target.value)} placeholder="e.g. Alpha-RSI" required />
        </div>
        <div>
          <label style={lbl}>SYMBOL</label>
          <input style={inp} value={form.symbol} onChange={(e) => set('symbol', e.target.value)} placeholder="AAPL / BTC/USDT" />
        </div>
        <div>
          <label style={lbl}>ROOM</label>
          <select style={inp} value={form.room} onChange={(e) => set('room', e.target.value)}>
            {ROOMS.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
        <div>
          <label style={lbl}>BROKER</label>
          <select style={inp} value={form.broker} onChange={(e) => set('broker', e.target.value)}>
            {BROKERS.map((b) => <option key={b} value={b}>{b}</option>)}
          </select>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
        {[['use_local_llm', 'Use Local LLM (Ollama)'], ['is_paper_trading', 'Paper Trading']].map(([k, label]) => (
          <label key={k} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.8rem', cursor: 'pointer' }}>
            <input type="checkbox" checked={form[k]} onChange={(e) => set(k, e.target.checked)} />
            <span style={{ color: 'var(--color-text-secondary)' }}>{label}</span>
          </label>
        ))}
      </div>

      <div style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
          <label style={{ ...lbl, marginBottom: 0 }}>CONTEXT / TRADING RULES *</label>
          <button
            type="button"
            onClick={() => setShowVars((v) => !v)}
            style={{ background: 'none', border: 'none', color: 'var(--color-accent-primary)', fontFamily: 'var(--font-mono)', fontSize: '0.65rem', cursor: 'pointer' }}
          >
            {showVars ? '▲ hide vars' : '▼ show vars'}
          </button>
        </div>

        {showVars && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 6 }}>
            {VARS.map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => set('context', form.context + v)}
                style={{
                  background: 'var(--color-bg-tertiary)',
                  border: '1px solid var(--color-border)',
                  color: 'var(--color-accent-primary)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.65rem',
                  padding: '2px 6px',
                  borderRadius: 3,
                  cursor: 'pointer',
                }}
              >
                {v}
              </button>
            ))}
          </div>
        )}

        <textarea
          style={{ ...inp, minHeight: 120, resize: 'vertical' }}
          value={form.context}
          onChange={(e) => set('context', e.target.value)}
          placeholder={`Buy when ${VARS[0]} < 30 and ${VARS[1]} > ${VARS[2]}\nSell when ${VARS[0]} > 70`}
          required
        />
      </div>

      {error && <div style={{ color: '#ff4444', fontSize: '0.75rem', marginBottom: '0.75rem' }}>{error}</div>}

      <button
        type="submit"
        disabled={loading || !form.name.trim() || !form.context.trim()}
        style={{
          padding: '0.6rem 1.5rem',
          background: 'var(--color-accent-primary, #00ff88)',
          color: '#000',
          border: 'none',
          borderRadius: 4,
          fontFamily: 'var(--font-mono)',
          fontWeight: 700,
          fontSize: '0.8rem',
          cursor: 'pointer',
          opacity: (loading || !form.name.trim() || !form.context.trim()) ? 0.5 : 1,
        }}
      >
        {loading ? 'CREATING...' : 'CREATE AGENT'}
      </button>
    </form>
  );
}
