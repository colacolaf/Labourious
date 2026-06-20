# Phase 4 Design Specifications — Extracted from LABOURIOUS_FRONTEND.md

## Animation Specifications

| Animation | Trigger | Variants | Duration | Easing | Notes |
|---|---|---|---|---|---|
| Agent Idle | Always (when not active) | `y: [0, -8, 0]` | 3s | easeInOut | Loop infinitely |
| Agent Active | While agent running check | `opacity: [1,0.6,1], scale: [1,1.08,1]` | 2s | easeInOut | Loop infinitely, pulse |
| Trade Notification | Trade executed | `opacity+scale pop` | 0.2s in / 2.5s hold / 0.5s out | easeOut / easeIn | Green ✅ or Red ❌ above agent |
| Approval Dialog | Decision needed | `y: -50→0` | 0.3s | spring(stiffness:300, damping:20) | Auto-dismiss 30s |
| Inspector Panel | Click agent | `x: 400→0, opacity: 0→1` | 0.3s | easeOut | Slide from right |
| Room Transition (exit) | Click scorecard | `scale: 1→0.8, opacity: 1→0` | 0.5s | easeInOut | Camera zoom out |
| Tab Switch | Click inspector tab | `opacity` only | 0.2s | easeOut | No slide |
| Modal Backdrop | Any modal | `opacity: 0→0.5` | 0.2s | easeOut | — |
| Toast | Any notification | `x: 400→0, opacity: 0→1` | 0.3s in / 4s hold / 0.3s out | easeOut | Top-right corner |
| Button Press | User click | `scale: 1.05 hover, 0.95 tap` | fast | — | Retro feel |
| Paused Handcuffs | Agent paused | `opacity+scale: 0→1` | 0.3s | — | Above agent head |

### Framer Motion variant objects (copy-paste ready)

```js
// Agent idle
const idleVariants = {
  animate: { y: [0, -8, 0], transition: { duration: 3, repeat: Infinity, ease: 'easeInOut' } }
};

// Agent active (thinking)
const activeVariants = {
  pulse: { opacity: [1, 0.6, 1], scale: [1, 1.08, 1], transition: { duration: 2, repeat: Infinity, ease: 'easeInOut' } }
};

// Trade notification
const tradeNotificationVariants = {
  initial: { opacity: 0, scale: 0.3, y: -20 },
  animate: { opacity: 1, scale: 1, y: 0, transition: { duration: 0.2, ease: 'easeOut' } },
  exit: { opacity: 0, scale: 0.8, y: -30, transition: { duration: 0.5, ease: 'easeIn' } }
};

// Approval dialog
const approvalDialogVariants = {
  initial: { opacity: 0, y: -50 },
  animate: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 300, damping: 20, duration: 0.3 } },
  exit: { opacity: 0, y: -50, transition: { duration: 0.2 } }
};

// Inspector panel
const inspectorVariants = {
  initial: { x: 400, opacity: 0 },
  animate: { x: 0, opacity: 1, transition: { duration: 0.3, ease: 'easeOut' } },
  exit: { x: 400, opacity: 0, transition: { duration: 0.2 } }
};

// Room transition (lobby exit)
const roomTransitionVariants = {
  initial: { scale: 1, opacity: 1 },
  exit: { scale: 0.8, opacity: 0, transition: { duration: 0.5, ease: 'easeInOut' } }
};

// Toast
const toastVariants = {
  initial: { x: 400, opacity: 0 },
  animate: { x: 0, opacity: 1, transition: { duration: 0.3, ease: 'easeOut' } },
  exit: { x: 400, opacity: 0, transition: { duration: 0.3 } }
};
```

---

## CSS Variables (verified against `frontend/src/styles/index.css`)

### Backgrounds
| Var | Value | Use |
|---|---|---|
| `--color-bg-primary` | `#0a0a0f` | Main background |
| `--color-bg-secondary` | `#0f0f1a` | Sidebar, panels |
| `--color-bg-tertiary` | `#141428` | Deep elements |
| `--color-bg-card` | `#12121e` | Cards |
| `--color-bg-elevated` | `#1a1a2e` | Elevated surfaces, tooltips |

### Borders
| Var | Value |
|---|---|
| `--color-border` | `#1e1e3a` |
| `--color-border-subtle` | `#16162a` |
| `--color-border-bright` | `#2a2a50` |

### Accents
| Var | Value | Use |
|---|---|---|
| `--color-accent-primary` | `#00ff88` | Active agents, positive P&L, CTA buttons |
| `--color-accent-secondary` | `#00d4ff` | Cyan highlights, charts |
| `--color-accent-tertiary` | `#7c3aed` | Purple accent |
| `--color-accent-warning` | `#ffb020` | Warnings, paused agents, amber flags |
| `--color-accent-danger` | `#ff4444` | Errors, negative P&L, stop |
| `--color-accent-success` | `#00ff88` | Same as primary |

