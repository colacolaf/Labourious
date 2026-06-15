# Labourious

**AI Trading Warroom** — autonomous agent orchestration platform for algorithmic trading.

## Overview

Labourious is a desktop application (Electron + React) backed by a FastAPI Python server. Multiple AI trading agents run concurrently, each with configurable strategy, risk parameters, and exchange credentials stored in an AES-256 encrypted vault.

## Architecture

| Layer | Technology |
|-------|-----------|
| Desktop Shell | Electron 32 |
| Frontend | React 18, Zustand, Framer Motion, Recharts |
| Backend API | FastAPI + Uvicorn |
| Database | SQLite (SQLAlchemy ORM) |
| Secrets | AES-256 Fernet + PBKDF2 vault |
| Real-time | WebSocket (Socket.io) |

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit VAULT_PASSWORD
python -m backend.main
```

### Frontend

```bash
cd frontend
npm install
npm start             # web dev server
npm run electron:dev  # Electron + React dev
```

### Docker

```bash
cp .env.example .env
docker-compose up --build
```

## Project Structure

```
labourious/
├── backend/
│   ├── api/          # FastAPI route handlers
│   ├── database/     # SQLAlchemy models + session management
│   ├── vault/        # AES-256 encrypted secrets store
│   └── utils/        # Logging, helpers
├── frontend/
│   ├── public/       # Static HTML template
│   └── src/
│       ├── stores/   # Zustand state stores
│       ├── styles/   # Global CSS variables (retro theme)
│       └── utils/    # API client, constants
└── docker/           # Container configuration
```

## Phases

- **Phase 1** (current) — Foundation: backend skeleton, DB models, vault, React shell
- **Phase 2** — Agent engine: strategy execution, live trading, WebSocket feed
- **Phase 3** — Analytics: performance dashboards, backtesting, reporting
