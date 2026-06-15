LABOURIOUS PHASE 1: FOUNDATION FILES (SKELETON CODE)
Copy-paste ready. All imports, structure, and stubs included.
================================================================================
FILE 1: .env.example (Repository Root)
LLM Configuration
LOCAL_LLM=true
OLLAMA_PORT=11434
OLLAMA_MODEL=mistral
CLOUD_LLM_PROVIDER=anthropic
CLOUD_LLM_API_KEY=
CLOUD_LLM_MODEL=claude-sonnet-4-20250514
Backend Configuration
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
FRONTEND_PORT=3000
DEBUG=false
Database
DB_PATH=./data/labourious.db
LOG_LEVEL=INFO
Trading
PAPER_TRADING=true
Security (auto-generated on first run)
VAULT_PASSWORD=
================================================================================
FILE 2: backend/requirements.txt
Web Framework
fastapi==0.104.1
uvicorn==0.24.0
python-multipart==0.0.6
Database
sqlalchemy==2.0.23
aiosqlite==3.14.0
Async
httpx==0.25.1
aiofiles==23.2.1
Security
cryptography==41.0.5
python-dotenv==1.0.0
Task Scheduling
apscheduler==3.10.4
Data Validation
pydantic==2.5.0
pydantic-settings==2.1.0
LLM APIs
anthropic==0.7.0
openai==1.3.0
Broker APIs
krakenex==2.1.0
ib-insync==10.21.1
Data Processing
pandas==2.1.3
numpy==1.24.3
Testing
pytest==7.4.0
pytest-asyncio==0.21.1
httpx==0.25.1
Utilities
python-json-logger==2.0.7
================================================================================
FILE 3: backend/config.py
from pydantic_settings import BaseSettings
from pathlib import Path
import os
class Settings(BaseSettings):
"""Application settings loaded from .env"""
# LLM Configuration
local_llm: bool = True
ollama_port: int = 11434
ollama_model: str = "mistral"
cloud_llm_provider: str = "anthropic"  # anthropic or openai
cloud_llm_api_key: str = ""
cloud_llm_model: str = "claude-sonnet-4-20250514"

# Backend Configuration
backend_host: str = "127.0.0.1"
backend_port: int = 8000
frontend_port: int = 3000
debug: bool = False

# Database
db_path: str = "./data/labourious.db"

# Logging
log_level: str = "INFO"

# Trading
paper_trading: bool = True

# Security
vault_password: str = ""
encryption_key: str = ""

class Config:
    env_file = ".env"
    case_sensitive = False
Load settings
settings = Settings()
Ensure data directory exists
os.makedirs(os.path.dirname(settings.db_path), exist_ok=True)
os.makedirs("./data/logs", exist_ok=True)
================================================================================
FILE 4: backend/utils/logger.py
import logging
import os
from pathlib import Path
from config import settings
from pythonjsonlogger import jsonlogger
def setup_logger(name: str, level: str = None) -> logging.Logger:
"""
Configure logger for a module.
Args:
    name: Logger name (usually __name__)
    level: Log level (defaults to settings.log_level)

Returns:
    Configured logger instance
"""
if level is None:
    level = settings.log_level

logger = logging.getLogger(name)
logger.setLevel(getattr(logging, level))

# Don't add handlers if already configured
if logger.handlers:
    return logger

# Ensure log directory exists
os.makedirs("./data/logs", exist_ok=True)

# Console handler (human-readable)
console_handler = logging.StreamHandler()
console_handler.setLevel(getattr(logging, level))
console_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_handler.setFormatter(console_formatter)

# File handler (JSON for parsing)
file_handler = logging.FileHandler("./data/logs/labourious.log")
file_handler.setLevel(logging.DEBUG)
file_formatter = jsonlogger.JsonFormatter()
file_handler.setFormatter(file_formatter)

# Add handlers
logger.addHandler(console_handler)
logger.addHandler(file_handler)

return logger
================================================================================
FILE 5: backend/vault/key_derivation.py
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import base64
import os
def derive_key_from_password(
password: str,
salt: bytes = None,
iterations: int = 100000
) -> tuple:
"""
Derive encryption key from password using PBKDF2.
Args:
    password: User's vault password
    salt: Optional salt bytes (generates new if None)
    iterations: Number of iterations (higher = slower but more secure)

Returns:
    Tuple of (key, salt) both as base64 strings
"""
if not password or len(password) < 8:
    raise ValueError("Password must be at least 8 characters")

