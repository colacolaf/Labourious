# Labourious Phase 1 - Complete Architecture Generation

## Project Overview
Build complete Phase 1 foundation for Labourious AI trading warroom.

## References
- PROJECT_STRUCTURE.md (folder organization)
- PHASE_1_SKELETON_CODE.md (starter code)
- ARCHITECTURE.md (technical design)
- README.md (project vision)
- FEATURES.md (feature list)
- AGENTS.md (agent types)

## Generate These Files

### Backend Foundation
- backend/__init__.py
- backend/main.py
- backend/config.py
- backend/requirements.txt
- backend/database/db.py
- backend/database/models.py
- backend/vault/key_derivation.py
- backend/vault/encrypted_vault.py
- backend/utils/logger.py
- backend/api/__init__.py
- backend/api/health.py (health check endpoint)

### Frontend Foundation
- frontend/package.json
- frontend/src/index.jsx
- frontend/src/App.jsx
- frontend/src/electron-main.js
- frontend/src/preload.js
- frontend/src/styles/index.css
- frontend/src/stores/agents.store.js
- frontend/src/stores/dashboard.store.js
- frontend/src/utils/api-client.js
- frontend/src/utils/constants.js
- frontend/public/index.html

### Config & Documentation
- .env.example
- .gitignore
- setup.cfg
- README.md
- docker/Dockerfile
- docker-compose.yml

## Requirements

### Backend (Python)
- FastAPI
- SQLAlchemy
- Cryptography (Fernet + PBKDF2)
- httpx (async HTTP)
- python-dotenv

### Frontend (Node/React)
- React 18+
- Electron
- Zustand (state management)
- Framer Motion (animations)
- Recharts (charts)
- Socket.io-client (WebSocket)
- Axios (HTTP client)

## Instructions

1. Generate all files listed above
2. Use complete, production-ready code (not pseudocode)
3. All imports must work
4. Database models must be complete
5. Encryption vault must have full AES-256 implementation
6. FastAPI app must have startup/shutdown events
7. React stores must be complete Zustand implementations
8. All __init__.py files must exist
9. All dependencies must be listed in requirements.txt and package.json

## Output Format
- Create each file with complete working code
- Include all necessary imports
- All functions should be functional (even if they return stubs for logic)
- All async functions properly defined
