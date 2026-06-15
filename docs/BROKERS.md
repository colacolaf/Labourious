Broker Integration Guide
Setup instructions and best practices for all Labourious-supported brokers.

Broker Overview
Labourious supports multiple brokers for different asset classes:
BrokerAssetsDifficultyCostInteractive BrokersStocks, Options, FuturesMediumMonthly feeKrakenCrypto (BTC, ETH, Altcoins)EasyFee per tradeCoinbaseCrypto (BTC, ETH, limited coins)EasyFee per trade

Interactive Brokers (Stocks, Options, Futures)
What You Can Trade

US and international stocks
Options (equity and index)
Futures (commodities, indices, crypto)
Bonds and fixed income
NOT: Crypto directly

Account Setup
Step 1: Open Account

Visit www.interactivebrokers.com
Click "Open Account"
Choose "Individual" or "Joint"
Complete application (1-2 days)
Fund account

Step 2: Install IB Gateway

Download IB Gateway from IB website
Install on your machine
IB Gateway is lighter than TWS (recommended)
After installation, start IB Gateway
Log in with your IB username and password

Step 3: Enable API

Log into www.ibclient.com
Go to Account Management → Settings
Look for "API" section
Enable "Enable ActiveX and Socket Clients"
Note the settings

Step 4: Get Credentials
From IB Gateway/TWS settings you'll see:

Account ID (e.g., U1234567)
User ID (e.g., edemo)
Master account password

