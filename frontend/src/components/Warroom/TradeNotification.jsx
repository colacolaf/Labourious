import { motion, AnimatePresence } from 'framer-motion';
import { useEffect } from 'react';

// ponytail: pop-in → hold → fade, auto-removes via onDone callback
export default function TradeNotification({ trade, svgX, svgY, onDone }) {
  const isGain = (trade?.pnl ?? 0) >= 0;
  const color = isGain ? '#00ff88' : '#ff4444';
  const label = trade?.pnl != null
    ? `${isGain ? '+' : ''}$${trade.pnl.toFixed(2)}`
    : trade?.side ?? '';

  useEffect(() => {
    const t = setTimeout(onDone, 3200);
    return () => clearTimeout(t);
  }, [onDone]);

  return (
    <AnimatePresence>
      <motion.g
        initial={{ opacity: 0, y: 8, scale: 0.8 }}
        animate={{ opacity: 1, y: 0, scale: 1, transition: { duration: 0.2 } }}
        exit={{ opacity: 0, y: -8, transition: { duration: 0.5, delay: 2.5 } }}
      >
        <rect
          x={svgX - 28}
          y={svgY - 36}
          width={56}
          height={18}
          rx={4}
          fill={color}
          fillOpacity={0.9}
        />
        <text
          x={svgX}
          y={svgY - 23}
          textAnchor="middle"
          fontSize={9}
          fontWeight="bold"
          fill="#000"
          style={{ userSelect: 'none' }}
        >
          {label}
        </text>
      </motion.g>
    </AnimatePresence>
  );
}
