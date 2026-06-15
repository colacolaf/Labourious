LABOURIOUS FRONTEND ARCHITECTURE & DESIGN
Complete frontend specification for the Labourious AI trading warroom.
Version: 1.0 MVP

Status: Ready for Implementation

Last Updated: June 2026

TABLE OF CONTENTS

Design Vision
Tech Stack
Lobby Architecture
Warroom Architecture
Component Specifications
SVG Isometric Rendering
Animation System
Color Palette & Styling
State Management (Zustand)
WebSocket Integration
File Structure
Development Roadmap


DESIGN VISION
The Lobby: Command Center Lounge
Users start in a command center lounge where they can see the two meta-agents (Risk Manager & Bodyguard) and choose which trading room to enter via interactive scorecards.
Visual Style:

Retro lounge aesthetic (1980s-90s office with vintage character)
Clean, professional, suitable for managing real money
Lounge furniture/decorations (no silly stuff, subtle vintage touches)
Risk Agent stands on left side, Bodyguard on right
4 room scorecards in center, displayed as clickable cards

Navigation Flow:
Lobby (Hub)
├─ [Risk Agent] [Scorecard Day] [Scorecard Swing] [Bodyguard]
│  [Scorecard Long-Term] [Scorecard Control]
│
├─ User clicks scorecard → Camera pans/zooms smoothly
├─ User enters selected room (warroom or control room)
├─ Sticky "◀ Return to Lobby" button in top-left
└─ Click to exit room and return to lobby
The Warroom: Retro Football Stadium Floor
Each trading room (Day Trading, Swing Trading, Long-Term) is a 2D isometric view of a trading floor, inspired by a retro football stadium viewed from above.
Visual Style:

Birds-eye isometric perspective (not true 3D, clean 2D)
Grid floor with subtle retro coloring
Agents positioned as sprites on the floor
Clean, minimal UI (slide-out inspector panel)
Real-time animations above agents' heads (notifications, P&L, status)


TECH STACK
json{
  "framework": {
    "electron": "^27.0.0 (desktop app)",
    "react": "^18.2.0",
    "react-router-dom": "^6.20.0 (navigation between rooms)",
    "zustand": "^4.4.0 (state management)",
    "zustand_devtools": "middleware for debugging"
  },
  "rendering": {
    "svg": "native SVG for isometric grid and agents",
    "framer-motion": "^10.16.0 (animations)",
    "react-icons": "^4.12.0 (icons)"
  },
  "styling": {
    "tailwindcss": "^3.3.0 (utility CSS)",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0"
  },
  "charting": {
    "recharts": "^2.10.0 (performance charts)"
  },
  "websocket": {
    "socket.io-client": "^4.7.0 (real-time updates)"
  },
  "utilities": {
    "axios": "^1.6.0 (HTTP client)",
    "date-fns": "^2.30.0 (date formatting)",
    "clsx": "^2.0.0 (conditional classNames)"
  },
  "dev": {
    "typescript": "^5.3.0 (type safety)",
    "vite": "^5.0.0 (build tool)",
    "eslint": "^8.54.0",
    "prettier": "^3.1.0"
  }
}

LOBBY ARCHITECTURE
Lobby Layout (Command Center Lounge)
┌─────────────────────────────────────────────────────────────┐
│                  LABOURIOUS TRADING COMMAND CENTER          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🤵 Risk Agent              [Portrait/Status]  🛡️ Bodyguard │
│  Manager                                      Security     │
│  [Standing L]                                [Standing R]  │
│  Status: Monitoring                          Status: Ready │
│  Last Alert: None                            Last Action: Idle
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │         SELECT A TRADING ROOM                         │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │                                                       │ │
│  │  ┌──────────────────┐  ┌──────────────────┐         │ │
│  │  │ 📊 DAY TRADING   │  │ 📊 SWING TRADING │         │ │
│  │  ├──────────────────┤  ├──────────────────┤         │ │
│  │  │ Agents:      3   │  │ Agents:      2   │         │ │
│  │  │ P&L:   +$5,240   │  │ P&L:   +$8,100   │         │ │
│  │  │ Win Rate:   65%  │  │ Win Rate:   58%  │         │ │
│  │  │ Allocation: 10%  │  │ Allocation: 30%  │         │ │
│  │  │ Status:     ✅   │  │ Status:     ✅   │         │ │
│  │  └──────────────────┘  └──────────────────┘         │ │
│  │                                                       │ │
│  │  ┌──────────────────┐  ┌──────────────────┐         │ │
│  │  │ 📊 LONG-TERM     │  │ ⚙️ CONTROL ROOM  │         │ │
│  │  ├──────────────────┤  ├──────────────────┤         │ │
│  │  │ Agents:      2   │  │ Brokers:     2   │         │ │
│  │  │ P&L:  +$10,500   │  │ LLM:    Ollama   │         │ │
│  │  │ Win Rate:   75%  │  │ Settings:  Ready │         │ │
│  │  │ Allocation: 60%  │  │ Status:     ✅   │         │ │
│  │  │ Status:     ✅   │  │                  │         │ │
│  │  └──────────────────┘  └──────────────────┘         │ │
│  │                                                       │ │
│  │  Portfolio Total: +$23,840 (+12.3%)                 │ │
│  │  Last Trade: 15 minutes ago (News Agent)            │ │
│  │                                                       │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
Lobby Components
LobbyPage.jsx
javascript// Main entry point - command center lounge
// Shows:
// - Risk Agent (left side, interactive)
// - 4 room scorecards (center, clickable)
// - Bodyguard Agent (right side, interactive)
// - Quick portfolio stats (bottom)
// - Click scorecard → camera pan to warroom
RiskAgent.jsx
javascript// Manager figure in suit, left side
// Appearance:
// - Business suit silhouette
// - Clipboard/chart in hand
// - Professional pose (analytical)
// 
// Interactive on click:
// - Shows modal: "Risk Analysis Report"
// - Lists recent alerts
// - Shows confidence scores
// - Recommends actions (pause agents, adjust allocation)
// 
// Reactive animations:
// - When alert triggered: Brief pause, then thumbs-down gesture
// - Shows tooltip: "⚠️ Losing streak detected"
// - Auto-dismisses after 5 seconds
BodyguardAgent.jsx
javascript// Security/protector figure, right side
// Appearance:
// - Broad shoulders, vigilant pose
// - Shield symbol or armor-like
// - Professional security look (no comedy)
// 
// Interactive on click:
// - Shows modal: "Pause History"
// - Lists agents paused today
// - Shows reasons for pauses
// - Shows auto-resume candidates
// 
// Reactive animations:
// - When pause action: Brief hand-raise gesture
// - Shows tooltip: "🛡️ Tech Trader paused"
// - Indicates protection action
RoomScorecard.jsx (x4 instances)
javascript// Clickable scorecard for each room
// Props: room (day|swing|long_term|control)
//
// Display:
// - Room emoji + name
// - Number of active agents
// - Room P&L (color-coded green/red)
// - Win rate
// - Capital allocation %
// - Status indicator (✅ or ⚠️)
// - Quick confidence average
//
// Interaction:
// - Hover: Slight scale increase, highlight border
// - Click: Trigger camera pan animation
// - Pan lasts 0.5s, room fades in
PortfolioQuickStats.jsx
javascript// Bottom of lobby - quick glance portfolio data
// Display:
// - Total portfolio P&L (large, prominent)
// - Allocation breakdown (3 bars: Day/Swing/Long-Term)
// - Last trade info (agent name, symbol, time)
// - Next agent check time

