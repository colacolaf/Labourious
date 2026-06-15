Labourious Installation Guide
Estimated setup time: 15-30 minutes
This guide covers three installation methods. Choose one based on your comfort level:

Option A: Native (Recommended for most) — Python + npm directly on your machine
Option B: Docker (Recommended for safety) — everything containerized, cleaner isolation
Option C: Standalone (Easiest) — download pre-built executable, click to run


Pre-Installation Requirements
For All Options:

Computer: macOS, Windows, or Linux
Internet: Download ~500MB of dependencies (one-time)
Disk space: ~2GB for Labourious + dependencies

For Native & Docker Options:

Git — install here
Basic CLI comfort — not required but helpful


Option A: Native Installation (Python + React)
Step 1: Clone the Repository
bashgit clone https://github.com/yourusername/labourious.git
cd labourious
Step 2: Install Backend Dependencies (Python 3.9+)
macOS / Linux:
bash# Install Python 3.9+ (if not present)
# macOS: brew install python3
# Ubuntu: sudo apt-get install python3 python3-pip

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
Windows (PowerShell):
powershellpython -m venv venv
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
Step 3: Install Frontend Dependencies (Node.js 16+)
bash# Install Node (if not present): https://nodejs.org/

cd frontend
npm install
cd ..
Step 4: Set Up Environment Variables
bash# Copy example env file
cp .env.example .env

# Edit .env with your settings:
# - LOCAL_LLM=true (or false for cloud LLM)
# - OLLAMA_PORT=11434 (if using Ollama)
# - DB_PATH=./data/labourious.db
# - ENCRYPTION_KEY=(auto-generated on first run)
Step 5: Run the Interactive Setup Wizard
bashpython setup.py
The wizard will guide you through:

✅ Checking dependencies
✅ Installing Ollama (optional, but recommended)
✅ Creating encrypted credential vault
✅ Configuring first broker connection (interactive prompts)
✅ Setting initial capital allocation
✅ Running the onboarding tutorial

Step 6: Launch Labourious
Terminal 1 (Backend):
bashpython main.py
You should see: [INFO] FastAPI server running on http://127.0.0.1:8000
Terminal 2 (Frontend):
bashcd frontend
npm start
You should see: [INFO] Electron app opening...
Expected result: Warroom UI opens in Electron window. You're done!

Option B: Docker Installation (All-in-One Container)
Prerequisites:

Docker Desktop — install here
~3GB free disk space (for container image)

Step 1: Clone Repository
bashgit clone https://github.com/yourusername/labourious.git
cd labourious
Step 2: Build Docker Image
bashdocker build -t labourious:latest -f docker/Dockerfile .
Takes ~2-3 minutes on first run.
Step 3: Run Container with Volume Mounts
bashdocker run -it \
  --name labourious \
  -p 3000:3000 \
  -p 8000:8000 \
  -v ~/labourious-data:/app/data \
  -v ~/.labourious-keys:/app/keys \
  labourious:latest
What this does:

-p 3000:3000 — exposes frontend (http://localhost:3000)
-p 8000:8000 — exposes backend (http://localhost:8000)
-v ~/labourious-data:/app/data — persists your trades, logs
-v ~/.labourious-keys:/app/keys — persists encrypted keys on YOUR machine (outside container)

Step 4: Run Setup Wizard Inside Container
bashdocker exec -it labourious python setup.py
Follow prompts (same as native install).
Step 5: Access Labourious
Open browser: http://localhost:3000
Managing the Docker Container
bash# Stop (gracefully)
docker stop labourious

# Restart
docker start labourious

# View logs
docker logs labourious -f

# Remove container (keeps data volumes intact)
docker rm labourious

# Backup keys (before you delete anything)
cp -r ~/.labourious-keys ~/labourious-keys-backup

Option C: Standalone Executable (Windows/macOS Only)
Step 1: Download
Download labourious-v1.0.0-{platform}.zip from GitHub Releases
Step 2: Extract & Run
Windows:

Extract zip to C:\Program Files\Labourious (or anywhere)
Double-click labourious.exe

macOS:

Extract zip to Applications
Double-click Labourious.app
(First run: right-click → Open, then confirm security)

Step 3: Setup Wizard Opens Automatically
Follow the on-screen prompts. No terminal needed.
Step 4: Done!
Warroom opens automatically.

Security Setup: Creating Your Encrypted Vault
During setup.py, you'll be asked to:

Set a Vault Password (8+ characters, not your broker password)

This encrypts all broker API keys at rest
You'll need this password only when launching Labourious


Connect First Broker

Choose broker (Interactive Brokers, Kraken, Coinbase, etc.)
Provide API credentials
These are encrypted and stored locally ONLY
Labourious will ask for vault password on next launch


Backup Encrypted Keyfile

System generates ~/.labourious/keys/backup.enc
Store this file somewhere safe (external drive, password manager)
If you lose your vault password, this backup allows recovery



Security best practices:

✅ Use strong vault password (uppercase, lowercase, numbers, symbols)
✅ Never share your vault password
✅ Back up encrypted keyfiles regularly
✅ Keep Labourious updated (security patches)
✅ Review broker API key permissions (read-only for first tests)


Configuring Your First Broker
Interactive Brokers (Recommended)

Create API account:

Log in to IB account management
Enable "API Access"
Generate API key + secret


In Labourious setup wizard:

   Broker: Interactive Brokers
   Account ID: [your IB account number]
   API Key: [paste here]
   Secret: [paste here]
   Paper Trading: [yes/no]

Verify connection:

Wizard fetches your account balance
Asks: "Is this correct?" before proceeding



Kraken (Crypto)

Create API key:

Settings → API
Generate new key
Permissions: Query Funds, Query Orders, Query Trades, Create & Modify Orders


In Labourious setup wizard:

   Broker: Kraken
   API Key: [paste here]
   Private Key: [paste here]
   2FA: [if enabled, enter here]
Coinbase
Similar to Kraken — see BROKERS.md for detailed steps

Installing Ollama (Local LLM)
If you chose "local LLM" during setup, Ollama will be installed automatically for macOS/Linux. For Windows or manual install:
macOS / Linux
bashcurl https://ollama.ai/install.sh | sh
ollama pull mistral  # Downloads ~4GB model
Windows

Download ollama.com
Run installer
In terminal: ollama pull mistral

Verify
bashcurl http://localhost:11434/api/generate -d '{"model":"mistral","prompt":"test","stream":false}'
If you see a response, Ollama is working.

Choosing Your LLM: Local vs Cloud
Local LLM (Ollama) - Recommended for Privacy
AspectLocalCloudCostFree~$0.001-0.01 per decisionSpeed1-3 sec/decision0.5-1 sec/decisionPrivacyYour data never leaves your machineData sent to Anthropic/OpenAI serversQualityGood for most strategiesBetter for complex reasoningSetupAuto-installedNeed API keyInternetWorks offlineRequires internet
Recommended Defaults:

Beginners & learning: Local Ollama (free, private, good enough)
Serious traders: Start local, upgrade to Claude API for complex rules
High-frequency traders: Cloud LLM likely better (lower latency)

Switching LLMs After Setup
Edit .env:
env# Local
LOCAL_LLM=true
OLLAMA_MODEL=mistral

# Cloud
LOCAL_LLM=false
CLOUD_LLM_PROVIDER=anthropic  # or openai
CLOUD_LLM_API_KEY=[your key]
CLOUD_LLM_MODEL=claude-sonnet-4-20250514
Then restart backend: python main.py

Paper Trading Setup (Test Before Going Live!)
During setup or in Settings, configure:
Paper Trading Mode: ENABLED
Initial Balance: $100,000
Slippage Simulation: 0.1%
Commission: $10 per trade
This mode:

✅ Simulates trades without real money
✅ Still uses live market data
✅ Shows what your agents WOULD do
✅ Helps test rules before going live

Best practice: Run agents in paper mode for 2-4 weeks before going live.

Verifying Your Installation
Run the verification script:
bashpython verify_install.py
Checklist:

✅ Python 3.9+
✅ Node.js 16+
✅ Database initialized
✅ Broker connection working
✅ LLM responding
✅ Vault encrypted properly

All green? You're ready to go.

Troubleshooting
"ModuleNotFoundError: No module named 'fastapi'"
bash# Activate virtual environment first
source venv/bin/activate  # macOS/Linux
# or
.\venv\Scripts\Activate.ps1  # Windows

pip install -r requirements.txt
"Port 8000 already in use"
bash# Find what's using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Use different port
export BACKEND_PORT=8001  # or set in .env
python main.py
"Broker connection failed"

Verify API credentials in vault: python manage_vault.py
Check broker is online (try logging in directly)
Confirm API key permissions allow trading account access
Try paper trading first (don't require live account)

"Ollama connection failed"
bash# Check if Ollama is running
ollama serve

# Check connection
curl http://localhost:11434/api/tags

# If not installed
ollama pull mistral
"Cannot find vault password"
If you forget your vault password:

Stop Labourious
Delete ~/.labourious/vault.db
Restart and run setup.py again
⚠️ You'll need to re-enter all broker credentials

Better: Use encrypted keyfile backup:
bashpython restore_vault.py --backup ~/.labourious/keys/backup.enc

Next Steps

✅ You're installed! Open http://localhost:3000
📖 Read AGENT_CREATION.md — write your first trading rule
🎮 Follow FIRST_TRADE.md — paper trading walkthrough
🚀 Deploy agents — start with paper mode, graduate to small live positions


Getting Help

Setup issues? Check TROUBLESHOOTING.md
Specific broker problems? See BROKERS.md
General questions? Open a GitHub Issue


Ready? Launch Labourious and watch your AI trading warroom come to life. 🚀
