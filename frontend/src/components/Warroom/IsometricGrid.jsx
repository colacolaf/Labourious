import { useRef, useState } from 'react';

const TILE_W = 80;
const TILE_H = 40;
const COLS = 8;
const ROWS = 6;

// Convert grid [col, row] to SVG screen [x, y] (isometric projection)
function toScreen(col, row) {
  return {
    x: (col - row) * (TILE_W / 2),
    y: (col + row) * (TILE_H / 2),
  };
}

function GridTile({ col, row }) {
  const { x, y } = toScreen(col, row);
  const pts = [
    [x, y + TILE_H / 2],
    [x + TILE_W / 2, y],
    [x + TILE_W, y + TILE_H / 2],
    [x + TILE_W / 2, y + TILE_H],
  ].map((p) => p.join(',')).join(' ');

  return (
    <polygon
      points={pts}
      fill="var(--color-surface, #0d0d1a)"
      stroke="var(--color-border, #1e1e3a)"
      strokeWidth={0.5}
    />
  );
}

export default function IsometricGrid({ children }) {
  const svgRef = useRef(null);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const dragging = useRef(null);

  const viewW = COLS * TILE_W + 100;
  const viewH = ROWS * TILE_H * 2 + 80;

  function onMouseDown(e) {
    dragging.current = { startX: e.clientX - pan.x, startY: e.clientY - pan.y };
  }
  function onMouseMove(e) {
    if (!dragging.current) return;
    setPan({ x: e.clientX - dragging.current.startX, y: e.clientY - dragging.current.startY });
  }
  function onMouseUp() {
    dragging.current = null;
  }

  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${viewW} ${viewH}`}
      style={{ width: '100%', height: '100%', cursor: dragging.current ? 'grabbing' : 'grab' }}
      onMouseDown={onMouseDown}
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      onMouseLeave={onMouseUp}
    >
      <g transform={`translate(${pan.x + viewW / 2},${pan.y + 40})`}>
        {/* Tiles */}
        {Array.from({ length: ROWS }, (_, row) =>
          Array.from({ length: COLS }, (_, col) => (
            <GridTile key={`${col}-${row}`} col={col} row={row} />
          ))
        )}
        {/* Agent sprites injected as children */}
        {children}
      </g>
    </svg>
  );
}

export { toScreen, TILE_W, TILE_H };