WARROOM ARCHITECTURE
Warroom Layout (Retro Football Stadium View)
┌─────────────────────────────────────────────────────┐
│ [◀ Return to Lobby] Day Trading Room      [Search] │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │                                             │   │
│  │     [GRID - Isometric View]                 │   │
│  │                                             │   │
│  │     Agent1 ●                                │   │
│  │             ↓ ✅ +$1,240                    │   │
│  │                                             │   │
│  │                  Agent2 ●                   │   │
│  │                          ↓ ⚠️ -$340 (sl)    │   │
│  │                                             │   │
│  │     Agent3 ●                                │   │
│  │             [Waiting for approval]          │   │
│  │             [Approve] [Reject]              │   │
│  │                                             │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │ Inspector Panel (Slide Out)                 │   │
│  │                                             │   │
│  │ Agent: News Trader           [X]            │   │
│  │ P&L: +$1,240 (+6.2%)                        │   │
│  │ Status: Active, 3 winning streak            │   │
│  │                                             │   │
│  │ [Overview] [Trades] [Rules] [Perf] [Set]   │   │
│  │                                             │   │
│  │ Content of selected tab...                  │   │
│  │                                             │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘
Warroom Components
Warroom.jsx (Main Container)
javascript// SVG canvas rendering isometric grid
// Shows:
// - Isometric grid background (lines, subtle color)
// - Agent sprites positioned on grid
// - Real-time P&L/status above each agent
// - Approval dialogs for human-in-loop trades
// - Click agent → open inspector panel
//
// Props: room (day|swing|long_term)
// Subscribes to WebSocket for agent updates
IsometricGrid.jsx
javascript// SVG component rendering the isometric grid
// - Draws floor tiles in isometric perspective
// - Subtle grid lines (retro style)
// - Color scheme matches room theme
// - Faint coordinate labels (optional for debugging)
// - Interactive: Can zoom/pan (optional, basic implementation)
AgentSprite.jsx
javascript// SVG agent visual (single agent on grid)
// Props: agent object (id, status, p_and_l, active_trade, etc)
//
// Renders:
// - Agent avatar (colored circle + initials or icon)
// - Status indicator (idle, active, paused, etc)
// - Idle animation: Gentle vertical sway (±8px, 3s cycle)
// - Active animation: Pulse or typing effect (when running check)
//
// Interactions:
// - Hover: Slight glow, show tooltip (agent name, status)
// - Click: Trigger inspector panel open
//
// Notifications above head:
// - Trade executed: Green ✅ + number (+$1,240)
// - Trade failed: Red ❌ + number (-$340)
// - Waiting approval: Yellow ⚠️ + timer (30s countdown)
// - Paused: Padlock 🔒 + reason ("Losing streak")
// - Confidence: Brief % display (72%)
AgentInspector.jsx (Slide-out Panel)
javascript// Right-side slide-out panel showing agent details
// Props: agent object, isOpen (boolean), onClose (function)
//
// Features:
// - Smooth slide-in animation (0.3s from right)
// - Can be closed by X button or clicking warroom
// - Tab system (5 tabs below)
// - Each tab shows relevant data
//
// Tabs:
// 1. Overview: P&L, status, active positions, confidence score
// 2. Trades: Recent 10 trades in table, clickable for details
// 3. Rules: Display context file (read-only, scrollable)
// 4. Performance: Charts (equity, Sharpe, drawdown) + metrics
// 5. Settings: Enable/disable, execution mode, position size, freq
OverviewTab.jsx
javascript// Contents of inspector "Overview" tab
// Displays:
// - Agent name + status (bold, color-coded)
// - Current P&L (large, green/red)
// - Win rate (%)
// - Active positions (number + list)
// - Last trade (symbol, entry price, entry time)
// - Confidence score (progress bar 0-100%)
// - Last check time
// - Next check time (countdown)
TradesTab.jsx
javascript// Contents of inspector "Trades" tab
// Displays:
// - Table of recent 10 trades
// - Columns: Date, Symbol, Side, Quantity, Entry, Exit, P&L, %
// - Click row to expand full trade details
// - "Load more" button for trade history
// - Filter options (by symbol, by status, by date range)
RulesTab.jsx
javascript// Contents of inspector "Rules" tab
// Displays:
// - Agent's context file (read-only)
// - Syntax highlighting for conditions
// - Scrollable text area
// - "Upload new context" button (opens file dialog)
// - Validation feedback (if context updated)
PerformanceTab.jsx
javascript// Contents of inspector "Performance" tab
// Displays:
// - Equity curve chart (Recharts, last 30 days)
// - Sharpe ratio (number + gauge)
// - Max drawdown (number + bar)
// - Win/loss counts and percentages
// - Consecutive wins/losses
// - Best/worst trade
// - Average winner/loser
SettingsTab.jsx
javascript// Contents of inspector "Settings" tab
// Displays:
// - Enable/disable toggle
// - Execution mode selector (autonomous, human-in-loop, risk-based)
// - Position size slider (%)
// - Check frequency selector (every 5min, 30min, hourly, daily, weekly)
// - Broker selector (if multi-broker)
// - Capital allocation (read-only, controlled in Control Room)
ApprovalDialog.jsx
javascript// Modal dialog for human-in-loop trade approval
// Appears above warroom when agent needs approval
//
// Contents:
// - Agent name + icon
// - Trade details (symbol, side, quantity, entry price)
// - Confidence score (%)
// - Reasoning (from LLM analysis)
// - [✅ APPROVE] [❌ REJECT] buttons
// - Timer showing seconds remaining (30s default)
// - Auto-rejects if no response in 30s
//
// Animation:
// - Slide in from top (0.3s, bounce ease)
// - Position: Center-top of screen
// - If approved: Brief ✅ animation, notification
// - If rejected: Brief ❌ animation, dismisses
TradeNotification.jsx
javascript// Small notification popup appearing above agent
// Triggered when trade executes
//
// Contents:
// - Trade result (✅ or ❌)
// - P&L amount (color-coded green/red)
// - Percentage (%)
//
// Animation:
// - Pops up above agent (0.2s scale from small to normal)
// - Fades out after 2.5s (0.5s fade)
// - Bounces slightly for emphasis
ControlRoom.jsx
javascript// Settings/admin area (separate view from warrooms)
// Accessed via "Control Room" scorecard in lobby
//
// Sections:
// 1. Broker Connections
//    - List connected brokers
//    - Test connection button
//    - Add new broker button
//    - Remove broker confirmation
//
// 2. LLM Configuration
//    - Toggle local vs cloud LLM
//    - Select local model (Ollama model selector)
//    - Cloud API key input
//    - Test LLM button
//    - Cost estimate (if cloud)
//
// 3. Capital Allocation
//    - Sliders for Day/Swing/Long-Term allocation
//    - Total must = 100%
//    - Shows impact (rebalancing confirmation)
//    - Apply button
//
// 4. Agent Management (Basic)
//    - List all agents
//    - Enable/disable toggles
//    - Delete agent confirmation
//    - (Detailed settings in warroom inspector)
//
// 5. Risk Settings
//    - Max portfolio drawdown (%)
//    - Auto-pause triggers
//    - Emergency stop button
//
// 6. Vault & Security
//    - Change vault password
//    - Export encrypted backup
//    - Import from backup

