// Room layout editor: paint the floor/wall tile layers and place/rotate/delete furniture
// for one of the three warroom maps, then persist to the backend (roomLayoutsApi).
//
// ponytail: a plain 2D canvas grid (not a second live Phaser instance) is enough to paint
// tile indices and object rects — reuses the same tile-index -> color mapping map-loader.js's
// fallback painting already uses, without pulling Phaser into an editor page.
import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { OBJECT_TYPES, getObjectFootprint, computeOccupiedTiles } from '../../../lib/object-types';
import { SECTOR_PALETTE } from '../../../game/scenes/palettes/sector-palette';
import { CUBICLE_PALETTE } from '../../../game/scenes/palettes/cubicle-palette';
import { roomLayoutsApi } from '../../../utils/api-client';

const COLS = 40;
const ROWS = 30;
const CELL = 14;

// Matches map-loader.js's TILE_KEY_BY_INDEX / PALETTES tables (design spec's tile index table).
const TILE_KEY_BY_INDEX = { 1: 'floor', 2: 'wall' };
const INDEX_BY_TOOL = { floor: 1, wall: 2, erase: 0 };
const PALETTES = {
  investment: { floor: 0x8b8378, wall: 0x4a4a5e },
  sector: SECTOR_PALETTE,
  cubicle: CUBICLE_PALETTE,
};

const ROOMS = [
  { key: 'long_term', label: 'Long Term', file: 'investment-room', theme: 'investment' },
  { key: 'swing_trading', label: 'Swing Trading', file: 'sector-room', theme: 'sector' },
  { key: 'day_trading', label: 'Day Trading', file: 'day-trading-room', theme: 'cubicle' },
];

function hexToCss(num) {
  return `#${(num ?? 0x999999).toString(16).padStart(6, '0')}`;
}

function emptyLayer() {
  return Array.from({ length: ROWS }, () => Array.from({ length: COLS }, () => 1));
}

