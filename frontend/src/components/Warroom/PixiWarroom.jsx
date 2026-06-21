import React, { useEffect, useRef } from 'react';
import * as PIXI from 'pixi.js';
import { WalkingAgent } from './sprites/WalkingAgent';
import { SeatedAgent } from './sprites/SeatedAgent';
import { ChaosSymbol } from './sprites/ChaosSymbol';
import { drawBloomberg } from './rooms/bloomberg';
import { drawOak } from './rooms/oak';
import { drawPit } from './rooms/pit';
import { useWarroomAgents } from './hooks/useWarroomAgents';

const ROOM_W = 780;
const ROOM_H = 600;

const BLOOMBERG_SHIRTS = [0x1a3a6a, 0x1a5a3a, 0x3a1a5a, 0x5a3a1a, 0x1a4a5a, 0x5a1a3a, 0x3a3a1a];
const OAK_SHIRTS = [0x2a3a5a, 0x1a3a28, 0x3a2a1a, 0x2a1a3a, 0x1e3a2a, 0x3a2a2a];
const PIT_VESTS = [0xff2222, 0x2244ff, 0xffcc00, 0x22aa44, 0xff6600, 0xaa22ff, 0x22aaff, 0xff22aa, 0x88ff22, 0xffaa22, 0xff4488, 0x44aaff, 0x88aa22];
const BLOOM_SYMBOLS = ['AAPL', 'MSFT', 'VOO', 'BRK.B', 'SPY', 'AMZN', 'JNJ'];
const OAK_SYMBOLS = ['TECH', 'UTIL', 'HLTH', 'ENRG', 'FINL', 'XLF', 'ROTATE'];
const PIT_SYMBOLS = ['TSLA', 'NVDA', 'AMD', 'GME', 'SPY', 'QQQ', 'AAPL'];
const PIT_CHAOS = [
  { s: '▲', c: 0x00ff00 }, { s: '▼', c: 0xff3333 }, { s: '!!', c: 0xff3333 },
  { s: '$', c: 0x00ff00 }, { s: 'BUY', c: 0x00ff00 }, { s: '⚡', c: 0xff3333 },
  { s: 'SELL', c: 0xff3333 }, { s: '%%%', c: 0xff8c00 },
];

function buildBloomberg(app) {
  const { desks, bounds, spawnPoints } = drawBloomberg(app);
  return spawnPoints.map(([x, y], i) => {
    const ag = new WalkingAgent(
      app, x, y,
      BLOOMBERG_SHIRTS[i % BLOOMBERG_SHIRTS.length],
      0xdfc090, 0x1a3a3a, null,
      bounds, desks
    );
    ag.spd = 0.38 + Math.random() * 0.08;
    return ag;
  });
}

function buildOak(app) {
  const { seatPositions } = drawOak(app);
  return seatPositions.map(([x, y], i) =>
    new SeatedAgent(app, x, y, OAK_SHIRTS[i % OAK_SHIRTS.length], 0xd4b896, 0xcc8833, null, 6)
  );
}

function buildPit(app) {
  const { seatPositions, screenRects, timerText } = drawPit(app);
  const agents = seatPositions.map(([x, y], i) =>
    new SeatedAgent(app, x, y, 0x120404, 0xe0a070, 0xff3333, PIT_VESTS[i % PIT_VESTS.length], 5)
  );
  return { agents, screenRects, timerText };
}

const ROOM_BG = {
  long_term: 0xe8f0f8,
  swing_trading: 0x36454f,
  day_trading: 0x080404,
};

const ROOM_ACCENT = {
  long_term: '#4a7eba',
  swing_trading: '#CC8833',
  day_trading: '#FF3333',
};