COMPONENT SPECIFICATIONS
Component Tree
App.jsx (Root)
├─ Router
├─ GlobalHeader.jsx
├─ GlobalNotifications.jsx (Toast system)
├─ MainContent.jsx
│  ├─ LobbyPage.jsx
│  │  ├─ RiskAgent.jsx
│  │  ├─ RoomScorecard.jsx (x4)
│  │  ├─ BodyguardAgent.jsx
│  │  └─ PortfolioQuickStats.jsx
│  │
│  ├─ RoomView.jsx (for each room: day, swing, long_term)
│  │  ├─ Warroom.jsx
│  │  │  ├─ IsometricGrid.jsx
│  │  │  ├─ AgentSprite.jsx (x N agents)
│  │  │  ├─ TradeNotification.jsx (conditional)
│  │  │  └─ ApprovalDialog.jsx (conditional)
│  │  │
│  │  └─ AgentInspector.jsx (slide-out)
│  │     ├─ OverviewTab.jsx
│  │     ├─ TradesTab.jsx
│  │     ├─ RulesTab.jsx
│  │     ├─ PerformanceTab.jsx
│  │     └─ SettingsTab.jsx
│  │
│  └─ ControlRoom.jsx
│     ├─ BrokerSection.jsx
│     ├─ LLMSection.jsx
│     ├─ AllocationSection.jsx
│     ├─ AgentManagementSection.jsx
│     ├─ RiskSection.jsx
│     └─ VaultSection.jsx
│
└─ GlobalFooter.jsx
Shared/Utility Components
Common/
├─ Header.jsx (top bar with breadcrumbs, logo)
├─ Footer.jsx (connection status, LLM status, broker status)
├─ Button.jsx (retro-styled button, reusable)
├─ Input.jsx (text input with retro styling)
├─ Select.jsx (dropdown with retro styling)
├─ Slider.jsx (range slider, custom styled)
├─ Modal.jsx (modal dialog wrapper)
├─ Toast.jsx (notification toast)
├─ Spinner.jsx (loading indicator)
└─ StatusBadge.jsx (status indicator)

SVG ISOMETRIC RENDERING
Isometric Coordinate System
2D Isometric Projection Math:
javascript// Convert from grid coordinates (row, col) to SVG screen coordinates (x, y)
// Using standard isometric projection

const TILE_WIDTH = 60;   // SVG units (pixels)
const TILE_HEIGHT = 30;  // SVG units (isometric ratio 2:1)
const OFFSET_X = 100;    // Initial X offset
const OFFSET_Y = 100;    // Initial Y offset

function gridToScreen(row, col) {
  const x = OFFSET_X + (col - row) * (TILE_WIDTH / 2);
  const y = OFFSET_Y + (col + row) * (TILE_HEIGHT / 2);
  return { x, y };
}

function screenToGrid(x, y) {
  const adjX = x - OFFSET_X;
  const adjY = y - OFFSET_Y;
  
  const col = (adjX / (TILE_WIDTH / 2) + adjY / TILE_HEIGHT) / 2;
  const row = (adjY / TILE_HEIGHT - adjX / (TILE_WIDTH / 2)) / 2;
  
  return { row: Math.round(row), col: Math.round(col) };
}
IsometricGrid.jsx Implementation
javascriptimport React, { useMemo } from 'react';

