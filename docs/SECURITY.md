Security & Privacy Guide
How Labourious protects your data, credentials, and trading activity.

Security Philosophy
Labourious follows security-first principles:

Local-first: All data stays on your machine
Encrypted: API keys are encrypted at rest (AES-256)
No cloud: Credentials never transmitted to external servers
Open-source: Code is auditable by security researchers
User control: You own and manage all credentials


Encryption Model
Vault Password
During setup, you create a vault password (8+ characters):
Vault Password
    ↓
PBKDF2 key derivation (100,000 iterations)
    ↓
Encryption key (256-bit)
    ↓
Used to encrypt all API keys
Important:

Vault password is NOT stored anywhere
Cannot be recovered if forgotten
Required every time you start Labourious

API Key Encryption
API Key (plain text)
    ↓
AES-256 encryption (Fernet cipher)
    ↓
Encrypted blob stored in vault.db
Result:

vault.db file is encrypted
Worthless without vault password
Attacker who steals vault.db still can't access keys

Network Encryption
Labourious ──HTTPS/TLS──→ Broker APIs
                            (encrypted in transit)

Labourious ──localhost──→ Frontend
                            (not transmitted over network)

What's Encrypted vs Not
ENCRYPTED (At Rest)
✅ API keys (broker credentials)
✅ API secrets
✅ Private keys (for crypto)
✅ Vault password hash
✅ Encrypted backup file (user-controlled)
NOT ENCRYPTED (But Local-Only)
Trade history (SQLite DB)
Agent configurations
Log files
Market data cache
Why? These are local-only files, not transmitted. Encryption would slow down queries. If someone has local access to steal these, they already have access to much.
OPTIONAL OS-Level Encryption
If paranoid, encrypt entire ~/.labourious/ folder:
macOS:
bash# Use FileVault 2
System Preferences → Security & Privacy → FileVault
Windows:
bash# Use BitLocker
Settings → System → About → Device Encryption
Linux:
bash# Use LUKS
sudo cryptsetup luksFormat /dev/sdX

Vault Password Requirements
Minimum Requirements