export default function PixiWarroom({ room }) {
  const canvasRef = useRef(null);
  const appRef = useRef(null);
  const agentSpritesRef = useRef([]);
  const chaosRef = useRef([]);
  const symTimerRef = useRef(0);
  const ftRef = useRef(0);

  useWarroomAgents(room, agentSpritesRef.current);

  useEffect(() => {
    const app = new PIXI.Application({
      view: canvasRef.current,
      width: ROOM_W,
      height: ROOM_H,
      backgroundColor: ROOM_BG[room] ?? 0x0a0a0f,
      antialias: false,
      resolution: 1,
    });
    app.ticker.maxFPS = 30;
    appRef.current = app;

    let pitScreenRects = [];
    let pitTimerText = null;

    if (room === 'long_term') {
      agentSpritesRef.current = buildBloomberg(app);
      app.ticker.add(() => {
        agentSpritesRef.current.forEach(a => a.tick(BLOOM_SYMBOLS, 0, 0.08));
      });
    } else if (room === 'swing_trading') {
      agentSpritesRef.current = buildOak(app);
      app.ticker.add(() => {
        agentSpritesRef.current.forEach(a => a.tick(OAK_SYMBOLS, 6, 0.09));
      });
    } else if (room === 'day_trading') {
      const { agents, screenRects, timerText } = buildPit(app);
      agentSpritesRef.current = agents;
      pitScreenRects = screenRects;
      pitTimerText = timerText;

      const flickerG = new PIXI.Graphics();
      app.stage.addChild(flickerG);

      app.ticker.add(() => {
        agentSpritesRef.current.forEach(a => a.tick(PIT_SYMBOLS, 5, 0.18));

        symTimerRef.current++;
        if (symTimerRef.current % 15 === 0 && agentSpritesRef.current.length > 0) {
          const ag = agentSpritesRef.current[Math.floor(Math.random() * agentSpritesRef.current.length)];
          const sym = PIT_CHAOS[Math.floor(Math.random() * PIT_CHAOS.length)];
          chaosRef.current.push({ sym: new ChaosSymbol(app, ag.x + 7, ag.y + 8, sym.s, sym.c), ag });
        }
        chaosRef.current = chaosRef.current.filter(({ sym, ag }) => {
          const alive = sym.tick(ag.x + 7, ag.y + 8);
          if (!alive) sym.destroy(app);
          return alive;
        });

        ftRef.current++;
        flickerG.clear();
        if (ftRef.current % 40 < 2 && pitScreenRects.length > 0) {
          const s = pitScreenRects[Math.floor(Math.random() * pitScreenRects.length)];
          flickerG.beginFill(s.color, 0.1);
          flickerG.drawRect(s.x, s.y, s.w, s.h);
        }
        if (pitTimerText && ftRef.current % 60 === 0) {
          const mn = 24 + Math.floor(ftRef.current / 60) % 30;
          const sc = ftRef.current % 60;
          pitTimerText.text = `09:${String(mn).padStart(2, '0')}:${String(sc).padStart(2, '0')}`;
        }
      });
    }

    return () => {
      agentSpritesRef.current.forEach(a => a.destroy());
      agentSpritesRef.current = [];
      chaosRef.current.forEach(({ sym }) => sym.destroy(app));
      chaosRef.current = [];
      app.destroy(false, { children: true, texture: true });
      appRef.current = null;
    };
  }, [room]);

  const accent = ROOM_ACCENT[room] ?? 'var(--color-border)';

  return (
    <div style={{
      position: 'relative',
      border: `2px solid ${accent}`,
      overflow: 'hidden',
      width: '100%',
      maxWidth: ROOM_W,
      margin: '0 auto',
    }}>
      <canvas
        ref={canvasRef}
        style={{
          display: 'block',
          width: '100%',
          height: 'auto',
          imageRendering: 'pixelated',
        }}
      />
      <div style={{
        position: 'absolute',
        inset: 0,
        background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.08) 2px, rgba(0,0,0,0.08) 4px)',
        pointerEvents: 'none',
      }} />
    </div>
  );
}