These are needed for Labourious.
Labourious Setup
During Setup Wizard:
Broker: Interactive Brokers
Account ID: U1234567
Server: 127.0.0.1:7497 (default, don't change)
Or in Settings:

Click "Add Broker"
Select "Interactive Brokers"
Enter account ID
Test connection

Verification

Start IB Gateway on your machine
In Labourious, click "Test Connection"
Should show: "✅ Connected to IB - Balance: $[amount]"

Troubleshooting
Error: "Connection refused 127.0.0.1:7497"

IB Gateway is not running
Start IB Gateway first

Error: "API not enabled"

Log into ibclient.com
Go to Account Management → Settings
Enable API

Error: "Account locked"

Too many failed login attempts
Wait 15 minutes before trying again

Trades not executing

Check account has buying power (cash)
Check market is open (not weekend, 4pm-9:30am EST)
Check position size isn't too large

Permissions & Modes
Read-Only API (Safe, for paper trading):

Can view balances and positions
Cannot place or execute trades
Cannot modify orders

Full API (Needed for live trading):

Can view and execute everything
Can place, modify, and cancel orders
More powerful, more risk

Paper vs Live
IB provides separate paper and live accounts:
Paper Trading Account:

Starting balance: Usually $1 million virtual
No real money needed
Good for learning
Limited to one paper account

Live Trading Account:

Uses your real funds
Real trades execute
Commissions apply
Can have multiple live accounts

To switch between paper and live in Labourious:

In Settings, edit agent config
Change paper_trading: true/false
Select which account to use


Kraken (Cryptocurrency)
What You Can Trade

Bitcoin, Ethereum, Litecoin, Ripple, altcoins
Spot trading (buy and hold)
Futures trading (advanced, not MVP)
NOT: Stocks or traditional assets

Account Setup
Step 1: Create Account

Go to www.kraken.com
Sign up with email
Verify email
Enable 2-Factor Authentication (required!)

Use authenticator app (Google Authenticator, Authy)
Not SMS (less secure)


Complete identity verification (KYC)
Fund account

Step 2: Enable API Access

Log into Kraken
Click Settings (gear icon)
Click "API"
Click "Generate New Key"

Step 3: Configure Permissions
CRITICAL: Set correct permissions
✅ ENABLE THESE:

Query Funds (view balance)
Query Orders (view orders)
Query Trades (view trades)
Query Open Orders & Trades
Create & Modify Orders
Cancel/Close Orders

❌ DO NOT ENABLE:

Access Ledger Query (unnecessary)
Edit Settings (dangerous)
Withdraw Funds (dangerous)

Step 4: Get Credentials

You'll see:

API Key (copy and save safely)
Private Key (click "Show", copy and save safely)


Store these securely (treat like passwords!)
Can only view private key once

Labourious Setup
During Setup Wizard:
Broker: Kraken
API Key: [paste from above]
Private Key: [paste from above]
2FA Code: [only if you have 2FA enabled]
Or in Settings:

Click "Add Broker"
Select "Kraken"
Paste API key and private key
If 2FA enabled, enter code
Test connection

Verification
In Labourious:

Click "Test Connection"
Should show: "✅ Connected to Kraken - Balance: $[amount]"

Troubleshooting
Error: "Invalid API key"

Double-check you copied the key exactly
No extra spaces before/after
Kraken keys are case-sensitive!

Error: "Invalid signature"

Private key is incorrect
Check you copied the FULL private key
Keys are very long, check entire thing

Error: "2FA required"

You have 2FA enabled on account
Enter the code from your authenticator app
Or disable 2FA (less secure)

Error: "Insufficient funds"

Account balance too low for trade
Deposit more crypto or funds

Security Best Practices

Create separate API key just for Labourious
Use minimum required permissions
Never share API key or private key
Store keys ONLY in Labourious vault
Rotate keys every 6 months

Recovery
If you forget API key:

Log into Kraken
Go to Settings → API
Revoke old key
Generate new key
Update Labourious


Coinbase (Cryptocurrency)
What You Can Trade

Bitcoin, Ethereum, Dogecoin
Select altcoins
Spot trading only (buy and hold)
Requires: Coinbase Advanced account (not regular Coinbase)

Account Setup
Step 1: Create Account

Go to www.coinbase.com
Sign up with email
Complete identity verification (KYC)
Enable 2-factor authentication (optional but recommended)

Step 2: Upgrade to Coinbase Advanced

This is different from regular Coinbase
Go to Settings → Accounts
Look for "Advanced Trading" or "Pro Trading"
Upgrade (may require minimum balance)

Step 3: Enable API Access

In Advanced settings, click "Create API Key"
Or go to Settings → Developers → API Access

Step 4: Configure Permissions
✅ ENABLE:

View account balances
View account transactions
Place orders
Cancel orders

❌ DO NOT ENABLE:

Transfer funds
Edit account settings

Step 5: Get Credentials
You'll see three credentials (Coinbase is unique):

API Key
API Secret
API Passphrase (unique to Coinbase!)

Copy all three and save safely.
Labourious Setup
During Setup Wizard:
Broker: Coinbase
API Key: [paste]
API Secret: [paste]
API Passphrase: [paste]
Or in Settings:

Click "Add Broker"
Select "Coinbase"
Paste all three credentials
Test connection

Verification
In Labourious:

Click "Test Connection"
Should show: "✅ Connected to Coinbase - Balance: $[amount]"

Troubleshooting
Error: "Invalid API key"

Check you copied the key exactly
No extra spaces
Keys are case-sensitive

Error: "Invalid signature"

Wrong API secret or passphrase
Coinbase requires all three credentials
Check for typos

Error: "Account not authorized for Advanced Trading"

Need to upgrade to Coinbase Advanced
May require minimum account balance
Contact Coinbase support

Security Best Practices

Create separate API key just for Labourious
Passphrase is unique to Coinbase (not used elsewhere)
Store all three credentials safely
Never share credentials
Rotate keys every 6 months


Broker Comparison
FeatureIBKrakenCoinbaseSetup DifficultyMediumEasyEasyAccount MinimumVariesNoneNoneAPI QualityExcellentGoodGoodTrading PairsN/A50+ cryptos20+ cryptosFeesCommission-based% fee per trade% fee per tradePaper TradingYes (separate account)LimitedLimited2FA RequiredNoRecommendedOptionalWithdrawalEasyEasyEasy

API Key Best Practices (All Brokers)
DO:
✅ Create separate API key for each application
✅ Create separate API key just for Labourious
✅ Use MINIMUM permissions (not "admin")
✅ Store keys ONLY in Labourious encrypted vault
✅ Enable 2FA on broker account (extra security)
✅ Rotate keys every 6 months
✅ Review trades monthly for unusual activity
DON'T:
❌ Share API key with anyone
❌ Store API key in plain text files
❌ Store API key in cloud storage (Dropbox, Google Drive)
❌ Store API key in email
❌ Give "admin" or "all permissions"
❌ Use same API key for multiple machines
❌ Paste API key into untrusted websites
❌ Log API keys in error messages
If Compromised:

Immediately log into broker website
Revoke the compromised API key
Create new API key
Update Labourious with new key
Check broker account for unauthorized trades
Contact broker support if fraud occurred


Using Multiple Brokers
You can use multiple brokers simultaneously:
Setup:

Connect first broker (e.g., IB for stocks)
Create agents for stocks
Click "Add Broker" in Settings
Connect second broker (e.g., Kraken for crypto)
Create agents for crypto
Allocate capital between brokers

Each Agent Trades on One Broker:

Agent config specifies which broker to use
Can have agents on different brokers simultaneously
Allocate capital separately for each broker

Example Portfolio:
Interactive Brokers (Stocks):
  - Stock Picker Agent: $50,000
  - Sector Traders: $30,000
  Total: $80,000

Kraken (Crypto):
  - BTC Momentum Trader: $15,000
  - ETH Swing Trader: $5,000
  Total: $20,000

Overall: $100,000

Switching Brokers
To switch from one broker to another:

Backup your current setup and trades
New Broker: Connect via Settings → Add Broker
New Agents: Create agents for new broker
Paper Trade: Test on new broker first
Transfer Funds: Move capital to new broker
Update Agents: Point agents to new broker
Test: Verify agents work on new broker
Old Broker: Can disconnect after transition


Troubleshooting Checklist
Before contacting support:

 Is market open? (Stocks: 9:30am-4pm EST, Crypto: 24/7)
 Do I have enough buying power?
 Have I tested connection in Labourious settings?
 Are credentials encrypted in vault?
 Have I enabled API on broker account?
 Is firewall blocking connection?
 Have I restarted Labourious?
 For IB: Is IB Gateway running?
 For Kraken: Did I copy API key correctly (case-sensitive)?
 For Coinbase: Did I enter all three credentials?


Fees & Costs
Interactive Brokers

Stocks: $1-2 per trade (or 0.002% per share)
Options: $0.65 per contract
Futures: $2-3 per contract
Account fee: None if active, $10/month if inactive

Kraken

Maker fee: 0.16% (you add liquidity)
Taker fee: 0.26% (you take liquidity)
Staking: Additional rewards (optional)

Coinbase

Maker fee: 0.4-0.6%
Taker fee: 0.4-0.6%
Advanced (lower fees if high volume)


Account Minimums
BrokerMinimumNotesInteractive Brokers$2,000Waived for agents <25Kraken$0Can start with any amountCoinbase$0Can start with any amount

Regulatory Notes

US Traders: All three brokers comply with FINRA and SEC regulations
International Traders: Kraken and Coinbase available in most countries; IB varies
Pattern Day Trader Rule: Stocks (IB) only - need $25k to day trade frequently
Crypto: Unregulated in many jurisdictions; check your local laws


Getting Help
For broker-specific issues:

Check broker's documentation
Contact broker support directly
Check Labourious GitHub issues for similar problems

For Labourious integration issues:

Review TROUBLESHOOTING.md
Check broker is working (test in broker's app)
Verify Labourious can connect to broker
Open GitHub issue with details


Recommended Setup for Beginners

Start with 1 broker (Kraken if crypto, IB if stocks)
Paper trade first (2-4 weeks minimum)
Small position sizes (1-2% per trade)
Daily monitoring (check agents once per day)
Monthly review (assess strategy, adjust if needed)
Add more brokers later (once confident)


Ready to connect a broker? Follow the step-by-step guide above for your chosen broker, then continue with SETUP.md setup wizard.