const IsometricGrid = ({ width = 1200, height = 800, rows = 10, cols = 10 }) => {
  const TILE_WIDTH = 60;
  const TILE_HEIGHT = 30;
  const OFFSET_X = 100;
  const OFFSET_Y = 100;

  const gridLines = useMemo(() => {
    const lines = [];
    
    // Horizontal iso lines (↘)
    for (let i = 0; i <= rows; i++) {
      const x1 = OFFSET_X - (cols * TILE_WIDTH) / 2;
      const y1 = OFFSET_Y + i * TILE_HEIGHT;
      const x2 = OFFSET_X + (cols * TILE_WIDTH) / 2;
      const y2 = y1;
      
      lines.push({
        x1, y1, x2, y2,
        key: `h-${i}`,
        stroke: 'rgba(74, 158, 222, 0.2)' // Muted cyan
      });
    }
    
    // Vertical iso lines (↙)
    for (let j = 0; j <= cols; j++) {
      const startY = OFFSET_Y;
      const endY = OFFSET_Y + rows * TILE_HEIGHT;
      const startX = OFFSET_X + (j - rows / 2) * TILE_WIDTH / 2;
      const endX = OFFSET_X + (j + rows / 2 - rows) * TILE_WIDTH / 2;
      
      lines.push({
        x1: startX,
        y1: startY,
        x2: endX,
        y2: endY,
        key: `v-${j}`,
        stroke: 'rgba(74, 158, 222, 0.2)'
      });
    }
    
    return lines;
  }, [rows, cols]);

  return (
    <svg width={width} height={height} className="warroom-grid">
      {/* Background */}
      <rect width={width} height={height} fill="#1a1a1a" />
      
      {/* Grid lines */}
      {gridLines.map(line => (
        <line
          key={line.key}
          x1={line.x1}
          y1={line.y1}
          x2={line.x2}
          y2={line.y2}
          stroke={line.stroke}
          strokeWidth={1}
        />
      ))}
      
      {/* Subtle scanlines effect (via CSS) */}
      <defs>
        <pattern id="scanlines" patternUnits="userSpaceOnUse" width="100%" height="2">
          <line x1="0" y1="1" x2="100%" y2="1" stroke="rgba(0,0,0,0.15)" strokeWidth="1" />
        </pattern>
      </defs>
      <rect width={width} height={height} fill="url(#scanlines)" opacity="0.03" />
    </svg>
  );
};

export default IsometricGrid;
AgentSprite.jsx Implementation
javascriptimport React, { useState } from 'react';
import { motion } from 'framer-motion';

const AgentSprite = ({ agent, position, onClickAgent, roomType }) => {
  const [isHovered, setIsHovered] = useState(false);

  // Idle animation variants
  const idleVariants = {
    animate: {
      y: [0, -8, 0],
      transition: {
        duration: 3,
        repeat: Infinity,
        ease: 'easeInOut'
      }
    }
  };

  // Active animation (when agent is running a check)
  const activeVariants = {
    pulse: {
      opacity: [1, 0.6, 1],
      scale: [1, 1.08, 1],
      transition: {
        duration: 2,
        repeat: Infinity,
        ease: 'easeInOut'
      }
    }
  };

  // Get color based on agent status
  const getAgentColor = () => {
    if (agent.status === 'paused') return '#FF8C42'; // Orange warning
    if (agent.confidence_score < 50) return '#f44336'; // Red low confidence
    if (agent.p_and_l < 0) return '#f44336'; // Red negative P&L
    return '#4CAF50'; // Green profitable
  };

  const agentColor = getAgentColor();

  return (
    <g
      key={agent.id}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={() => onClickAgent(agent.id)}
      style={{ cursor: 'pointer' }}
    >
      {/* Agent avatar circle */}
      <motion.circle
        cx={position.x}
        cy={position.y}
        r={20}
        fill={agentColor}
        opacity={0.8}
        variants={agent.status === 'active' ? activeVariants : idleVariants}
        animate={agent.status === 'active' ? 'pulse' : 'animate'}
        whileHover={{ scale: 1.15, opacity: 1 }}
      />

      {/* Agent initials or icon */}
      <text
        x={position.x}
        y={position.y}
        textAnchor="middle"
        dominantBaseline="central"
        fill="white"
        fontSize="12"
        fontWeight="bold"
        fontFamily="monospace"
        pointerEvents="none"
      >
        {agent.name.substring(0, 1).toUpperCase()}
      </text>

      {/* Status indicator (small dot) */}
      <circle
        cx={position.x + 18}
        cy={position.y - 18}
        r={6}
        fill={agent.status === 'active' ? '#FFFF00' : '#4a9ede'}
        opacity={0.9}
      />

      {/* Hover tooltip */}
      {isHovered && (
        <g>
          {/* Tooltip background */}
          <rect
            x={position.x - 50}
            y={position.y - 50}
            width={100}
            height={35}
            fill="#000"
            stroke="#4a9ede"
            strokeWidth={1}
            rx={4}
          />
          {/* Tooltip text */}
          <text
            x={position.x}
            y={position.y - 35}
            textAnchor="middle"
            fill="#e8e8e8"
            fontSize="11"
            fontFamily="monospace"
          >
            {agent.name}
          </text>
          <text
            x={position.x}
            y={position.y - 23}
            textAnchor="middle"
            fill="#a0a0a0"
            fontSize="10"
            fontFamily="monospace"
          >
            {agent.status === 'paused' ? '⏸ Paused' : '✅ Active'}
          </text>
        </g>
      )}

      {/* Notifications above agent (for trade results, approvals, etc) */}
      {/* Rendered separately in TradeNotification component */}
    </g>
  );
};

export default AgentSprite;

ANIMATION SYSTEM
Animation Library: Framer Motion
Why Framer Motion:

Declarative animation API (easy to understand)
Works well with React
Smooth performance
Built-in spring physics for bouncy feel
Supports gesture animations

Animation Specs
javascript// 1. AGENT IDLE ANIMATION (Always looping)
// Movement: ±8px vertical sway
// Duration: 3 seconds
// Easing: easeInOut
// Effect: Subtle breathing/swaying motion
const idleVariants = {
  animate: {
    y: [0, -8, 0],
    transition: {
      duration: 3,
      repeat: Infinity,
      ease: 'easeInOut'
    }
  }
};