### Text
| Var | Value | Use |
|---|---|---|
| `--color-text-primary` | `#e8e8f0` | Body text (NOT hacker-green) |
| `--color-text-secondary` | `#9090b0` | Secondary labels |
| `--color-text-muted` | `#606080` | Hints, captions |
| `--color-text-accent` | `#00ff88` | Highlighted text |
| `--color-text-warning` | `#ffb020` | Warning text |
| `--color-text-danger` | `#ff4444` | Error text |

### Agent Status Colors
| Var | Value |
|---|---|
| `--color-agent-running` | `#00ff88` |
| `--color-agent-idle` | `#9090b0` |
| `--color-agent-paused` | `#ffb020` |
| `--color-agent-error` | `#ff4444` |
| `--color-agent-stopped` | `#606080` |

### P&L Colors
| Var | Value |
|---|---|
| `--color-pnl-positive` | `#00ff88` |
| `--color-pnl-negative` | `#ff4444` |
| `--color-pnl-neutral` | `#9090b0` |

### Typography
| Var | Value |
|---|---|
| `--font-mono` | `'JetBrains Mono', 'Fira Code', 'Courier New', monospace` |
| `--font-sans` | `'Space Grotesk', 'Inter', system-ui, sans-serif` |
| `--font-size-xs` | `0.625rem` |
| `--font-size-sm` | `0.75rem` |
| `--font-size-base` | `0.875rem` |
| `--font-size-md` | `1rem` |
| `--font-size-lg` | `1.125rem` |
| `--font-size-xl` | `1.25rem` |
| `--font-size-2xl` | `1.5rem` |
| `--font-size-3xl` | `2rem` |

### Spacing
`--space-1` (0.25rem) → `--space-2` (0.5rem) → `--space-3` (0.75rem) → `--space-4` (1rem) → `--space-6` (1.5rem) → `--space-8` (2rem) → `--space-12` (3rem) → `--space-16` (4rem)

### Radii
`--radius-sm` (4px) · `--radius-md` (8px) · `--radius-lg` (12px) · `--radius-xl` (16px)

### Shadows
| Var | Value |
|---|---|
| `--shadow-glow-green` | `0 0 20px rgba(0,255,136,0.15)` |
| `--shadow-glow-cyan` | `0 0 20px rgba(0,212,255,0.15)` |
| `--shadow-card` | `0 4px 24px rgba(0,0,0,0.4)` |
| `--shadow-elevated` | `0 8px 40px rgba(0,0,0,0.6)` |

### Transitions
`--transition-fast` (120ms ease) · `--transition-base` (200ms ease) · `--transition-slow` (350ms ease)

### Layout
`--sidebar-width: 240px` · `--topbar-height: 56px`

---

## Component Tree

```
App.jsx (Root)
├── Router
├── GlobalHeader.jsx
├── GlobalNotifications.jsx (Toast system)
├── MainContent.jsx
│   ├── LobbyPage.jsx
│   │   ├── RiskAgent.jsx (left)
│   │   ├── RoomScorecard.jsx (×4)
│   │   ├── BodyguardAgent.jsx (right)
│   │   └── PortfolioQuickStats.jsx (bottom)
│   │
│   ├── RoomView.jsx (day / swing / long_term)
│   │   ├── Warroom.jsx (SVG canvas)
│   │   │   ├── IsometricGrid.jsx
│   │   │   ├── AgentSprite.jsx (×N)
│   │   │   ├── TradeNotification.jsx (conditional)
│   │   │   └── ApprovalDialog.jsx (conditional)
│   │   └── AgentInspector.jsx (slide-out)
│   │       ├── OverviewTab.jsx
│   │       ├── TradesTab.jsx
│   │       ├── RulesTab.jsx
│   │       ├── PerformanceTab.jsx
│   │       └── SettingsTab.jsx
│   │
│   └── ControlRoom.jsx
│       ├── BrokerSection.jsx
│       ├── LLMSection.jsx
│       ├── AllocationSection.jsx
│       ├── AgentManagementSection.jsx
│       ├── RiskSection.jsx
│       └── VaultSection.jsx
│
└── GlobalFooter.jsx
```

**Shared/Common components:** `Header`, `Footer`, `Button`, `Input`, `Select`, `Slider`, `Modal`, `Toast`, `Spinner`, `StatusBadge`

---

## Lobby Layout (Variant A — FROZEN)