if salt is None:
    salt = os.urandom(16)

# Derive key using PBKDF2
kdf = PBKDF2(
    algorithm=hashes.SHA256(),
    length=32,
    salt=salt,
    iterations=iterations,
    backend=default_backend()
)
key = base64.urlsafe_b64encode(kdf.derive(password.encode()))

return key, salt
def verify_password(password: str, stored_key: bytes, salt: bytes) -> bool:
"""
Verify password against stored key.
Args:
    password: Password to verify
    stored_key: Previously stored key
    salt: Salt used during original derivation

Returns:
    True if password matches
"""
key, _ = derive_key_from_password(password, salt)
return key == stored_key
================================================================================
FILE 6: backend/vault/encrypted_vault.py
from cryptography.fernet import Fernet, InvalidToken
from vault.key_derivation import derive_key_from_password
import base64
import os
from utils.logger import setup_logger
logger = setup_logger(name)
class EncryptedVault:
"""
Encrypts and stores sensitive data (API keys, secrets) at rest.
Uses AES-256 encryption with user password-derived keys.
"""
def __init__(self, vault_password: str, salt: bytes = None):
    """
    Initialize vault with password.
    
    Args:
        vault_password: User-provided vault password (8+ chars)
        salt: Optional salt (generates new if None)
    
    Raises:
        ValueError: If password is too short
    """
    if not vault_password or len(vault_password) < 8:
        raise ValueError("Vault password must be 8+ characters")
    
    self.password = vault_password
    self.salt = salt or os.urandom(16)
    self.key, _ = derive_key_from_password(vault_password, self.salt)
    self.cipher_suite = Fernet(self.key)
    
    logger.info("Vault initialized")

def encrypt(self, plaintext: str) -> str:
    """
    Encrypt data.
    
    Args:
        plaintext: String to encrypt
    
    Returns:
        Encrypted string (can be stored in database)
    """
    try:
        encrypted = self.cipher_suite.encrypt(plaintext.encode())
        return encrypted.decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise

def decrypt(self, ciphertext: str) -> str:
    """
    Decrypt data.
    
    Args:
        ciphertext: Encrypted string
    
    Returns:
        Decrypted plaintext
    
    Raises:
        ValueError: If decryption fails (wrong password or corrupted data)
    """
    try:
        decrypted = self.cipher_suite.decrypt(ciphertext.encode())
        return decrypted.decode()
    except InvalidToken:
        logger.error("Decryption failed - wrong password or corrupted data")
        raise ValueError("Decryption failed - wrong password?")
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        raise

def export_backup(self, filepath: str):
    """
    Export encrypted backup (for user to store safely).
    
    Args:
        filepath: Where to save backup file
    """
    try:
        backup_data = {
            "salt": base64.b64encode(self.salt).decode(),
            "version": "1.0"
        }
        # In practice, user would export encrypted keys separately
        with open(filepath, 'w') as f:
            import json
            json.dump(backup_data, f)
        logger.info(f"Backup exported to {filepath}")
    except Exception as e:
        logger.error(f"Failed to export backup: {e}")
        raise

@staticmethod
def create_vault(vault_password: str) -> "EncryptedVault":
    """Create new vault"""
    return EncryptedVault(vault_password)
================================================================================
FILE 7: backend/database/db.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event
import os
from config import settings
from utils.logger import setup_logger
logger = setup_logger(name)
Construct database URL
DATABASE_URL = f"sqlite+aiosqlite:///{settings.db_path}"
Create async engine
engine = create_async_engine(
DATABASE_URL,
echo=settings.debug,
future=True,
connect_args={"timeout": 30}
)
Create session factory
AsyncSessionLocal = sessionmaker(
engine,
class_=AsyncSession,
expire_on_commit=False,
autoflush=False,
autocommit=False
)
async def get_db():
"""
Dependency injection for FastAPI routes.
Usage:
    @router.get("/items")
    async def get_items(db: AsyncSession = Depends(get_db)):
        ...
"""
async with AsyncSessionLocal() as session:
    try:
        yield session
    except Exception as e:
        logger.error(f"Database error: {e}")
        await session.rollback()
        raise
    finally:
        await session.close()
async def init_db():
"""
Initialize database schema.
Call this on application startup.
"""
try:
from database.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")
    raise
