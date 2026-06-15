Troubleshooting Guide
Solutions for common Labourious issues. Most problems can be solved here.

Installation & Setup Issues
ERROR: "ModuleNotFoundError: No module named 'fastapi'"
Cause: Python virtual environment not activated
Solution:
bash# Activate virtual environment first

# macOS/Linux:
source venv/bin/activate

# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Windows Command Prompt:
venv\Scripts\activate

# Then install dependencies:
pip install -r backend/requirements.txt

ERROR: "npm: command not found"
Cause: Node.js not installed
Solution:

Go to https://nodejs.org/
Download and install Node.js (LTS version)
Restart terminal
Verify: node --version and npm --version


ERROR: "Port 3000 already in use"
Cause: Another app is using frontend port
Solution:
bash# Find what's using port 3000:

# macOS/Linux:
lsof -i :3000

# Windows:
netstat -ano | findstr :3000

# Then either:
# 1. Kill the process (if you control it)
# 2. Or use different port:
export FRONTEND_PORT=3001
npm start

ERROR: "Port 8000 already in use"
Cause: Another backend instance already running
Solution:
bash# Kill existing backend process:

# macOS/Linux:
pkill -f "python main.py"

# Windows:
taskkill /F /IM python.exe

# Wait 10 seconds, then restart:
python main.py

ERROR: "pip install fails with 'PermissionError'"
Cause: Installing to system Python (not virtual environment)
Solution:
bash# Make sure virtual environment is activated:
source venv/bin/activate  # macOS/Linux
.\venv\Scripts\Activate.ps1  # Windows

# Then try pip install again:
pip install -r backend/requirements.txt

# Verify venv is active (should show "(venv)" in prompt)

Broker Connection Issues
ERROR: "Connection refused to Interactive Brokers"
Cause: IB Gateway not running
Solution:

Download IB Gateway from Interactive Brokers website
Install and start IB Gateway
Log in with your IB username and password
In Labourious, test connection again
Expected: "✅ Connected to IB - Balance: $[amount]"

Verify IB Gateway is running:
bash# Test connection:
telnet 127.0.0.1 7497

# Should show connection (not "connection refused")

ERROR: "Invalid API key" (Kraken)
Cause: API key copied incorrectly
Solution:

Log into Kraken
Go to Settings → API
Click on your API key
Click "Show" button next to API Key
Copy the ENTIRE key (watch for spaces)
Paste into Labourious
Check for extra spaces before/after

Common mistakes:

Extra space at beginning or end
Only copied part of the key
Copied while the field was still loading


ERROR: "EAPI:Invalid signature" (Kraken)
Cause: Private key is incorrect or incomplete
Solution:

Go to Kraken Settings → API
Click "Show" button next to Private Key
Copy the ENTIRE private key (it's very long!)
Make sure no spaces before/after
Paste into Labourious
Test connection again

Remember: Kraken keys are case-sensitive!

ERROR: "2FA required" (Kraken)
Cause: Your Kraken account has 2FA enabled
Solution Option 1: Enter 2FA code in Labourious

Get code from your authenticator app
In Labourious settings, paste the 2FA code
Test connection

Solution Option 2: Disable 2FA (less secure)

Log into Kraken
Go to Settings → Security
Disable 2FA
You can re-enable it later if wanted


ERROR: "Account not authorized for Advanced Trading" (Coinbase)
Cause: Using regular Coinbase instead of Coinbase Advanced
Solution:

Log into www.coinbase.com
Go to Settings → Accounts
Look for "Advanced Trading" or "Pro Trading"
Click "Upgrade"
May require minimum account balance
Contact Coinbase support if issues


ERROR: "Connection test passed, but trades aren't executing"
Cause: Multiple possible reasons
Checklist:

 Do I have enough buying power? (Check in broker app)
 Is the market open? (Stocks: 9:30am-4pm EST, Crypto: 24/7)
 Is the position size valid for the broker? (Check minimums)
 Are the symbols correct? (IB uses NASDAQ tickers, Kraken uses PAIR format)
 Have I set stop losses? (Some brokers require stops for certain assets)
 Is the order within reasonable price range? (No limit orders at 10% from current)


LLM & Market Data Issues
ERROR: "Connection refused to Ollama"
Cause: Ollama not running
Solution:
bash# Start Ollama in terminal:
ollama serve

# Or on macOS:
# Click Ollama icon in Applications

# Verify Ollama is running:
curl http://localhost:11434/api/tags
# Should list available models

ERROR: "Ollama model not found"
Cause: Model not downloaded yet
Solution:
bash# Download Mistral model:
ollama pull mistral

# Or Llama:
ollama pull llama2

# Check available models:
ollama list
This may take 5-10 minutes (downloads 4GB model)

ERROR: "Claude API key invalid"
Cause: API key expired or incorrect
Solution:

Log into console.anthropic.com
Click "API Keys"
Verify your key is active (not expired)
Copy the key again
Paste into Labourious Settings → LLM
Test by running an agent


ERROR: "Rate limit exceeded (Claude API)"
Cause: Too many API calls too fast
Solution:

Reduce agent check frequency

Change from every 5 min to every 30 min
Spread agents across different schedules


Upgrade Claude API plan (if budget allows)
Switch to local Ollama (no rate limits)

Example staggered schedule:
Agent 1: Check every 30 minutes (9:30, 10:00, 10:30...)
Agent 2: Check every 30 minutes (9:35, 10:05, 10:35...)
Agent 3: Check every 30 minutes (9:40, 10:10, 10:40...)

ERROR: "Market data not loading"
Cause: Broker API not responding or data API down
Solution:

Verify broker connection works (test in broker app)
Check internet connection
Restart Labourious backend
Check if broker API is down (visit broker status page)
Try again in 5 minutes


Database Issues
ERROR: "Database locked"
Cause: Another Labourious instance is running
Solution:
bash# Find and kill existing Labourious:
ps aux | grep main.py  # See what's running

pkill -f main.py  # Kill it

# Wait 5 seconds
sleep 5

# Restart:
python main.py

ERROR: "No such table: agents"
Cause: Database not initialized
Solution:
bash# Initialize database:
python -c "from database.db import init_db; import asyncio; asyncio.run(init_db())"

# Or restart Labourious (should auto-initialize):
python main.py

ERROR: "Disk space full"
Cause: Database grew too large from too many trades
Solution:

Find log files: du -sh ~/.labourious/*
Archive old trades (export to CSV first)
Delete old log files: rm ~/.labourious/logs/*.log
Restart Labourious


Trade Execution Issues
ERROR: "Insufficient funds"
Cause: Account doesn't have cash for trade
Solution:

Check account balance in broker app
Reduce position size in agent config
Or deposit more funds into broker account
Allow 24-48 hours for deposit to clear


ERROR: "Invalid symbol"
Cause: Symbol not recognized by broker
Solution:

Check symbol spelling
Verify symbol exists on broker
Different brokers use different formats:

IB Stocks: AAPL (NASDAQ tickers)
Kraken: XBTUSDT (currency pairs)
Coinbase: BTC-USD (dash-separated)


See BROKERS.md for broker-specific formats


ERROR: "Order rejected by broker"
Cause: Order parameters invalid
Troubleshooting:

 Position size too small? (Check broker minimums)
 Price too far from current? (Limit orders must be close)
 Market closed? (Check trading hours)
 Sufficient buying power? (Check account)
 Order type not supported? (IB supports market/limit/stop)


ERROR: "Trade executed but position shows $0 P&L"
Cause: Price data not updating
Solution:

Restart backend: python main.py
Check broker connection working
Verify market data is flowing (check warroom for price updates)
Wait 1 minute (sometimes data is delayed)


Warroom UI Issues
ERROR: "Warroom not rendering / blank screen"
Cause: Frontend not built properly
Solution:
bash# Stop frontend (Ctrl+C)

# Rebuild:
cd frontend
npm run build

# Restart:
npm start

# Refresh browser (Ctrl+R or Cmd+R)

ERROR: "WebSocket connection failed"
Cause: Backend not running or WebSocket disabled
Solution:

Start backend: python main.py
Check it prints: "FastAPI server running on http://127.0.0.1:8000"
Refresh browser
Check browser console for errors (F12 → Console tab)


ERROR: "Agents not updating in real-time"
Cause: WebSocket disconnected
Solution:

Refresh browser (Ctrl+R)
Restart backend (python main.py)
Open browser DevTools (F12)
Check Network tab for WebSocket errors
Check Console tab for JavaScript errors


ERROR: "Clicking agent does nothing"
Cause: Agent inspector not opening
Solution:

Check browser console for errors (F12)
Refresh warroom page
Try clicking different agent
Restart frontend (npm start)


Vault & Encryption Issues
ERROR: "Vault password incorrect"
Cause: Wrong password entered
Solution:

Try again, type carefully
Check Caps Lock is off
Remember password is case-sensitive
If forgotten, use backup.enc file:

bash   labourious restore-vault --backup ~/.labourious/keys/backup.enc

ERROR: "Cannot decrypt credential"
Cause: Vault corrupted or password wrong
Solution:
bash# Stop Labourious

# Option 1: Restore from backup
labourious restore-vault --backup ~/.labourious/keys/backup.enc

# Option 2: Start fresh
rm ~/.labourious/vault.db
python setup.py  # Re-run setup to re-enter credentials

ERROR: "Missing backup.enc file"
Cause: Backup wasn't created or was deleted
Solution:
bash# If you still have vault.db with correct password:
python -c "from vault import EncryptedVault; v = EncryptedVault('YOUR_PASSWORD'); v.export_backup('/path/to/backup.enc')"

# Otherwise:
# Delete vault.db and restart (will lose all stored credentials)
rm ~/.labourious/vault.db
python setup.py

Performance Issues
ERROR: "Labourious running very slow"
Cause: Too many agents, database too large, LLM slow
Solutions:

Reduce number of agents:

Disable agents you're not using
Pause underperforming agents


Reduce check frequency:

Day traders: Change from every 5 min to every 15 min
Sector traders: Change from daily to twice-daily
Long-term: Keep as is


Switch to local LLM:

If using Claude/GPT API, switch to Ollama
Local is much faster


Restart Labourious:

Clears cache and memory
May improve performance




ERROR: "High CPU usage"
Cause: Agent check frequency too high, LLM processing
Solutions:

Reduce check frequency
Disable slow agents
Switch to local Ollama (faster)
Close other CPU-heavy apps


ERROR: "Memory usage growing over time"
Cause: Memory leak or too much cached data
Solution:

Restart Labourious periodically (daily or weekly)
Clear cache: Delete ~/.labourious/cache/
Archive old trades to CSV
Update to latest version (may fix leak)


Paper Trading Issues
ERROR: "Paper trading not working"
Cause: Paper trading disabled in agent config
Solution:

In agent settings, toggle "Paper Trading Mode" to ON
Or edit agent config: "paper_trading": true
Restart agent
Simulate a trade and verify P&L updates


ERROR: "Simulated orders not executing"
Cause: Entry conditions not being met
Solution:

Review agent rules and current market data
Check context file is logically correct
Run backtest to verify rules work:

bash   labourious backtest agent.json --start=2024-01-01 --end=2024-06-30

Adjust rules if backtest shows issues


Docker Issues
ERROR: "Cannot find docker or docker-compose"
Cause: Docker not installed
Solution:

Install Docker Desktop from docker.com
Start Docker application
Restart terminal
Verify: docker --version


ERROR: "Permission denied while trying to connect to Docker daemon"
Cause: User doesn't have Docker permissions
Solution (Linux):
bash# Add user to docker group:
sudo usermod -aG docker $USER

# Log out and log back in (or restart computer)

# Verify:
docker ps

ERROR: "Volume mount failed"
Cause: Path doesn't exist on host machine
Solution:
bash# Create required directories:
mkdir -p ~/labourious-data
mkdir -p ~/.labourious-keys

# Then run docker:
docker-compose up

Remote Access Issues
ERROR: "Can't access Labourious from another machine"
Cause: Frontend not exposed to network
Solution:

By design, Labourious is localhost-only
To access from another machine, use SSH tunnel:

bash   ssh -L 3000:localhost:3000 user@remote-machine
   # Then visit localhost:3000 on local machine

Or setup VPN to connect to home network


Agent Approval (Human-in-Loop) Issues
ERROR: "Trade approval notification doesn't appear"
Cause: WebSocket disconnected or notifications disabled
Solution:

Check Settings → Notifications are enabled
Refresh browser
Restart backend
Check browser has notification permission


ERROR: "30-second approval timeout too short"
Cause: Default timeout is 30 seconds
Solution:

Edit agent config: "approval_timeout_seconds": 60
Or edit globally in Settings
Restart agent


Getting Additional Help
Step 1: Check Logs
Backend logs:

Shows in terminal where you ran python main.py
Look for error messages, timestamps

Frontend logs:

Open browser DevTools (F12)
Click Console tab
Look for red error messages

Application logs:

Located in: ~/.labourious/logs/
Files: labourious.log
Review for errors with timestamps


Step 2: Search GitHub Issues

Go to github.com/yourusername/labourious/issues
Search for similar error message
Check if issue was already solved
Read through discussion for solutions


Step 3: Create New GitHub Issue
If not found, create new issue with:

Title: Brief description of problem
OS: macOS/Windows/Linux, version
Steps to reproduce: Exact steps that cause error
Error message: Full error text (mask API keys!)
Logs: Relevant log excerpts (mask credentials!)
Screenshots: If UI issue

Do NOT include:

API keys or secrets
Vault passwords
Personal account info


Step 4: Ask Community

Post on GitHub Discussions
Ask on Discord (if community exists)
Be specific about what you've tried
Include relevant error messages


Common Error Messages Explained
ErrorMeaningUsually Caused ByECONNREFUSEDConnection rejectedService not runningEADDRINUSEPort already in useAnother app using portENOENTFile not foundPath doesn't existEINVALIDInvalid inputBad parametersTIMEOUTNo responseService crashed/slowAUTH_ERRORAuthentication failedWrong credentialsPERMISSION_DENIEDNot allowedFile permissions, API scope

Quick Restart Procedures
Quick Restart (Try First)
bash# Terminal 1 (Backend):
Ctrl+C
python main.py

# Terminal 2 (Frontend):
Ctrl+C
npm start

# Browser:
Refresh (Ctrl+R)
Full Restart (More Thorough)
bash# Kill all processes:
pkill -f "python main.py"
pkill -f "npm start"
pkill -f "node"

# Wait 10 seconds:
sleep 10

# Restart backend:
python main.py

# In another terminal:
npm start

# Refresh browser
Nuclear Restart (Last Resort)
bash# Delete cache and restart:
rm -rf ~/.labourious/cache/
pkill -f main.py
pkill -f npm
sleep 10
python main.py
npm start

Prevention Tips

Keep updated: git pull regularly for bug fixes
Test in paper mode: Always test agents in paper mode first
Monitor regularly: Check agents daily initially
Backup regularly: Back up vault monthly
Document changes: Keep notes on what you change
Save logs: Before closing terminal, copy log output


Still stuck? Open a GitHub issue with full details, logs, and error messages. The community will help!
