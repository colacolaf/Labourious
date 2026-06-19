import { motion } from 'framer-motion';
import { toScreen, TILE_W, TILE_H } from './IsometricGrid';

const STATUS_COLOR = {
  running: '#00ff88',
  idle: '#00d4ff',
  paused: '#666',
  error: '#ff4444',
  stopped: '#555',
};

// Framer Motion variants per status
const spriteVariants = {
  running: {
    y: [0, -4, 0],
    transition: { repeat: Infinity, duration: 1.2, ease: 'easeInOut' },
  },
  idle: {
    y: [0, -2, 0],
    transition: { repeat: Infinity, duration: 3, ease: 'easeInOut' },
  },
  paused: { opacity: 0.45, scale: 0.9 },
  error: {
    rotate: [-2, 2, -2],
    transition: { repeat: Infinity, duration: 0.3 },
  },
  stopped: { opacity: 0.3 },
};

const pulseVariants = {
  running: {
    scale: [1, 1.6, 1],
    opacity: [0.6, 0, 0.6],
    transition: { repeat: Infinity, duration: 0.8 },
  },
  default: { scale: 1, opacity: 0 },
};

export default function AgentSprite({ agent, onClick }) {
  const { x, y } = toScreen(agent.grid_col ?? 0, agent.grid_row ?? 0);
  const status = agent.status ?? 'idle';
  const color = STATUS_COLOR[status] ?? STATUS_COLOR.idle;
  const cx = x + TILE_W / 2;
  const cy = y + TILE_H / 2;

  return (
    <motion.g
      key={agent.id}
      style={{ cursor: 'pointer' }}
      onClick={() => onClick?.(agent)}
      whileHover={{ scale: 1.12 }}
      title={agent.name}
    >
      {/* Pulse ring (running only) */}
      <motion.circle
        cx={cx}
        cy={cy}
        r={14}
        fill="none"
        stroke={color}
        strokeWidth={2}
        variants={pulseVariants}
        animate={status === 'running' ? 'running' : 'default'}
      />

      {/* Body */}
      <motion.rect
        x={cx - 12}
        y={cy - 20}
        width={24}
        height={24}
        rx={4}
        fill={color}
        fillOpacity={status === 'paused' || status === 'stopped' ? 0.35 : 0.9}
        variants={spriteVariants}
        animate={status}
      />

      {/* Label */}
      <text
        x={cx}
        y={cy + 14}
        textAnchor="middle"
        fontSize={8}
        fill="var(--color-text-muted, #888)"
        style={{ userSelect: 'none' }}
      >
        {agent.name.length > 10 ? agent.name.slice(0, 10) + '…' : agent.name}
      </text>

      {/* Confidence badge */}
      <text
        x={cx}
        y={cy - 7}
        textAnchor="middle"
        fontSize={7}
        fill="#fff"
        fontWeight="bold"
        style={{ userSelect: 'none' }}
      >
        {agent.confidence_score ?? 10}%
      </text>
    </motion.g>
  );
}