// 2. AGENT ACTIVE ANIMATION (While checking market)
// Movement: Pulse effect (opacity + scale)
// Duration: 2 seconds
// Effect: Indicates agent is "thinking"
const activeVariants = {
  pulse: {
    opacity: [1, 0.6, 1],
    scale: [1, 1.08, 1],
    transition: {
      duration: 2,
      repeat: Infinity,
      ease: 'easeInOut'
    }
  }
};

// 3. TRADE EXECUTION NOTIFICATION
// Pops up above agent head
// Duration: 0.2s pop-in, 2.5s hold, 0.5s fade-out
const tradeNotificationVariants = {
  initial: { opacity: 0, scale: 0.3, y: -20 },
  animate: { 
    opacity: 1, 
    scale: 1, 
    y: 0,
    transition: { duration: 0.2, ease: 'easeOut' }
  },
  exit: { 
    opacity: 0, 
    scale: 0.8, 
    y: -30,
    transition: { duration: 0.5, ease: 'easeIn' }
  }
};

// 4. APPROVAL DIALOG SLIDE-IN
// Comes from top, bounces slightly
// Duration: 0.3s
const approvalDialogVariants = {
  initial: { opacity: 0, y: -50 },
  animate: { 
    opacity: 1, 
    y: 0,
    transition: {
      type: 'spring',
      stiffness: 300,
      damping: 20,
      duration: 0.3
    }
  },
  exit: { 
    opacity: 0, 
    y: -50,
    transition: { duration: 0.2 }
  }
};

// 5. INSPECTOR PANEL SLIDE-OUT
// Slides in from right side
// Duration: 0.3s
const inspectorVariants = {
  initial: { x: 400, opacity: 0 },
  animate: { 
    x: 0, 
    opacity: 1,
    transition: { duration: 0.3, ease: 'easeOut' }
  },
  exit: { 
    x: 400, 
    opacity: 0,
    transition: { duration: 0.2 }
  }
};

// 6. ROOM TRANSITION (Camera pan/zoom)
// Smooth zoom into selected room
// Duration: 0.5s
const roomTransitionVariants = {
  initial: { scale: 1, opacity: 1 },
  exit: { 
    scale: 0.8, 
    opacity: 0,
    transition: { duration: 0.5, ease: 'easeInOut' }
  }
};

// 7. HOVER EFFECTS (Agent sprite)
const hoverVariants = {
  hover: {
    scale: 1.15,
    opacity: 1,
    transition: { duration: 0.2 }
  }
};

// 8. PAUSED AGENT HANDCUFFS ANIMATION
// Handcuffs appear above agent when paused
const handcuffVariants = {
  initial: { opacity: 0, scale: 0 },
  animate: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.3 }
  }
};

// 9. ALERT/NOTIFICATION TOAST
// Slides in from top-right
// Duration: 0.3s in, auto-dismiss 4s, 0.3s out
const toastVariants = {
  initial: { x: 400, opacity: 0 },
  animate: { 
    x: 0, 
    opacity: 1,
    transition: { duration: 0.3, ease: 'easeOut' }
  },
  exit: { 
    x: 400, 
    opacity: 0,
    transition: { duration: 0.3 }
  }
};

// 10. BUTTON PRESS EFFECT (Retro style)
// Slight inward press, then bounce back
const buttonPressVariants = {
  initial: { scale: 1 },
  hover: { scale: 1.05 },
  tap: { scale: 0.95 }
};
Using Animations in Components
javascriptimport { motion } from 'framer-motion';

function AgentExample() {
  return (
    <motion.circle
      cx={100}
      cy={100}
      r={20}
      fill="#4CAF50"
      variants={idleVariants}
      animate="animate"
      initial="initial"
    />
  );
}

function ApprovalDialogExample() {
  return (
    <motion.div
      variants={approvalDialogVariants}
      initial="initial"
      animate="animate"
      exit="exit"
    >
      {/* Dialog content */}
    </motion.div>
  );
}

COLOR PALETTE & STYLING
CSS Variables (Theme)
css:root {
  /* Backgrounds */
  --bg-primary: #1a1a1a;      /* Main background */
  --bg-secondary: #242424;    /* Cards, panels */
  --bg-tertiary: #0a0a0a;     /* Deep elements */
  --bg-hover: #2d2d2d;        /* Hover state */

  /* Primary Colors */
  --color-primary: #2d5a5a;   /* Deep teal (professional) */
  --color-primary-light: #4a7a7a;
  --color-primary-dark: #1a3a3a;

  /* Secondary Colors */
  --color-secondary: #4a9ede; /* Muted cyan (accent) */
  --color-secondary-light: #6ab0ff;
  --color-secondary-dark: #2a7ebe;

  /* Accent Colors */
  --color-accent: #FF8C42;    /* Warm orange (alerts) */
  --color-accent-light: #FFB366;
  --color-accent-dark: #E67C2B;

  /* Status Colors */
  --status-success: #4CAF50;  /* Green (wins) */
  --status-danger: #f44336;   /* Red (losses) */
  --status-warning: #FF8C42;  /* Orange (warnings) */
  --status-info: #4a9ede;     /* Cyan (info) */

  /* Text Colors */
  --text-primary: #e8e8e8;    /* Main text (off-white) */
  --text-secondary: #a0a0a0;  /* Secondary text */
  --text-muted: #666666;      /* Muted text */
  --text-inverse: #1a1a1a;    /* Text on light bg */

  /* Borders & Dividers */
  --border-color: #333333;    /* Main borders */
  --border-light: #444444;    /* Light borders */
  --divider: #1f1f1f;         /* Divider lines */

  /* Typography */
  --font-mono: 'JetBrains Mono', 'IBM Plex Mono', monospace;
  --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-weight-normal: 400;
  --font-weight-medium: 500;
  --font-weight-bold: 700;

  /* Shadows */
  --shadow-sm: 0 2px 4px rgba(0,0,0,0.3);
  --shadow-md: 0 4px 8px rgba(0,0,0,0.4);
  --shadow-lg: 0 8px 16px rgba(0,0,0,0.5);

  /* Z-index */
  --z-base: 1;
  --z-dropdown: 100;
  --z-modal: 1000;
  --z-toast: 2000;
}