```
┌─────────────────────────────────────────────────────────────┐
│              LABOURIOUS TRADING COMMAND CENTER              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Risk Agent SVG]        Title         [Bodyguard SVG]     │
│  Status: Monitoring                    Status: Ready       │
│  (click → Risk Analysis modal)         (click → Pause      │
│                                               History modal)│
│  ┌─────────────────────────────────────────────────────┐   │
│  │              SELECT A TRADING ROOM                  │   │
│  │                                                     │   │
│  │  ┌─────────────────┐   ┌─────────────────┐         │   │
│  │  │ 📊 DAY TRADING  │   │ 📊 SWING TRADING│         │   │
│  │  │ Agents:     3   │   │ Agents:     2   │         │   │
│  │  │ P&L:  +$5,240   │   │ P&L:  +$8,100  │         │   │
│  │  │ Win Rate:  65%  │   │ Win Rate:  58%  │         │   │
│  │  │ Alloc:     10%  │   │ Alloc:     30%  │         │   │
│  │  │ Status:    ✅   │   │ Status:    ✅   │         │   │
│  │  └─────────────────┘   └─────────────────┘         │   │
│  │                                                     │   │
│  │  ┌─────────────────┐   ┌─────────────────┐         │   │
│  │  │ 📊 LONG-TERM    │   │ ⚙️  CONTROL ROOM │         │   │
│  │  │ Agents:     2   │   │ Brokers:    2   │         │   │
│  │  │ P&L: +$10,500   │   │ LLM:   Ollama  │         │   │
│  │  │ Win Rate:  75%  │   │ Settings: Ready │         │   │
│  │  │ Alloc:     60%  │   │ Status:    ✅   │         │   │
│  │  │ Status:    ✅   │   │                 │         │   │
│  │  └─────────────────┘   └─────────────────┘         │   │
│  │                                                     │   │
│  │  Portfolio: +$23,840 (+12.3%) | Last trade: 15m ago │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**RoomScorecard interactions:**
- Hover: `scale: 1.02`, border → `--color-accent-primary`
- Click: Room transition animation (0.5s easeInOut), navigate to room

---

## Control Room Layout (6 Sections, Tabbed)

```
┌─────────────────────────────────────────────────────────────┐
│ [Broker] [LLM] [Allocation] [Agents] [Risk] [Vault]        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Active section content (~600px wide, scrollable)          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

| Tab | Key fields |
|---|---|
| Broker Connections | List exchanges, test connection, add/remove |
| LLM Configuration | Ollama/Claude toggle, model selector, cost estimate, test |
| Capital Allocation | Day/Swing/LongTerm sliders (sum=100%), pie chart |
| Agent Management | Agent table, enable/disable toggles, delete |
| Risk Settings | Max drawdown %, stop-loss %, auto-pause triggers, emergency stop |
| Vault & Security | Change password, export backup, import backup, user mgmt (admin) |

---

## Warroom Layout

```
┌─────────────────────────────────────────────┐
│ [◀ Lobby]  Day Trading Room        [Search] │
├─────────────────────────────────────────────┤
│                                             │
│   [Isometric SVG grid]                      │
│                                             │
│   Agent● ──→ ✅ +$1,240  (trade notif)      │
│   Agent● ──→ ⚠️ [Approve/Reject] (30s)      │
│   Agent● ──→ 🔒 Paused (losing streak)      │
│                                             │
└─────────────────────────────────────────────┘
│ Inspector Panel (slides in from right)      │
│ [Overview] [Trades] [Rules] [Perf] [Sett]  │
└─────────────────────────────────────────────┘
```

---

## Isometric Grid Math

```js
const TILE_WIDTH = 60;   // SVG units
const TILE_HEIGHT = 30;  // 2:1 ratio
const OFFSET_X = 100;
const OFFSET_Y = 100;

// Grid coords → SVG screen coords
function gridToScreen(row, col) {
  return {
    x: OFFSET_X + (col - row) * (TILE_WIDTH / 2),
    y: OFFSET_Y + (col + row) * (TILE_HEIGHT / 2),
  };
}

// Grid line color: rgba(74, 158, 222, 0.2)  (muted cyan)
```

---

## Agent Color Logic

```js
function getAgentColor(agent) {
  if (agent.status === 'paused') return 'var(--color-agent-paused)';   // #ffb020
  if (agent.confidence_score < 50) return 'var(--color-agent-error)'; // #ff4444
  if (agent.total_pnl < 0) return 'var(--color-pnl-negative)';        // #ff4444
  return 'var(--color-agent-running)';                                  // #00ff88
}
```

---

## ⚠️ Discrepancies: FRONTEND.md vs index.css

| FRONTEND.md says | index.css actual | Use |
|---|---|---|
| `--bg-primary: #1a1a1a` | `--color-bg-primary: #0a0a0f` | Use `--color-bg-*` (actual) |
| `--color-primary: #2d5a5a` | Does not exist | Use `--color-accent-primary` |
| `--color-secondary: #4a9ede` | Does not exist | Use `--color-accent-secondary` |
| `--status-success: #4CAF50` | `--color-accent-success: #00ff88` | Use `--color-accent-success` |
| `--text-primary: #e8e8e8` | `--color-text-primary: #e8e8f0` | Use `--color-text-primary` |

**Rule: Always use the vars from `index.css`. Never reference FRONTEND.md var names directly.**