async def close_db():
"""Close database connection"""
await engine.dispose()
================================================================================
FILE 8: backend/database/models.py
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, JSON, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
Base = declarative_base()
class Agent(Base):
"""Trading agent entity"""
tablename = "agents"
id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
name = Column(String, nullable=False, index=True)
room = Column(String, nullable=False)  # day_trading, swing_trading, long_term
asset = Column(String, nullable=False)
broker = Column(String, nullable=False)
enabled = Column(Boolean, default=True, index=True)
config = Column(JSON, nullable=False)
context_file_path = Column(String)
created_at = Column(DateTime, default=datetime.utcnow, index=True)
updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Relationships
trades = relationship("Trade", back_populates="agent", cascade="all, delete-orphan")
performance = relationship("AgentPerformance", back_populates="agent", cascade="all, delete-orphan")
class Trade(Base):
"""Trade execution record"""
tablename = "trades"
id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
agent_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)
symbol = Column(String, nullable=False)
side = Column(String, nullable=False)  # BUY, SELL
quantity = Column(Float, nullable=False)
entry_price = Column(Float, nullable=False)
entry_time = Column(DateTime, nullable=False)
exit_price = Column(Float)
exit_time = Column(DateTime)
p_and_l = Column(Float)
p_and_l_percent = Column(Float)
reason = Column(Text)
status = Column(String)  # open, closed, rejected
created_at = Column(DateTime, default=datetime.utcnow, index=True)

# Relationships
agent = relationship("Agent", back_populates="trades")
class AgentPerformance(Base):
"""Daily performance metrics"""
tablename = "agent_performance"
id = Column(Integer, primary_key=True, autoincrement=True)
agent_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)
date = Column(String, nullable=False)  # YYYY-MM-DD format
total_return_pct = Column(Float)
win_rate = Column(Float)
sharpe_ratio = Column(Float)
max_drawdown = Column(Float)
num_trades = Column(Integer)
num_wins = Column(Integer)
num_losses = Column(Integer)

# Relationships
agent = relationship("Agent", back_populates="performance")
class BrokerConfig(Base):
"""Encrypted broker credentials"""
tablename = "broker_configs"
id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
broker_name = Column(String, nullable=False)
api_key_encrypted = Column(String, nullable=False)
api_secret_encrypted = Column(String, nullable=False)
account_id = Column(String)
extra_config = Column(JSON)
created_at = Column(DateTime, default=datetime.utcnow)
class Log(Base):
"""Application logs"""
tablename = "logs"
id = Column(Integer, primary_key=True, autoincrement=True)
timestamp = Column(DateTime, default=datetime.utcnow, index=True)
agent_id = Column(String, index=True)
level = Column(String)  # INFO, WARNING, ERROR, DEBUG
message = Column(Text)
context = Column(JSON)
================================================================================
FILE 9: backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from pathlib import Path
from config import settings
from database.db import init_db, close_db
from utils.logger import setup_logger
logger = setup_logger(name)
Global state (will be populated on startup)
vault = None
orchestrator = None
@asynccontextmanager
async def lifespan(app: FastAPI):
"""Handle startup and shutdown events"""
# STARTUP
try:
logger.info("=" * 50)
logger.info("LABOURIOUS BACKEND STARTING")
logger.info("=" * 50)
logger.info(f"Environment: {'DEBUG' if settings.debug else 'PRODUCTION'}")
logger.info(f"Paper Trading: {settings.paper_trading}")
logger.info(f"LLM: {'Local Ollama' if settings.local_llm else settings.cloud_llm_provider}")
    # Initialize database
    await init_db()
    logger.info("✅ Database initialized")
    
    # Initialize vault
    from vault.encrypted_vault import EncryptedVault
    global vault
    if not settings.vault_password:
        logger.warning("⚠️  No vault password set! Run setup.py first.")
        vault = None
    else:
        vault = EncryptedVault(settings.vault_password)
        logger.info("✅ Vault initialized")
    
    logger.info("✅ Backend started successfully")
    logger.info("=" * 50)

except Exception as e:
    logger.error(f"❌ Startup failed: {e}")
    raise

yield