body {
  background-color: var(--bg-primary);
  color: var(--text-primary);
  font-family: var(--font-sans);
  line-height: 1.6;
}

code, pre, .monospace {
  font-family: var(--font-mono);
}
Retro Effects CSS
css/* Subtle Scanlines Effect */
.warroom::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-image: repeating-linear-gradient(
    0deg,
    rgba(0, 0, 0, 0.15),
    rgba(0, 0, 0, 0.15) 1px,
    transparent 1px,
    transparent 2px
  );
  pointer-events: none;
  opacity: 0.03; /* Very subtle, not distracting */
}

/* 90s-Style Beveled Button */
.btn-retro {
  background: linear-gradient(135deg, #3a3a3a, #2a2a2a);
  border: 1px solid;
  border-color: #555 #000 #000 #555; /* Beveled effect */
  box-shadow: inset 1px 1px 0 rgba(255,255,255,0.2),
              inset -1px -1px 0 rgba(0,0,0,0.5),
              0 2px 4px rgba(0,0,0,0.3);
  font-weight: bold;
  text-shadow: 1px 1px 0 rgba(0,0,0,0.5);
  padding: 8px 16px;
  cursor: pointer;
  transition: all 0.1s ease;
}

.btn-retro:active {
  box-shadow: inset 2px 2px 0 rgba(0,0,0,0.5),
              inset -1px -1px 0 rgba(255,255,255,0.2),
              0 1px 2px rgba(0,0,0,0.3);
  transform: translateY(1px);
}

.btn-retro:hover {
  background: linear-gradient(135deg, #4a4a4a, #3a3a3a);
}

/* CRT Monitor Glow Effect (on text, optional) */
.crt-glow {
  text-shadow: 0 0 8px rgba(74, 158, 222, 0.5),
               0 0 16px rgba(45, 90, 90, 0.3);
}

/* Grid Lines (isometric) */
.grid-line {
  stroke: rgba(74, 158, 222, 0.2);
  stroke-width: 1;
}

/* Agent Avatar */
.agent-avatar {
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.5));
}

.agent-avatar:hover {
  filter: drop-shadow(0 0 8px rgba(74, 158, 222, 0.6));
}

/* Inspector Panel */
.inspector-panel {
  background-color: var(--bg-secondary);
  border-left: 2px solid var(--color-primary);
  box-shadow: var(--shadow-lg);
  padding: 20px;
}

/* Retro Card Style */
.card-retro {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 16px;
  box-shadow: var(--shadow-sm);
  transition: all 0.2s ease;
}

.card-retro:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

/* Status Badge */
.badge-success {
  background-color: rgba(76, 175, 80, 0.2);
  color: var(--status-success);
  border: 1px solid var(--status-success);
}

.badge-danger {
  background-color: rgba(244, 67, 54, 0.2);
  color: var(--status-danger);
  border: 1px solid var(--status-danger);
}

.badge-warning {
  background-color: rgba(255, 140, 66, 0.2);
  color: var(--color-accent);
  border: 1px solid var(--color-accent);
}

/* Tab Navigation */
.tabs {
  display: flex;
  gap: 8px;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 16px;
}

.tab {
  padding: 8px 12px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: var(--font-mono);
}

.tab:hover {
  color: var(--text-primary);
}

.tab.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}

STATE MANAGEMENT (ZUSTAND)
Store Structure
javascript// stores/agents.store.js
import create from 'zustand';
import { devtools } from 'zustand/middleware';

export const useAgentsStore = create(
  devtools(
    (set, get) => ({
      // State
      agents: [],
      selectedAgentId: null,
      
      // Actions
      setAgents: (agents) => set({ agents }),
      
      updateAgent: (id, updates) =>
        set(state => ({
          agents: state.agents.map(a =>
            a.id === id ? { ...a, ...updates } : a
          )
        })),
      
      selectAgent: (id) => set({ selectedAgentId: id }),
      
      deselectAgent: () => set({ selectedAgentId: null }),
      
      // Selectors
      getAgent: (id) => get().agents.find(a => a.id === id),
      
      getSelectedAgent: () => {
        const id = get().selectedAgentId;
        return get().agents.find(a => a.id === id);
      },
      
      getAgentsByRoom: (room) =>
        get().agents.filter(a => a.room === room),
      
      getTotalAgentsPnL: () =>
        get().agents.reduce((sum, a) => sum + (a.p_and_l || 0), 0)
    }),
    { name: 'agents-store' }
  )
);

// stores/trades.store.js
import create from 'zustand';

export const useTradesStore = create((set, get) => ({
  // State
  trades: [],
  recentTrades: [],
  
  // Actions
  setTrades: (trades) => set({ trades }),
  
  addTrade: (trade) =>
    set(state => ({
      trades: [trade, ...state.trades],
      recentTrades: [trade, ...state.recentTrades.slice(0, 19)] // Keep last 20
    })),
  
  getTrade: (id) => get().trades.find(t => t.id === id),
  
  getTradesByAgent: (agentId) =>
    get().trades.filter(t => t.agent_id === agentId),
  
  getRecentTrades: (limit = 20) =>
    get().trades.slice(0, limit)
}));

// stores/dashboard.store.js
import create from 'zustand';

export const useDashboardStore = create((set, get) => ({
  // State
  portfolio: {
    total_balance: 0,
    cash: 0,
    p_and_l: 0,
    p_and_l_percent: 0,
    return_30d: 0,
    return_ytd: 0,
    max_drawdown: 0,
    sharpe_ratio: 0
  },
  
  allocation: {
    day_trading: { allocated: 0, current: 0, percent: 10 },
    swing_trading: { allocated: 0, current: 0, percent: 30 },
    long_term: { allocated: 0, current: 0, percent: 60 }
  },
  
  // Actions
  updatePortfolio: (portfolioData) =>
    set({ portfolio: portfolioData }),
  
  updateAllocation: (room, percent) =>
    set(state => ({
      allocation: {
        ...state.allocation,
        [room]: { ...state.allocation[room], percent }
      }
    })),
  
  // Selectors
  getAllocationByRoom: (room) =>
    get().allocation[room]
}));

// stores/ui.store.js
import create from 'zustand';