async function loadDefaultMap(file) {
  const basePath = process.env.PUBLIC_URL || '';
  const res = await fetch(`${basePath}/maps/${file}.json`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export default function RoomEditor({ roomKey }) {
  const navigate = useNavigate();
  const room = ROOMS.find((r) => r.key === roomKey) || ROOMS[0];

  const [mapData, setMapData] = useState(null);
  const [tool, setTool] = useState('floor'); // 'floor' | 'wall' | 'erase' | 'select' | an OBJECT_TYPES value
  const [selectedObjectId, setSelectedObjectId] = useState(null);
  const [status, setStatus] = useState('');
  const canvasRef = useRef(null);
  const paintingRef = useRef(false);

  useEffect(() => {
    setSelectedObjectId(null);
    setStatus('');
    let cancelled = false;
    (async () => {
      try {
        const saved = await roomLayoutsApi.get(room.key);
        if (cancelled) return;
        if (saved?.custom) {
          setMapData(saved.map_json);
          return;
        }
      } catch (err) {
        console.warn(`[RoomEditor] failed to fetch custom layout: ${err.message}`);
      }
      try {
        const defaultMap = await loadDefaultMap(room.file);
        if (!cancelled) setMapData(defaultMap);
      } catch (err) {
        console.error(`[RoomEditor] failed to load default map: ${err.message}`);
      }
    })();
    return () => { cancelled = true; };
  }, [room.key, room.file]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !mapData) return;
    const ctx = canvas.getContext('2d');
    const palette = PALETTES[mapData.theme] || PALETTES.investment;

    for (let row = 0; row < ROWS; row++) {
      for (let col = 0; col < COLS; col++) {
        const wallIndex = mapData.layers?.walls?.[row]?.[col] || 0;
        const floorIndex = mapData.layers?.floor?.[row]?.[col] || 0;
        const index = wallIndex || floorIndex;
        const key = TILE_KEY_BY_INDEX[index] || 'floor';
        ctx.fillStyle = hexToCss(palette[key] ?? palette.floor);
        ctx.fillRect(col * CELL, row * CELL, CELL, CELL);
        ctx.strokeStyle = 'rgba(0,0,0,0.15)';
        ctx.strokeRect(col * CELL, row * CELL, CELL, CELL);
      }
    }

    (mapData.objects || []).forEach((obj) => {
      const { w, h } = getObjectFootprint(obj.type);
      const x = obj.col * CELL;
      const y = obj.row * CELL;
      ctx.fillStyle = obj.id === selectedObjectId ? '#f59e0b' : '#6366f1';
      ctx.fillRect(x + 1, y + 1, w * CELL - 2, h * CELL - 2);
      ctx.fillStyle = '#fff';
      ctx.font = '8px monospace';
      ctx.fillText(obj.type.slice(0, 2), x + 2, y + CELL - 3);
    });
  }, [mapData, selectedObjectId]);

  useEffect(() => { draw(); }, [draw]);

  const cellFromEvent = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const col = Math.floor((e.clientX - rect.left) / CELL);
    const row = Math.floor((e.clientY - rect.top) / CELL);
    return { col, row };
  };

  const paintTile = (col, row) => {
    if (!INDEX_BY_TOOL.hasOwnProperty(tool)) return;
    if (row < 0 || row >= ROWS || col < 0 || col >= COLS) return;
    setMapData((prev) => {
      const layerName = tool === 'wall' ? 'walls' : 'floor';
      const otherLayer = tool === 'wall' ? 'floor' : 'walls';
      const layers = {
        floor: (prev.layers?.floor || emptyLayer()).map((r) => [...r]),
        walls: (prev.layers?.walls || emptyLayer().map((r) => r.map(() => 0))).map((r) => [...r]),
      };
      layers[layerName][row][col] = INDEX_BY_TOOL[tool];
      if (tool !== 'erase') layers[otherLayer][row][col] = 0;
      return { ...prev, layers };
    });
  };

  const findObjectAt = (col, row) =>
    (mapData.objects || []).find((obj) => {
      const { w, h } = getObjectFootprint(obj.type);
      return col >= obj.col && col < obj.col + w && row >= obj.row && row < obj.row + h;
    });

  const placeObject = (col, row) => {
    const occupied = computeOccupiedTiles(mapData.objects);
    const { w, h } = getObjectFootprint(tool);
    for (let dc = 0; dc < w; dc++) {
      for (let dr = 0; dr < h; dr++) {
        if (occupied.has(`${col + dc},${row + dr}`)) {
          setStatus('Tile occupied — choose an empty spot.');
          return;
        }
      }
    }
    const newObj = { id: `obj-${Date.now()}`, type: tool, col, row, direction: 'down' };
    setMapData((prev) => ({ ...prev, objects: [...(prev.objects || []), newObj] }));
  };

  const handlePointerDown = (e) => {
    const { col, row } = cellFromEvent(e);
    if (tool === 'select') {
      const obj = findObjectAt(col, row);
      setSelectedObjectId(obj?.id || null);
      return;
    }
    if (OBJECT_TYPES.includes(tool)) {
      placeObject(col, row);
      return;
    }
    paintingRef.current = true;
    paintTile(col, row);
  };

  const handlePointerMove = (e) => {
    if (!paintingRef.current) return;
    const { col, row } = cellFromEvent(e);
    paintTile(col, row);
  };

  const stopPainting = () => { paintingRef.current = false; };

  const rotateSelected = () => {
    const order = ['down', 'left', 'up', 'right'];
    setMapData((prev) => ({
      ...prev,
      objects: (prev.objects || []).map((obj) =>
        obj.id === selectedObjectId
          ? { ...obj, direction: order[(order.indexOf(obj.direction || 'down') + 1) % order.length] }
          : obj
      ),
    }));
  };

  const deleteSelected = () => {
    setMapData((prev) => ({ ...prev, objects: (prev.objects || []).filter((o) => o.id !== selectedObjectId) }));
    setSelectedObjectId(null);
  };

  const save = async () => {
    setStatus('Saving…');
    try {
      await roomLayoutsApi.save(room.key, mapData);
      setStatus('Saved.');
    } catch (err) {
      setStatus(`Save failed: ${err.message}`);
    }
  };

  const reset = async () => {
    setStatus('Resetting…');
    try {
      await roomLayoutsApi.reset(room.key);
      const defaultMap = await loadDefaultMap(room.file);
      setMapData(defaultMap);
      setSelectedObjectId(null);
      setStatus('Reset to default.');
    } catch (err) {
      setStatus(`Reset failed: ${err.message}`);
    }
  };

  const toolButtonStyle = (active) => ({
    padding: '0.3rem 0.6rem',
    fontFamily: 'var(--font-mono)',
    fontSize: '0.7rem',
    cursor: 'pointer',
    borderRadius: 3,
    border: `1px solid ${active ? 'var(--color-accent-primary)' : 'var(--color-border)'}`,
    background: active ? 'var(--color-accent-primary)' : 'var(--color-bg-tertiary)',
    color: active ? 'var(--color-text-inverse, #111827)' : 'var(--color-text-secondary)',
  });

  return (
    <div style={{ padding: 'var(--space-4)', fontFamily: 'var(--font-mono)', color: 'var(--color-text-primary)' }}>
      <div style={{ display: 'flex', gap: 'var(--space-2)', marginBottom: 'var(--space-4)' }}>
        {ROOMS.map((r) => (
          <button
            key={r.key}
            onClick={() => navigate(`/editor/room/${r.key}`)}
            style={toolButtonStyle(r.key === room.key)}
          >
            {r.label}
          </button>
        ))}
      </div>

      {!mapData ? (
        <div style={{ color: 'var(--color-text-muted)' }}>Loading…</div>
      ) : (
        <div style={{ display: 'flex', gap: 'var(--space-4)', alignItems: 'flex-start' }}>
          <canvas
            ref={canvasRef}
            width={COLS * CELL}
            height={ROWS * CELL}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={stopPainting}
            onPointerLeave={stopPainting}
            style={{ border: '1px solid var(--color-border)', cursor: 'crosshair' }}
          />

          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', minWidth: 180 }}>
            <div>
              <div style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', marginBottom: 'var(--space-1)' }}>TILES</div>
              <div style={{ display: 'flex', gap: 'var(--space-1)' }}>
                <button style={toolButtonStyle(tool === 'floor')} onClick={() => setTool('floor')}>Floor</button>
                <button style={toolButtonStyle(tool === 'wall')} onClick={() => setTool('wall')}>Wall</button>
                <button style={toolButtonStyle(tool === 'erase')} onClick={() => setTool('erase')}>Erase</button>
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', marginBottom: 'var(--space-1)' }}>OBJECTS</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-1)' }}>
                {OBJECT_TYPES.map((type) => (
                  <button key={type} style={toolButtonStyle(tool === type)} onClick={() => setTool(type)}>
                    {type}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', marginBottom: 'var(--space-1)' }}>SELECT / EDIT</div>
              <div style={{ display: 'flex', gap: 'var(--space-1)' }}>
                <button style={toolButtonStyle(tool === 'select')} onClick={() => setTool('select')}>Select</button>
                <button style={toolButtonStyle(false)} onClick={rotateSelected} disabled={!selectedObjectId}>Rotate</button>
                <button style={toolButtonStyle(false)} onClick={deleteSelected} disabled={!selectedObjectId}>Delete</button>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 'var(--space-1)', marginTop: 'var(--space-2)' }}>
              <button
                onClick={save}
                style={{ ...toolButtonStyle(true), flex: 1 }}
              >
                Save
              </button>
              <button onClick={reset} style={{ ...toolButtonStyle(false), flex: 1 }}>Reset</button>
            </div>

            {status && <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>{status}</div>}
          </div>
        </div>
      )}
    </div>
  );
}