# SHUTDOWN
logger.info("Shutting down...")
await close_db()
logger.info("Goodbye!")
Create FastAPI app
app = FastAPI(
title="Labourious Trading API",
description="AI trading warroom backend",
version="1.0.0",
lifespan=lifespan,
docs_url="/docs",
redoc_url="/redoc",
openapi_url="/openapi.json"
)
Add CORS middleware
app.add_middleware(
CORSMiddleware,
allow_origins=[""],  # In production, restrict this
allow_credentials=True,
allow_methods=[""],
allow_headers=["*"],
)
Health check route (doesn't require any initialization)
@app.get("/api/health")
async def health_check():
"""Basic health check"""
return {
"status": "healthy",
"version": "1.0.0",
"message": "Labourious backend is running",
"debug": settings.debug,
"paper_trading": settings.paper_trading,
}
Routes will be registered here in Phase 3+
@app.include_router(agents.router)
@app.include_router(brokers.router)
... etc
if name == "main":
import uvicorn
uvicorn.run(
    app,
    host=settings.backend_host,
    port=settings.backend_port,
    log_level=settings.log_level.lower(),
    reload=settings.debug
)
================================================================================
FILE 10: .gitignore
Python
pycache/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST
*.pot
Virtual environments
venv/
ENV/
env/
.venv
IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store
*.sublime-project
*.sublime-workspace
Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
Labourious specific
.env
data/
!data/.gitkeep
*.db
*.enc
*.key
logs/
!logs/.gitkeep
Node (frontend)
node_modules/
npm-debug.log
yarn-error.log
dist/
build/
OS
.DS_Store
Thumbs.db
================================================================================
FILE 11: setup.cfg (Python project config)
[metadata]
name = labourious
version = 1.0.0
author = Labourious Contributors
description = AI trading warroom with encrypted credentials
long_description = file: README.md
long_description_content_type = text/markdown
url = https://github.com/yourusername/labourious
project_urls =
Bug Tracker = https://github.com/yourusername/labourious/issues
Documentation = https://github.com/yourusername/labourious/docs
license = MIT
[options]
packages = find:
python_requires = >=3.9
install_requires =
fastapi>=0.104.0
uvicorn>=0.24.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
[options.packages.find]
where = backend
[tool:pytest]
testpaths = tests
python_files = test_.py
python_classes = Test
python_functions = test_*
asyncio_mode = auto
filterwarnings =
ignore::DeprecationWarning
[flake8]
max-line-length = 100
exclude = venv,pycache,.git
[mypy]
python_version = 3.9
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = False
================================================================================
DIRECTORY STRUCTURE FOR PHASE 1
labourious/
├── .env.example              ← Copy to .env
├── .gitignore
├── LICENSE
├── setup.cfg
├── README.md
├── backend/
│   ├── init.py          ← Empty file
│   ├── main.py              ← FastAPI entry
│   ├── config.py            ← Settings
│   ├── requirements.txt
│   │
│   ├── database/
│   │   ├── init.py
│   │   ├── db.py            ← Connection & init
│   │   ├── models.py        ← SQLAlchemy models
│   │   └── migrations/
│   │       └── init.sql     ← SQL backup
│   │
│   ├── vault/
│   │   ├── init.py
│   │   ├── key_derivation.py
│   │   └── encrypted_vault.py
│   │
│   ├── utils/
│   │   ├── init.py
│   │   └── logger.py
│   │
│   ├── api/
│   │   └── init.py      ← Empty (routes added later)
│   │
│   └── tests/
│       ├── init.py
│       └── test_phase1.py   ← Phase 1 tests
│
├── frontend/
│   ├── package.json         ← Added in Phase 2
│   └── src/
│       └── (added in Phase 2)
│
├── data/                    ← Auto-created
│   ├── .gitkeep
│   └── logs/
│       └── .gitkeep
│
└── tests/
└── (added in Phase 3+)
================================================================================
NEXT STEPS AFTER CREATING THESE FILES

Copy .env.example to .env
$ cp .env.example .env
Create Python virtual environment
$ python3 -m venv venv
$ source venv/bin/activate  # On Windows: venv\Scripts\activate
Install dependencies
$ pip install -r backend/requirements.txt
Run Phase 1 tests (see test file)
$ pytest tests/ -v
Verify database and vault work
$ python -c "from database.db import init_db; import asyncio; asyncio.run(init_db())"
Start backend (should see health check)
$ python backend/main.py
Test health endpoint
$ curl http://127.0.0.1:8000/api/health

If all of these work, Phase 1 is complete! ✅