export const useUIStore = create((set, get) => ({
  // State
  currentRoom: 'lobby', // 'lobby', 'day', 'swing', 'long_term', 'control'
  inspectorOpen: false,
  inspectorTab: 'overview',
  notificationQueue: [],
  
  // Actions
  setCurrentRoom: (room) => set({ currentRoom: room }),
  
  openInspector: () => set({ inspectorOpen: true }),
  
  closeInspector: () => set({ inspectorOpen: false }),
  
  setInspectorTab: (tab) => set({ inspectorTab: tab }),
  
  addNotification: (notification) =>
    set(state => ({
      notificationQueue: [
        ...state.notificationQueue,
        { ...notification, id: Date.now() }
      ]
    })),
  
  removeNotification: (id) =>
    set(state => ({
      notificationQueue: state.notificationQueue.filter(n => n.id !== id)
    }))
}));

// stores/websocket.store.js
import create from 'zustand';

export const useWebSocketStore = create((set, get) => ({
  // State
  isConnected: false,
  lastMessageTime: null,
  
  // Actions
  setConnected: (connected) => set({ isConnected: connected }),
  
  updateLastMessageTime: () => set({ lastMessageTime: Date.now() })
}));
Using Stores in Components
javascriptimport { useAgentsStore } from '../stores/agents.store';
import { useUIStore } from '../stores/ui.store';

function WarroomExample() {
  const agents = useAgentsStore(state =>
    state.getAgentsByRoom('day_trading')
  );
  const selectedAgent = useAgentsStore(state =>
    state.getSelectedAgent()
  );
  const openInspector = useUIStore(state => state.openInspector);
  const selectAgent = useAgentsStore(state => state.selectAgent);

  const handleAgentClick = (agentId) => {
    selectAgent(agentId);
    openInspector();
  };

  return (
    <div>
      {agents.map(agent => (
        <AgentSprite
          key={agent.id}
          agent={agent}
          onClickAgent={handleAgentClick}
        />
      ))}
    </div>
  );
}

WEBSOCKET INTEGRATION
WebSocket Events (From Backend)
javascript// Connection setup
const socket = io('http://localhost:8000', {
  reconnection: true,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 5000,
  reconnectionAttempts: Infinity
});

socket.on('connect', () => {
  useWebSocketStore.setState({ isConnected: true });
  console.log('Connected to backend');
});

socket.on('disconnect', () => {
  useWebSocketStore.setState({ isConnected: false });
});

// Agent Status Update
socket.on('agent_update', (data) => {
  const { agent_id, status, p_and_l, confidence_score, active_trade } = data;
  useAgentsStore.getState().updateAgent(agent_id, {
    status,
    p_and_l,
    confidence_score,
    active_trade
  });
});

// Trade Executed
socket.on('trade_executed', (data) => {
  const { agent_id, trade, p_and_l } = data;
  
  // Update trade history
  useTradesStore.getState().addTrade(trade);
  
  // Update agent P&L
  useAgentsStore.getState().updateAgent(agent_id, { p_and_l });
  
  // Show notification
  useUIStore.getState().addNotification({
    type: 'trade_success',
    message: `${trade.symbol} executed`,
    p_and_l: trade.p_and_l,
    agent_id
  });
  
  // Update portfolio
  useDashboardStore.getState().updatePortfolio(data.portfolio);
});

// Trade Approval Needed (Human-in-loop)
socket.on('trade_approval_needed', (data) => {
  const { agent_id, trade_id, trade_details, timeout_seconds } = data;
  
  // Show approval dialog
  useUIStore.getState().addNotification({
    type: 'approval_dialog',
    agent_id,
    trade_id,
    trade_details,
    timeout_seconds
  });
});

// Agent Paused
socket.on('agent_paused', (data) => {
  const { agent_id, reason } = data;
  
  useAgentsStore.getState().updateAgent(agent_id, {
    status: 'paused'
  });
  
  useUIStore.getState().addNotification({
    type: 'warning',
    message: `Agent paused: ${reason}`,
    agent_id
  });
});

// Portfolio P&L Update
socket.on('portfolio_update', (data) => {
  useDashboardStore.getState().updatePortfolio(data);
});

// Risk Alert
socket.on('risk_alert', (data) => {
  const { alert_type, message, severity } = data;
  
  useUIStore.getState().addNotification({
    type: 'risk_alert',
    alert_type,
    message,
    severity
  });
});
Sending Actions to Backend
javascript// Approve a trade (human-in-loop)
function approveTrade(agentId, tradeId) {
  socket.emit('approve_trade', {
    agent_id: agentId,
    trade_id: tradeId,
    approved: true
  });
}

// Reject a trade
function rejectTrade(agentId, tradeId) {
  socket.emit('approve_trade', {
    agent_id: agentId,
    trade_id: tradeId,
    approved: false
  });
}

// Toggle agent enabled/disabled
function toggleAgent(agentId, enabled) {
  fetch(`http://localhost:8000/api/agents/${agentId}/toggle`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled })
  });
}

