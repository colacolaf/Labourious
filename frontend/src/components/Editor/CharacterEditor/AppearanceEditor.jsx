// LPC character appearance editor: pick an item+variant per registry category, preview the
// composited walk-sheet live, and save to either an agent's or the current user's appearance.
import { useEffect, useRef, useState } from 'react';
import { loadRegistry, getItemVariants } from '../../../lib/lpc-registry';
import { compositeCharacter } from '../../../lib/sprite-compositor';
import { agentAppearanceApi } from '../../../utils/api-client';

const EMPTY_APPEARANCE = { bodyType: 'male', layers: {} };

export default function AppearanceEditor({ agentId }) {
  const [registry, setRegistry] = useState(null);
  const [appearance, setAppearance] = useState(EMPTY_APPEARANCE);
  const [status, setStatus] = useState('');
  const canvasRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const reg = await loadRegistry();
        if (!cancelled) setRegistry(reg);
      } catch (err) {
        console.error(`[AppearanceEditor] failed to load LPC registry: ${err.message}`);
      }
      try {
        const res = agentId ? await agentAppearanceApi.get(agentId) : await agentAppearanceApi.getUserAvatar();
        if (!cancelled && res?.appearance) setAppearance(res.appearance);
      } catch (err) {
        console.warn(`[AppearanceEditor] failed to load existing appearance: ${err.message}`);
      }
    })();
    return () => { cancelled = true; };
  }, [agentId]);

  useEffect(() => {
    if (canvasRef.current) {
      compositeCharacter(canvasRef.current, appearance).catch((err) => {
        console.warn(`[AppearanceEditor] preview composite failed: ${err.message}`);
      });
    }
  }, [appearance]);

  const setBodyType = (bodyType) => setAppearance((prev) => ({ ...prev, bodyType }));

  const setLayer = (categoryId, itemKey, variant) => {
    setAppearance((prev) => ({
      ...prev,
      layers: { ...prev.layers, [categoryId]: itemKey ? { itemKey, variant } : null },
    }));
  };

  const save = async () => {
    setStatus('Saving…');
    try {
      if (agentId) await agentAppearanceApi.save(agentId, appearance);
      else await agentAppearanceApi.saveUserAvatar(appearance);
      setStatus('Saved.');
    } catch (err) {
      setStatus(`Save failed: ${err.message}`);
    }
  };

  if (!registry) {
    return <div style={{ color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>Loading…</div>;
  }

  return (
    <div style={{ display: 'flex', gap: 'var(--space-4)', fontFamily: 'var(--font-mono)', color: 'var(--color-text-primary)', padding: 'var(--space-4)' }}>
      <div>
        <canvas
          ref={canvasRef}
          width={64}
          height={64}
          style={{
            width: 128, height: 128, imageRendering: 'pixelated',
            border: '1px solid var(--color-border)', background: 'var(--color-bg-tertiary)',
          }}
        />
        <div style={{ marginTop: 'var(--space-2)', display: 'flex', gap: 'var(--space-1)' }}>
          {['male', 'female'].map((bt) => (
            <button
              key={bt}
              onClick={() => setBodyType(bt)}
              style={{
                padding: '0.3rem 0.6rem', fontFamily: 'var(--font-mono)', fontSize: '0.7rem', cursor: 'pointer',
                borderRadius: 3,
                border: `1px solid ${appearance.bodyType === bt ? 'var(--color-accent-primary)' : 'var(--color-border)'}`,
                background: appearance.bodyType === bt ? 'var(--color-accent-primary)' : 'var(--color-bg-tertiary)',
                color: appearance.bodyType === bt ? 'var(--color-text-inverse, #111827)' : 'var(--color-text-secondary)',
              }}
            >
              {bt}
            </button>
          ))}
        </div>
        <button
          onClick={save}
          style={{
            marginTop: 'var(--space-3)', width: '100%', padding: '0.5rem',
            background: 'var(--color-accent-primary)', color: 'var(--color-text-inverse, #111827)',
            border: 'none', fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.8rem',
            cursor: 'pointer', borderRadius: 3,
          }}
        >
          Save
        </button>
        {status && <div style={{ marginTop: 'var(--space-2)', fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>{status}</div>}
      </div>

      <div style={{ flex: 1, maxHeight: 480, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
        {registry.categories.map((category) => {
          const currentLayer = appearance.layers?.[category.id];
          const currentItem = category.items.find((i) => i.key === currentLayer?.itemKey);
          return (
            <div key={category.id} style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center', fontSize: '0.75rem' }}>
              <span style={{ width: 120, color: 'var(--color-text-muted)' }}>{category.label}</span>
              <select
                value={currentLayer?.itemKey || ''}
                onChange={(e) => setLayer(category.id, e.target.value || null, category.items.find((i) => i.key === e.target.value)?.variants?.[0])}
                style={{ background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)', fontSize: '0.7rem' }}
              >
                <option value="">— none —</option>
                {category.items.map((item) => (
                  <option key={item.key} value={item.key}>{item.name}</option>
                ))}
              </select>
              {currentItem && (
                <select
                  value={currentLayer?.variant || ''}
                  onChange={(e) => setLayer(category.id, currentLayer.itemKey, e.target.value)}
                  style={{ background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)', fontSize: '0.7rem' }}
                >
                  {getItemVariants(currentItem).map((v) => (
                    <option key={v} value={v}>{v}</option>
                  ))}
                </select>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
