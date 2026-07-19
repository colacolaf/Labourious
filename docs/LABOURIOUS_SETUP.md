# Labourious Setup Guide

> **⚠️ Aspirational document.** This guide describes the planned setup process. The source code (backend/, frontend/, tests/) has not yet been rebuilt for the new architecture. Paths referenced below may not exist yet.

## Overview

Labourious is a local-first Electron desktop app you install from GitHub. You bring your own LLM API keys (or local Ollama). The app runs entirely on your machine.

**Requirements:**
- macOS, Windows, or Linux
- Node.js 18+
- Python 3.10+ (for backend)
- Git
- ~2GB disk space

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/colacolaf/Labourious.git
cd Labourious
```

### 2. Backend Setup (Python)

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
```

### 3. Frontend Setup (Electron + React)

```bash
cd frontend
npm install
cd ..
```

### 4. Configure Your LLM

Labourious requires at least one LLM connection. You have four options — use any or all.

#### Option A: Local Ollama (Free, Offline)
```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull a model (mistral, llama3, etc.)
ollama pull mistral

# Verify
curl http://localhost:11434/api/tags
```

No API key needed. Works fully offline.

#### Option B: Anthropic Claude
Get your API key at [console.anthropic.com](https://console.anthropic.com).

Set in `.env`:
```
CLAUDE_API_KEY=sk-ant-...
```

#### Option C: OpenAI (GPT)
Get your API key at [platform.openai.com](https://platform.openai.com).

Set in `.env`:
```
OPENAI_API_KEY=sk-...
```

#### Option D: Google Gemini
Get your API key at [aistudio.google.com](https://aistudio.google.com).

Set in `.env`:
```
GEMINI_API_KEY=...
```

### 5. Environment Configuration

```bash
cp .env.example .env
```

Edit `.env` with your settings:
```
# At least one of these:
OLLAMA_ENABLED=true
OLLAMA_MODEL=mistral
CLAUDE_API_KEY=
OPENAI_API_KEY=
GEMINI_API_KEY=

# Default model (which LLM the Portfolio Manager uses)
DEFAULT_MODEL=ollama/mistral

# Database (local SQLite)
DB_PATH=./data/labourious.db

# Vault encryption password (set on first run)
VAULT_PASSWORD=
```

### 6. Launch

**Terminal 1 — Backend:**
```bash
source .venv/bin/activate
python -m backend.main
```
Runs on `http://localhost:8000`

**Terminal 2 — Frontend (Electron):**
```bash
cd frontend
npm run electron:dev
```

The Electron app opens as a native desktop window.

---

## Model Flexibility

The Portfolio Manager and all subagents can use the same model or different models:

- **Same model (default):** PM routes all agents through your chosen LLM
- **Per-agent models:** Advanced users can assign specific models to specific agents (e.g., Quant Room gets GPT-4, Sentiment Room gets Claude)
- **Hybrid:** Use local Ollama for routine agents, cloud models for complex analysis

Configure in Settings → LLM Configuration.

---

## Broker Connections (Future)

Broker integration will be configured through the encrypted vault. Supported brokers:
- Interactive Brokers
- Kraken
- Coinbase
- Alpaca
- And more via ccxt

---

## Verify Installation

```bash
# Backend health check
curl http://localhost:8000/api/health

# Should return:
# { "status": "healthy", "version": "2.0.0", ... }
```

---

## Troubleshooting

**"Port 8000 already in use"**
```bash
lsof -i :8000  # macOS/Linux
# Change port in .env: BACKEND_PORT=8001
```

**"Ollama connection failed"**
```bash
ollama serve  # Start Ollama if not running
ollama pull mistral  # Pull a model if none downloaded
```

**"ModuleNotFoundError"**
```bash
# Make sure venv is activated
source .venv/bin/activate
pip install -r backend/requirements.txt
```

---

## Next Steps

1. Read [AGENTS.md](AGENTS.md) — understand the 16 rooms and 30-40 agents
2. Read [ARCHITECTURE.md](LABOURIOUS_ARCHITECTURE.md) — how the Portfolio Manager works
3. Start chatting with your Portfolio Manager

---

*Setup guide will be updated as the project is built out.*