// Update agent settings
function updateAgentSettings(agentId, settings) {
  fetch(`http://localhost:8000/api/agents/${agentId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings)
  });
}

FILE STRUCTURE
frontend/
├── src/
│   ├── App.jsx (Root component)
│   ├── index.jsx (Entry point)
│   ├── main.jsx (Vite entry)
│   │
│   ├── pages/
│   │   ├── Lobby.jsx
│   │   ├── RoomView.jsx
│   │   └── ControlRoom.jsx
│   │
│   ├── components/
│   │   ├── Warroom/
│   │   │   ├── Warroom.jsx
│   │   │   ├── IsometricGrid.jsx
│   │   │   ├── AgentSprite.jsx
│   │   │   ├── TradeNotification.jsx
│   │   │   ├── ApprovalDialog.jsx
│   │   │   └── warroom.module.css
│   │   │
│   │   ├── Lobby/
│   │   │   ├── LobbyPage.jsx
│   │   │   ├── RiskAgent.jsx
│   │   │   ├── BodyguardAgent.jsx
│   │   │   ├── RoomScorecard.jsx
│   │   │   ├── PortfolioQuickStats.jsx
│   │   │   └── lobby.module.css
│   │   │
│   │   ├── Inspector/
│   │   │   ├── AgentInspector.jsx
│   │   │   ├── tabs/
│   │   │   │   ├── OverviewTab.jsx
│   │   │   │   ├── TradesTab.jsx
│   │   │   │   ├── RulesTab.jsx
│   │   │   │   ├── PerformanceTab.jsx
│   │   │   │   └── SettingsTab.jsx
│   │   │   └── inspector.module.css
│   │   │
│   │   ├── Control/
│   │   │   ├── ControlRoom.jsx
│   │   │   ├── BrokerSection.jsx
│   │   │   ├── LLMSection.jsx
│   │   │   ├── AllocationSection.jsx
│   │   │   ├── AgentManagementSection.jsx
│   │   │   ├── RiskSection.jsx
│   │   │   ├── VaultSection.jsx
│   │   │   └── control.module.css
│   │   │
│   │   ├── Common/
│   │   │   ├── Header.jsx
│   │   │   ├── Footer.jsx
│   │   │   ├── Button.jsx
│   │   │   ├── Input.jsx
│   │   │   ├── Select.jsx
│   │   │   ├── Slider.jsx
│   │   │   ├── Modal.jsx
│   │   │   ├── Toast.jsx
│   │   │   ├── Spinner.jsx
│   │   │   ├── StatusBadge.jsx
│   │   │   └── common.css
│   │   │
│   │   └── GlobalNotifications.jsx
│   │
│   ├── stores/
│   │   ├── agents.store.js
│   │   ├── trades.store.js
│   │   ├── dashboard.store.js
│   │   ├── ui.store.js
│   │   └── websocket.store.js
│   │
│   ├── hooks/
│   │   ├── useWebSocket.js
│   │   ├── useAgent.js
│   │   ├── useDashboard.js
│   │   └── useApprovals.js
│   │
│   ├── utils/
│   │   ├── api-client.js
│   │   ├── websocket-client.js
│   │   ├── coordinate-converter.js
│   │   ├── formatting.js
│   │   └── constants.js
│   │
│   ├── styles/
│   │   ├── index.css (global)
│   │   ├── variables.css (CSS variables)
│   │   ├── retro.css (retro effects)
│   │   ├── animations.css (animation presets)
│   │   ├── theme.css (theme styles)
│   │   └── tailwind.css (tailwind directives)
│   │
│   └── assets/
│       ├── fonts/
│       ├── icons/
│       └── images/
│
├── electron/
│   ├── main.js
│   ├── preload.js
│   └── window.js
│
├── public/
│   ├── index.html
│   └── electron.svg
│
├── package.json
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
├── tsconfig.json
├── .eslintrc.json
└── .prettierrc

DEVELOPMENT ROADMAP
Phase 1: Foundation (Week 1-2)
Week 1:

 Set up Electron + React + Vite boilerplate
 Create basic routing (Lobby → Rooms)
 Set up Zustand stores (agents, trades, dashboard, ui)
 Create global styles and CSS variables
 Create common UI components (Button, Input, Modal, etc)

Week 2:

 Build Lobby page (layout, components)
 Create Risk Agent component (static appearance)
 Create Bodyguard Agent component (static appearance)
 Create RoomScorecard components (4x instances)
 Implement room navigation (click scorecard → transition to room)

Phase 2: Warroom Rendering (Week 3-4)
Week 3:

 Create IsometricGrid SVG component
 Implement isometric coordinate system math
 Create AgentSprite component
 Add idle animation (gentle sway)
 Add active animation (pulse effect)

Week 4:

 Create Warroom container
 Integrate WebSocket connection
 Implement agent position updates
 Create TradeNotification component
 Create ApprovalDialog component

Phase 3: Inspector Panel (Week 5)
Week 5:

 Build AgentInspector slide-out panel
 Create Overview tab
 Create Trades tab
 Create Rules tab
 Create Performance tab
 Create Settings tab

Phase 4: Control Room (Week 6)
Week 6:

 Build ControlRoom page
 Create Broker section
 Create LLM section
 Create Allocation section
 Create Risk section
 Create Vault section

Phase 5: Real-time Integration (Week 7)
Week 7:

 Connect WebSocket to Zustand stores
 Implement agent status updates
 Implement trade execution notifications
 Implement approval dialogs
 Implement portfolio updates
 Test with backend

Phase 6: Polish & Testing (Week 8)
Week 8:

 Animations tuning
 Accessibility audit
 Performance optimization
 Cross-browser testing
 Beta user testing
 Bug fixes
 Release v1.0


GITHUB REPOS FOR INSPIRATION
Retro/Nostalgic Design

https://github.com/MovingLights/nostalgic-css (90s CSS effects)
https://github.com/Crows-Shadow/Retro-CRT-CSS (CRT monitor effects)

Typography

https://github.com/JetBrains/JetBrainsMono (monospace font)
https://github.com/IBM/plex (IBM Plex font family)

Animation Libraries

https://github.com/framer/motion (Framer Motion docs)

Isometric Rendering

https://github.com/pixijs/pixijs (WebGL 2D if needed later)
https://github.com/mrdoob/three.js (3D if needed later)

Electron Examples

https://github.com/electron/electron-quick-start
https://github.com/electron-react-boilerplate/electron-react-boilerplate

UI Components

https://github.com/tailwindlabs/tailwindcss (Tailwind CSS)
https://github.com/radix-ui/primitives (accessible components)


KEY PRINCIPLES

Simplicity First: SVG + React rendering, no unnecessary libraries
Retro but Professional: Vintage aesthetic that feels safe for real money
Performance: Optimize for 50+ concurrent agents without lag
Accessibility: Keyboard navigation, color contrast, screen readers
Maintainability: Clear component hierarchy, reusable components
Responsiveness: Desktop-first, but structured for mobile later


NEXT STEPS

Set up Electron + React boilerplate
Create basic folder structure
Implement global styles and CSS variables
Build common UI components
Create Lobby page
Create Warroom rendering
Connect WebSocket
Test with backend

Ready to build! 🚀

Document Version: 1.0

Last Updated: June 2026

Status: Ready for Implementation