8+ characters (longer is better)
Mix of uppercase and lowercase (A-Z, a-z)
At least one number (0-9)
At least one special character (!@#$%^&*)
NOT your broker password (separate credential)

Examples - Good ✅
MyLabourious#2024
Trading$Rules99
Crypto&Stocks!88
MyPassphrase#1234
Examples - Bad ❌
12345678           (no letters)
password           (no numbers/symbols)
MyPassword         (no numbers/symbols)
BrokerPassword123  (reusing passwords)
Best Practices

Use unique password (not used anywhere else)
Make it memorable (or store safely in password manager)
Don't share it (not with anyone, including support)
Don't store in email (email is easily hacked)
Don't store in cloud (cloud storage is untrusted)
Write it down (in safe place like password manager)


Vault Password Recovery
If You Forget Vault Password
Option 1: Use Encrypted Backup
bashlabourious restore-vault --backup ~/.labourious/keys/backup.enc
Then set a new vault password.
Option 2: Reset and Re-enter Credentials
bash# Stop Labourious
# Delete vault.db
rm ~/.labourious/vault.db

# Restart Labourious
# Run setup.py
python setup.py

# Re-enter all broker credentials
Best Practice: Test recovery process once (so you know it works)
Encrypted Backup File
During setup, Labourious creates ~/.labourious/keys/backup.enc
This file:

Contains encrypted vault data
Can be used to recover credentials if vault is lost
Should be stored somewhere safe:

External drive (USB stick)
Password-protected cloud storage (Tresorit, Sync.com)
NOT email, NOT regular cloud (Dropbox)




API Key Management
Creating API Keys
Best Practice: Separate keys for each application
Don't:
One API key used by:
  - Labourious
  - Other trading app
  - Spreadsheet
  - Phone app
Do:
Separate API keys:
  - API key #1 for Labourious
  - API key #2 for other app
  - API key #3 for spreadsheet
Why? If one key is compromised, only that one app is affected.
Permissions
Always use MINIMUM required permissions
For Labourious (read/write):
✅ View balances
✅ View orders
✅ Place orders
✅ Cancel orders
❌ Transfer funds
❌ Edit settings
❌ Access all accounts
For testing/learning (read-only):
✅ View balances
✅ View orders
❌ Place orders
❌ Transfer funds
Rotation Schedule
FrequencyReasonEvery 6 monthsSecurity best practiceImmediatelyIf you suspect compromiseImmediatelyIf shared accidentallyImmediatelyIf system was hacked
Rotation process:

Create new API key on broker
Copy new key to Labourious vault
Test new key works
Delete old API key on broker
Done!


If Your Credentials Are Compromised
Immediate Actions (First 5 Minutes)

Stop trading - Pause all agents in Labourious
Verify - Log into broker directly, check for unauthorized trades
Revoke - Immediately delete compromised API key on broker
Create - Generate new API key on broker
Update - Update Labourious with new key

Investigation (Next Hour)

Check account - Review all trades for fraud
Check logs - Review Labourious logs for suspicious activity
Contact broker - If unauthorized trades found
Document - Screenshot evidence of unauthorized trades

Cleanup (Same Day)

Rotate other keys - If other apps used same key
Change vault password - In Labourious Settings
Create backup - New encrypted vault backup
Monitor - Watch account for suspicious activity next 2 weeks

Recovery
Most brokers will:

Reverse unauthorized trades within 48 hours
Refund any losses from fraud
Document the incident in your account


Privacy: What Data Does Labourious Collect?
LOCAL DATA (Stays on Your Machine)

All trade history
All agent configurations
All market data (cached locally)
All logs
Your vault password derivative

These are NEVER sent anywhere.
NO DATA SENT TO CLOUD
✅ No trade data sent to Labourious team
✅ No API keys sent anywhere
✅ No personal information sent anywhere
✅ No usage analytics or tracking
✅ No telemetry or phone-home
✅ No data selling
✅ No ads
✅ No targeted advertising
EXCEPTION: Optional Cloud LLM
If you switch from local Ollama to Claude or GPT:
Your market data + context file
    ↓
Sent to Claude/OpenAI servers (encrypted)
    ↓
LLM processes and returns decision
Important:

Claude and OpenAI are in US (GDPR concerns possible)
Read their privacy policies before using
Data is encrypted in transit
We NEVER see this data (encrypted directly)

Broker Data
Brokers see:

Your trades (required to execute)
Your account activity
Your positions

This is unavoidable and necessary. Read broker privacy policies.

Multi-User Security (Shared Machine)
If multiple people use same machine:
DO:
✅ Each person has separate OS account
✅ Each person runs own Labourious setup
✅ Each person has unique vault password
✅ Each person connects own broker accounts
DON'T:
❌ Share vault password
❌ Share broker credentials
❌ Run same Labourious instance for multiple people
Setup Example:
User 1:
  OS account: user1
  ~/.labourious/ folder: /home/user1/.labourious
  Vault password: MyPassword#1

User 2:
  OS account: user2
  ~/.labourious/ folder: /home/user2/.labourious
  Vault password: MyPassword#2
Each has separate encrypted vault.

Open Source Security
Labourious is open-source on GitHub.
Benefits:
✅ Anyone can read the code
✅ Security researchers can audit encryption
✅ Bugs found and fixed quickly
✅ Community can verify no backdoors
✅ No hidden malicious code possible
For Users:

Review backend/vault/encrypted_vault.py to see encryption
Review backend/database/models.py to see what's stored
Run security scanning tools on source code
Trust comes from transparency, not obscurity

For Developers:

Never hardcode secrets
Don't log sensitive data
Use battle-tested crypto libraries
Regular dependency updates
Security-focused code reviews


Common Security Mistakes
Mistake 1: Storing API Key in .env File
❌ WRONG:
.env file contains:
API_KEY=abc123xyz
API_SECRET=secret789
✅ RIGHT:
.env file is empty
Keys stored ONLY in Labourious vault
Why: .env files are often accidentally committed to git, shared, or backed up insecurely.

Mistake 2: Asking for Help with Real API Key
❌ WRONG:
"My API key is XYZ123ABC, why doesn't it work?"
✅ RIGHT:
"I'm getting 'invalid signature' error, API key is stored correctly,
what could be wrong?"
Why: Anyone who reads the answer also sees your API key.

Mistake 3: Weak Vault Password
❌ WRONG:
Vault password: "password123"
✅ RIGHT:
Vault password: "MyLabourious#2024$Trading"

Mistake 4: Never Backing Up Vault
❌ WRONG:
Never back up vault
Forget vault password
Lose all credentials
✅ RIGHT:
Back up encrypted vault monthly
Store backup.enc somewhere safe
Test recovery process once

Mistake 5: Running on Untrusted Network
❌ WRONG:
Running Labourious on public WiFi at coffee shop
Credentials transmitted in plaintext
Attacker on same network steals keys
✅ RIGHT:
Running on home network (trusted)
Or using VPN on public network
Credentials never transmitted over network

Mistake 6: Sharing API Key Between Apps
❌ WRONG:
One API key used by:
  - Labourious
  - Other trading app
  - Browser extension
  - Phone app
If any one is compromised, all are compromised.
✅ RIGHT:
Separate API key for each app
If one compromised, others unaffected

Mistake 7: Not Rotating Keys
❌ WRONG:
Same API key for 2+ years
✅ RIGHT:
Rotate every 6 months
Immediately if suspected compromise

Incident Response Plan
Scenario 1: Forgot Vault Password
→ Use backup.enc file to restore
→ Or delete vault.db and re-enter credentials
Scenario 2: API Key Compromised
→ Revoke API key immediately on broker website
→ Create new API key
→ Update Labourious
→ Check account for unauthorized trades
Scenario 3: Labourious Crashed with Credentials Exposed
→ Kill the process immediately
→ Check logs for what was exposed
→ Rotate API keys if needed
Scenario 4: Machine was Stolen
→ Revoke all API keys immediately (from another device)
→ Change vault password (not needed, key is lost anyway)
→ All data on machine is encrypted, attacker can't access
Scenario 5: Suspect Malware
→ Run antivirus scan
→ If malware found, revoke all API keys
→ Rotate all passwords
→ Check broker account for unauthorized activity

Security Checklist
Before going live with real money:

 Vault password is 8+ characters with mixed case/numbers/symbols
 Encrypted backup created and stored safely
 API keys have minimum required permissions
 Separate API keys for Labourious and other apps
 2FA enabled on broker account
 Firewall rules allow localhost only
 Started with paper trading first
 Position sizes are limited (max 2-5% per trade)
 Stop losses are set on all agents
 Account drawdown limits are set
 Monitoring plan created (daily/weekly reviews)
 Emergency contact info for broker saved


Regulatory & Legal
Not Legal Advice
Labourious is a tool for trading. It does not provide:

Financial advice
Investment recommendations
Tax advice
Legal advice

You are responsible for:

Compliance with local laws
Tax reporting of trades
Risk management
Understanding strategies before using

Jurisdictions
Check local laws for:

Cryptocurrency trading rules
Automated trading restrictions
Broker account requirements
Tax reporting requirements


Third-Party Audits
Labourious security model has been reviewed by:

[List any independent security audits here]
Community security researchers
Open-source security tools

Note: No system is 100% secure. This system is designed to be very secure for the use case.

Reporting Security Issues
If you find a security vulnerability:

DO NOT post on GitHub issues (public)
DO email security@labourious.dev with details
DO include proof-of-concept if safe
DO allow 30 days for fix before public disclosure

We take security seriously and will respond promptly.

Further Reading

BROKERS.md - Broker-specific security practices
SETUP.md - Security setup during installation
TROUBLESHOOTING.md - Security troubleshooting
ARCHITECTURE.md - Technical encryption details
