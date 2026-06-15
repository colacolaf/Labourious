LABOURIOUS PHASE 1: COMPLETE DOCUMENTATION PACKAGE
All missing documents for MVP (v1.0) in one file
Version: 1.0

Last Updated: June 2026

Status: Ready for Implementation

TABLE OF CONTENTS

CONTRIBUTING.md
TESTING_GUIDE.md
DEPLOYMENT.md
GLOSSARY.md
PERFORMANCE_TUNING.md


<a name="contributing"></a>
CONTRIBUTING.md
Contributing to Labourious
Thanks for your interest in contributing! Labourious is open-source and welcomes contributions from developers, traders, and community members.
Types of Contributions
Code Contributions:

Bug fixes (open GitHub issue first, then PR)
New features (discuss in issues before implementing)
Performance improvements
New broker integrations
LLM provider additions
UI/UX improvements

Content Contributions:

Trading rule examples (context files)
Agent templates
Documentation improvements
Translations
Video tutorials (links to videos)

Community Contributions:

Answering questions in issues/discussions
Bug reports with reproduction steps
Feature requests with use cases
User testimonials

Getting Started
1. Development Environment Setup
Prerequisites:

Git (https://git-scm.com/)
Python 3.9+ (https://www.python.org/)
Node.js 16+ (https://nodejs.org/)
Docker (optional, https://docker.com)

Clone & Setup:
bash# Clone repository
git clone https://github.com/yourusername/labourious.git
cd labourious

# Backend setup
python3 -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate (Windows)
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt  # Testing, linting

# Frontend setup
cd frontend
npm install
cd ..

# Verify installation
python verify_install.py
Optional: Docker Setup
bashdocker build -t labourious:dev -f docker/Dockerfile.dev .
docker-compose -f docker-compose.dev.yml up
2. Local Development Workflow
Start Backend (Terminal 1):
bashsource venv/bin/activate
python backend/main.py
# Runs on http://localhost:8000
# Logs show API requests and agent activity
Start Frontend (Terminal 2):
bashcd frontend
npm start
# Runs on http://localhost:3000
# Hot reload on file changes
Start Ollama (Terminal 3, optional):
bashollama serve
# Runs on http://localhost:11434
Run Tests (Terminal 4):
bash# Backend tests
pytest backend/tests/ -v

# Frontend tests
cd frontend && npm test
Code Style Guide
Python (Backend)
Style: PEP 8 with Black formatter
Installation:
bashpip install black flake8 isort mypy
Before committing:
bash# Format code
black backend/

# Check imports
isort backend/

# Lint
flake8 backend/

# Type checking
mypy backend/
Python style rules:

Max line length: 100 characters
Use type hints for functions
Docstrings for all public functions (Google format)
Async functions for I/O operations
Error handling with specific exceptions

Example:
pythonasync def place_order(
    self,
    symbol: str,
    side: str,
    quantity: float
) -> Dict[str, Any]:
    """
    Place market order with broker.
    
    Args:
        symbol: Trading pair (e.g., 'BTC/USD')
        side: 'BUY' or 'SELL'
        quantity: Order quantity
    
    Returns:
        Order response with order_id and status
    
    Raises:
        InsufficientFundsError: Account lacks buying power
        InvalidSymbolError: Symbol not supported by broker
        ConnectionError: Broker API unreachable
    """
    # Implementation
    pass
JavaScript/React (Frontend)
Style: ESLint + Prettier
Installation:
bashcd frontend
npm install --save-dev eslint prettier @typescript-eslint/parser
Before committing:
bash# Format code
npx prettier --write src/

# Lint
npx eslint src/
JavaScript style rules:

Max line length: 100 characters
Use const/let, avoid var
Arrow functions for callbacks
Functional components with hooks
Props destructuring
Meaningful variable names

Example:
javascript// Good
const AgentCard = ({ agent, onSelect }) => {
  const [isHovered, setIsHovered] = useState(false);
  
  return (
    <div
      className="agent-card"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={() => onSelect(agent.id)}
    >
      {agent.name}
    </div>
  );
};

// Bad
var AgentCard = function(props) {
  // ...
}
Git Workflow
Branch Naming
feature/description       # New feature
bugfix/issue-number       # Bug fix (reference issue)
docs/what-docs           # Documentation
refactor/what-refactor   # Code cleanup
test/what-test          # Test improvements
chore/what-chore        # Maintenance
Examples:
feature/kraken-integration
bugfix/issue-42-vault-encryption
docs/agent-creation-guide
refactor/llm-router-cleanup
test/increase-api-coverage
Commit Messages
Format:
<type>(<scope>): <subject>

<body>

<footer>
Types: feature, fix, docs, test, refactor, chore, perf
Examples:
feature(broker): Add Alpaca integration
  - Implement AlpacaConnector class
  - Add market data fetching
  - Add order placement
  
Closes #123

fix(vault): Correct decryption timeout
  - Increase PBKDF2 iterations to 100k
  - Add retry logic for slow systems
  
Fixes #456

docs(agent-creation): Update examples
  - Add momentum trading example
  - Fix RSI variable documentation
Guidelines:

Keep subject line < 50 characters
Use imperative mood ("add" not "added")
Reference issues/PRs (#123, Closes #456)
Explain why, not what

Pull Request Process

Create feature branch:

bash   git checkout -b feature/my-feature

Make changes:

Small, focused commits
Follow code style guide
Add tests for new code
Update documentation


Push & create PR:

bash   git push origin feature/my-feature

Go to GitHub → Create Pull Request
Fill out PR template completely


PR Template:

markdown   ## Description
   What does this PR do?
   
   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Documentation
   - [ ] Performance improvement
   
   ## Testing Done
   - [ ] Unit tests pass
   - [ ] Integration tests pass
   - [ ] Manual testing completed
   
   ## Related Issues
   Closes #123
   
   ## Screenshots (if UI change)
   [Screenshot or GIF]
   
   ## Checklist
   - [ ] Code follows style guide
   - [ ] Documentation updated
   - [ ] No new warnings
   - [ ] Tests added/updated

Code Review:

Maintainers review code
Address feedback
Push updates (don't force-push)


Merge:

Squash commits for small changes
Keep history for large features
Delete branch after merge



Testing Requirements
Before submitting PR, ensure:

All existing tests pass:

bash   pytest backend/tests/
   cd frontend && npm test

New code has tests (minimum 80% coverage):

bash   pytest backend/tests/ --cov=backend

No linting errors:

bash   black --check backend/
   flake8 backend/
   npx eslint frontend/src/

Manual testing (if applicable):

Paper trading works
Broker connection works
Encryption/decryption works
UI renders correctly



See TESTING_GUIDE.md for detailed testing procedures.
Adding a New Broker
Step 1: Create connector class
python# backend/brokers/new_broker.py

from .base_broker import BrokerConnector

class NewBrokerConnector(BrokerConnector):
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        # Initialize API client
    
    async def get_account_balance(self) -> float:
        # Implementation
        pass
    
    async def place_order(self, symbol: str, side: str, quantity: float) -> Dict:
        # Implementation
        pass
    
    # Implement all required abstract methods
Step 2: Register broker
python# backend/brokers/manager.py

BROKERS = {
    'interactive_brokers': IBConnector,
    'kraken': KrakenConnector,
    'coinbase': CoinbaseConnector,
    'new_broker': NewBrokerConnector,  # Add here
}
Step 3: Add tests
python# backend/tests/test_new_broker.py

def test_connection():
    connector = NewBrokerConnector(api_key='test', api_secret='test')
    # Mock API responses
    # Assert connection works

def test_place_order():
    # Test order placement
    pass

def test_get_balance():
    # Test balance retrieval
    pass
Step 4: Update documentation

Add to BROKERS.md
Add setup instructions
Add example configuration

Adding a New LLM Provider
Step 1: Create LLM adapter
python# backend/llm/new_llm.py

class NewLLMAdapter:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
    
    async def decide(self, prompt: str) -> str:
        """Send prompt to LLM, return decision"""
        # Implementation
        pass
Step 2: Register in router
python# backend/llm/llm_router.py

async def decide(self, market_data, context, agent):
    if agent.llm_provider == 'new_llm':
        return await self.call_new_llm(prompt)
    # ... other providers
Step 3: Add configuration
json{
  "llm_config": {
    "provider": "new_llm",
    "api_key": "your_key",
    "model": "model_name",
    "temperature": 0.7
  }
}
Step 4: Test integration

Ensure prompt parsing works
Verify response formatting
Test error handling

Feature Request Process

Check existing issues (don't duplicate)
Create GitHub issue with:

Clear title
Use case description
Why it's important
Potential implementation approach


Discussion with maintainers
Approval before implementation
Implementation with tests
Documentation updates

Reporting Bugs

Gather information:

OS and version
Python/Node version
Error message (full traceback)
Steps to reproduce
Logs from ~/.labourious/logs/


Search existing issues (don't duplicate)
Create GitHub issue with:

Clear title describing the bug
Expected vs actual behavior
Steps to reproduce
Screenshots/logs
System information


Example:

markdown   ## Bug: Vault password not persisting

   ### Environment
   - OS: macOS 14.2
   - Python: 3.11.0
   - Labourious: v1.0.0

   ### Steps to Reproduce
   1. Run setup.py
   2. Enter vault password
   3. Restart Labourious
   4. Vault password is forgotten

   ### Error
   [Paste full error message here]

   ### Expected
   Vault password should persist across restarts

   ### Logs
   [Paste relevant logs]
Communication
Where to ask questions:

GitHub Discussions (preferred)
GitHub Issues (for bugs)
Discord (if community exists)
Email (security issues only)

Be respectful:

Follow code of conduct
Be patient with maintainers
Give context for questions
Provide reproducible examples

Documentation Contributing
Update docs when:

Adding new features
Fixing bugs (if docs are wrong)
Improving clarity
Adding examples

Documentation format:

Use Markdown
Keep line length < 100 chars
Use code blocks for examples
Include table of contents for long docs
Update all related docs

Example:
markdown## Feature Name

What it does, one sentence.

### How It Works

Explanation of the mechanism.

### Configuration

```json
{
  "setting": "value"
}
```

### Example

[Complete, runnable example]

### Troubleshooting

Common issues and solutions.
Release Process
Version numbering: Semantic versioning (MAJOR.MINOR.PATCH)

MAJOR: Breaking changes
MINOR: New features
PATCH: Bug fixes

Release checklist:

 All tests passing
 Documentation updated
 CHANGELOG.md updated
 Version bumped in package.json and setup.py
 GitHub release created
 Release notes written

Questions?

Read existing documentation
Search GitHub issues
Ask in GitHub Discussions
Email maintainers


<a name="testing"></a>
TESTING_GUIDE.md
Testing Strategy for Labourious
Labourious uses a multi-layered testing approach: unit tests, integration tests, and end-to-end tests.
Test Setup
Backend Testing (Python)
Installation:
bashpip install -r backend/requirements-dev.txt
# Includes: pytest, pytest-asyncio, pytest-cov, pytest-mock
Configuration (pytest.ini):
ini[pytest]
testpaths = backend/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
Running tests:
bash# Run all tests
pytest

# Run specific test file
pytest backend/tests/test_agents.py

# Run specific test
pytest backend/tests/test_agents.py::test_agent_creation

# Run with coverage
pytest --cov=backend --cov-report=html

# Run in parallel (faster)
pytest -n auto

# Run with verbose output
pytest -v

# Run only fast tests (skip slow)
pytest -m "not slow"
Frontend Testing (JavaScript)
Installation:
bashcd frontend
npm install --save-dev jest @testing-library/react @testing-library/jest-dom
Configuration (jest.config.js):
javascriptmodule.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.js'],
  moduleNameMapper: {
    '\\.(css|less|scss)$': 'identity-obj-proxy',
  },
  collectCoverageFrom: [
    'src/**/*.{js,jsx}',
    '!src/index.js',
    '!src/electron-main.js',
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
};
Running tests:
bash# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Run in watch mode (re-run on changes)
npm test -- --watch

# Run specific test file
npm test Warroom

# Run tests matching pattern
npm test -- --testNamePattern="agent"
Test Types
1. Unit Tests
Purpose: Test individual functions in isolation
Backend example:
python# backend/tests/test_encryption.py

import pytest
from backend.vault.encrypted_vault import EncryptedVault

def test_vault_encrypt_decrypt():
    """Test encryption and decryption"""
    vault = EncryptedVault('TestPassword#123')
    original = 'my-secret-api-key'
    
    encrypted = vault.encrypt(original)
    assert encrypted != original  # Should be encrypted
    
    decrypted = vault.decrypt(encrypted)
    assert decrypted == original  # Should match original

def test_vault_wrong_password():
    """Test decryption with wrong password fails"""
    vault1 = EncryptedVault('Password#1')
    vault2 = EncryptedVault('Password#2')
    
    encrypted = vault1.encrypt('secret')
    
    with pytest.raises(ValueError):
        vault2.decrypt(encrypted)

def test_vault_weak_password():
    """Test weak password rejected"""
    with pytest.raises(ValueError):
        EncryptedVault('weak')  # Too short
Frontend example:
javascript// frontend/src/components/AgentCard.test.jsx

import { render, screen } from '@testing-library/react';
import AgentCard from './AgentCard';

describe('AgentCard', () => {
  const mockAgent = {
    id: 'agent1',
    name: 'Test Agent',
    p_and_l: 1000,
    status: 'active',
  };

  test('renders agent name', () => {
    render(<AgentCard agent={mockAgent} />);
    expect(screen.getByText('Test Agent')).toBeInTheDocument();
  });

  test('displays P&L correctly', () => {
    render(<AgentCard agent={mockAgent} />);
    expect(screen.getByText(/\+\$1,000/)).toBeInTheDocument();
  });

  test('shows active status indicator', () => {
    render(<AgentCard agent={mockAgent} />);
    expect(screen.getByTestId('status-active')).toBeInTheDocument();
  });
});
2. Integration Tests
Purpose: Test components working together
Backend example:
python# backend/tests/test_agent_execution.py

import pytest
from backend.orchestrator.agent_orchestrator import AgentOrchestrator
from backend.brokers.mock_broker import MockBroker

@pytest.mark.asyncio
async def test_agent_execution_flow():
    """Test complete agent execution: data → decision → trade"""
    orchestrator = AgentOrchestrator(vault=None)
    mock_broker = MockBroker()
    
    # Setup agent
    agent = {
        'id': 'test_agent',
        'context': 'BUY if price > 100',
        'broker': mock_broker,
    }
    
    # Mock market data
    market_data = {'price': 150, 'volume': 1000000}
    
    # Execute agent
    decision = await orchestrator.run_agent(agent, market_data)
    
    assert decision['action'] == 'BUY'
    assert decision['confidence'] > 0.5

@pytest.mark.asyncio
async def test_trade_execution_with_broker():
    """Test trade execution end-to-end"""
    broker = MockBroker()
    orchestrator = AgentOrchestrator(vault=None)
    
    # Place order
    order = await broker.place_order('BTC/USD', 'BUY', 0.5)
    
    assert order['status'] == 'filled'
    assert 'order_id' in order
Frontend example:
javascript// frontend/src/integration/warroom.test.jsx

import { render, screen, waitFor } from '@testing-library/react';
import Warroom from '../components/Warroom';
import { useAgentsStore } from '../stores/agents.store';

test('updates agent P&L when WebSocket message received', async () => {
  render(<Warroom room="day_trading" />);
  
  // Simulate WebSocket update
  const { updateAgent } = useAgentsStore.getState();
  updateAgent('agent1', { p_and_l: 5000 });
  
  await waitFor(() => {
    expect(screen.getByText(/\+\$5,000/)).toBeInTheDocument();
  });
});
3. End-to-End (E2E) Tests
Purpose: Test full user workflows
Tool: Playwright
Installation:
bashnpm install --save-dev @playwright/test
Example:
javascript// frontend/e2e/login-and-trade.spec.js

import { test, expect } from '@playwright/test';

test('complete trading workflow', async ({ page }) => {
  // 1. Start app
  await page.goto('http://localhost:3000');
  
  // 2. Navigate to warroom
  await page.click('button:has-text("Day Trading")');
  await expect(page).toHaveURL(/\/warroom\/day/);
  
  // 3. Click agent
  await page.click('[data-testid="agent-1"]');
  
  // 4. Inspector opens
  await expect(page.locator('.inspector-panel')).toBeVisible();
  
  // 5. Check agent P&L
  await expect(page.locator('.agent-pnl')).toContainText(/\+\$/);
  
  // 6. Close inspector
  await page.click('.inspector-close');
  await expect(page.locator('.inspector-panel')).toBeHidden();
});

test('approve trade in human-in-loop mode', async ({ page }) => {
  await page.goto('http://localhost:3000/warroom/day');
  
  // Wait for approval dialog
  await expect(page.locator('.approval-dialog')).toBeVisible();
  
  // Check trade details
  expect(await page.locator('.trade-symbol').textContent()).toBe('BTC/USD');
  
  // Approve
  await page.click('button:has-text("Approve")');
  
  // Verify trade executed
  await expect(page.locator('.notification')).toContainText('executed');
});
Running E2E tests:
bashnpx playwright test
npx playwright test --headed  # Show browser
npx playwright test --debug   # Step through
Test Coverage
Minimum coverage requirements:

Backend: 80% overall, 90% for critical (encryption, trading)
Frontend: 75% overall, 85% for critical (warroom, inspector)

Check coverage:
bash# Backend
pytest --cov=backend --cov-report=html
open htmlcov/index.html

# Frontend
npm test -- --coverage
open coverage/lcov-report/index.html
Critical modules (must test thoroughly):

backend/vault/encrypted_vault.py (100% coverage required)
backend/trading/trade_executor.py (95% coverage)
backend/llm/llm_router.py (90% coverage)
frontend/components/Warroom/Warroom.jsx (90% coverage)
frontend/components/AgentInspector/AgentInspector.jsx (85% coverage)

Mocking Strategies
Mocking Broker APIs
python# backend/tests/fixtures/mock_broker.py

from unittest.mock import AsyncMock, MagicMock

class MockBroker:
    def __init__(self):
        self.orders = []
    
    async def get_account_balance(self):
        return 100000.0
    
    async def place_order(self, symbol, side, quantity):
        order = {
            'order_id': f'mock_{len(self.orders)}',
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'status': 'filled',
        }
        self.orders.append(order)
        return order
    
    async def get_market_data(self, symbol):
        return {
            'price': 50000.0,
            'volume': 1000000,
            'rsi': 45.0,
            'macd': 0.5,
        }
Mocking LLM
python# backend/tests/fixtures/mock_llm.py

class MockLLM:
    async def decide(self, prompt):
        # Always return BUY for testing
        return {
            'action': 'BUY',
            'confidence': 0.85,
            'reason': 'Price above MA20',
            'position_size': 0.02,
        }
Mocking WebSocket
javascript// frontend/src/__mocks__/socket.js

export const socket = {
  on: jest.fn(),
  off: jest.fn(),
  emit: jest.fn(),
  disconnect: jest.fn(),
};
Performance Testing
Tool: k6 (for API load testing)
Installation:
bashbrew install k6  # macOS
# or download from https://k6.io/
Example test:
javascript// backend/performance/agent_load_test.js

import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 10,  // 10 virtual users
  duration: '30s',
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95th percentile < 500ms
    http_req_failed: ['rate<0.1'],      // Error rate < 10%
  },
};

export default function () {
  // Simulate multiple agents fetching data
  const res = http.get('http://localhost:8000/api/agents');
  
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
  
  sleep(1);
}
Run performance test:
bashk6 run backend/performance/agent_load_test.js
Security Testing
Tools: Bandit (for code), OWASP ZAP (for API)
Install Bandit:
bashpip install bandit
Scan for security issues:
bashbandit -r backend/
Check for common issues:
python# Don't do this:
password = input()  # Never trust user input
exec(user_code)     # Never execute user code

# Do this:
password = getpass.getpass()  # Use getpass
eval_result = ast.literal_eval(user_input)  # Safe parsing
CI/CD Integration
GitHub Actions workflow (.github/workflows/tests.yml):
yamlname: Tests

on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11']
    
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          python -m pip install -r backend/requirements.txt
          python -m pip install -r backend/requirements-dev.txt
      
      - name: Lint with flake8
        run: flake8 backend/
      
      - name: Test with pytest
        run: pytest backend/tests/ --cov
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
  
  frontend:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: cd frontend && npm ci
      
      - name: Lint
        run: cd frontend && npm run lint
      
      - name: Test
        run: cd frontend && npm test -- --coverage
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
Manual Testing Checklist
Before each release:

 Installation: Fresh install works (native, Docker, standalone)
 Setup wizard: All 5 steps complete successfully
 Broker connection: IB, Kraken, Coinbase all work
 Agent creation: Can create and upload custom agents
 Paper trading: Agent executes simulated trades
 Warroom UI: Agents display, animations smooth, inspector works
 Dashboard: P&L updates, charts render, trade history shows
 Notifications: Approvals prompt, trade notifications appear
 Settings: Can configure LLM, allocation, risk limits
 Encryption: Vault password required, API keys protected
 Error handling: Graceful failures, helpful error messages
 Performance: 10+ agents run without lag
 Cross-browser: Works in Chrome, Safari, Firefox

Troubleshooting Tests
Tests failing locally but pass in CI:

Clear cache: pytest --cache-clear
Check Python version: python --version
Rebuild dependencies: pip install --upgrade --force-reinstall -r requirements.txt

Flaky tests (sometimes fail):

Add pytest.mark.flaky(reruns=3) to unreliable tests
Increase timeouts for async tests
Check for timing issues (sleep, delays)

Tests running slow:

Use pytest -n auto for parallelization
Mark slow tests: @pytest.mark.slow
Skip slow tests in development: pytest -m "not slow"

Best Practices

Keep tests focused: One assertion per test (generally)
Use descriptive names: test_buy_when_rsi_oversold not test1
Mock external dependencies: Don't hit real APIs in tests
Test edge cases: Empty input, negative numbers, missing data
Use fixtures: Reusable test data setup
Clean up: Reset state after each test
Run locally first: Before pushing to GitHub
Document assumptions: Add comments explaining complex tests

Resources

Pytest docs: https://docs.pytest.org/
Jest docs: https://jestjs.io/
Playwright docs: https://playwright.dev/
Testing best practices: https://testingjavascript.com/


<a name="deployment"></a>
DEPLOYMENT.md
Deployment Guide for Labourious
Complete instructions for deploying Labourious in various environments.
Pre-Deployment Checklist

 All tests passing (backend and frontend)
 No security warnings from Bandit/ESLint
 Documentation updated
 CHANGELOG.md updated
 Version bumped (setup.py, package.json)
 Database schema verified
 API endpoints tested
 Broker integrations tested
 Encryption working
 Paper trading functional

Single Machine Deployment (Recommended for MVP)
Prerequisites

macOS 10.15+, Windows 10+, or Linux (Ubuntu 20.04+)
2GB RAM minimum, 4GB recommended
5GB disk space
Internet connection for initial setup

Installation Steps
1. Download Labourious
bashgit clone https://github.com/yourusername/labourious.git
cd labourious
2. Run Setup Wizard
bashpython setup.py
The wizard will:

Check dependencies
Create encrypted vault
Configure first broker
Set initial capital allocation
Run tutorial

3. Verify Installation
bashpython verify_install.py
Should show:

✅ Python 3.9+
✅ Node.js 16+
✅ Database initialized
✅ Broker connection working
✅ LLM responding
✅ Vault encrypted

Startup
Terminal 1 (Backend):
bashpython main.py
Terminal 2 (Frontend):
bashcd frontend && npm start
Access: http://localhost:3000
Stopping

Press Ctrl+C in each terminal
Graceful shutdown saves agent state

Backup & Recovery
Backup vault:
bashcp -r ~/.labourious/keys ~/.labourious-backup-$(date +%Y%m%d)
Backup database:
bashcp ~/.labourious/labourious.db ~/.labourious/labourious.db.backup
Restore:
bashcp ~/.labourious-backup-20240613/keys/* ~/.labourious/keys/
cp ~/.labourious/labourious.db.backup ~/.labourious/labourious.db
Docker Deployment
Prerequisites

Docker Desktop installed (https://docker.com/products/docker-desktop)
3GB disk space for image
2GB available RAM

Build Image
bashdocker build -t labourious:latest -f docker/Dockerfile .
Takes 2-3 minutes.
Run Container
bashdocker run -it \
  --name labourious \
  -p 3000:3000 \
  -p 8000:8000 \
  -v ~/labourious-data:/app/data \
  -v ~/.labourious-keys:/app/keys \
  labourious:latest
Port mapping:

3000: Frontend (React)
8000: Backend (FastAPI)

Volume mounts:

~/labourious-data: Trade history, logs, database
~/.labourious-keys: Encrypted vault (on host for security)

Docker Compose
Create docker-compose.yml:
yamlversion: '3.8'

services:
  labourious:
    image: labourious:latest
    container_name: labourious
    ports:
      - "3000:3000"
      - "8000:8000"
    volumes:
      - ~/labourious-data:/app/data
      - ~/.labourious-keys:/app/keys
      - /var/run/docker.sock:/var/run/docker.sock  # For Ollama
    environment:
      - LOCAL_LLM=true
      - OLLAMA_PORT=11434
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
    restart: unless-stopped

volumes:
  ollama-data:
Start services:
bashdocker-compose up -d
Stop services:
bashdocker-compose down
View logs:
bashdocker-compose logs -f labourious
Container Management
bash# Stop container
docker stop labourious

# Start container
docker start labourious

# Restart container
docker restart labourious

# Remove container (keeps data)
docker rm labourious

# View logs
docker logs labourious -f

# Enter shell
docker exec -it labourious bash
Kubernetes Deployment (Advanced)
Note: Recommended for organizations running 100+ agents.
Create deployment.yaml:
yamlapiVersion: apps/v1
kind: Deployment
metadata:
  name: labourious
spec:
  replicas: 1
  selector:
    matchLabels:
      app: labourious
  template:
    metadata:
      labels:
        app: labourious
    spec:
      containers:
      - name: labourious
        image: labourious:latest
        ports:
        - containerPort: 3000
          name: frontend
        - containerPort: 8000
          name: backend
        volumeMounts:
        - name: data
          mountPath: /app/data
        - name: keys
          mountPath: /app/keys
        livenessProbe:
          httpGet:
            path: /api/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "2000m"
            memory: "2Gi"
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: labourious-data
      - name: keys
        persistentVolumeClaim:
          claimName: labourious-keys
---
apiVersion: v1
kind: Service
metadata:
  name: labourious
spec:
  type: LoadBalancer
  ports:
  - name: frontend
    port: 3000
  - name: backend
    port: 8000
  selector:
    app: labourious
Deploy:
bashkubectl apply -f deployment.yaml
kubectl get pods
kubectl logs -f labourious-xxxxx
Remote Access Setup
Option 1: SSH Tunnel (Recommended)
From local machine:
bashssh -L 3000:localhost:3000 -L 8000:localhost:8000 user@remote-server
Then access: http://localhost:3000
Option 2: VPN

Set up VPN on server
Connect VPN from client
Access via local IP (192.168.x.x)

Option 3: Reverse Proxy (Nginx)
Install Nginx:
bashsudo apt-get install nginx
Configure (/etc/nginx/sites-enabled/labourious):
nginxupstream backend {
    server localhost:8000;
}

upstream frontend {
    server localhost:3000;
}

server {
    listen 443 ssl http2;
    server_name labourious.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
    }
    
    location /ws {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
    }
}
Reload Nginx:
bashsudo nginx -t
sudo systemctl reload nginx
Monitoring & Health Checks
Health Endpoint
bashcurl http://localhost:8000/api/health

# Response:
{
  "status": "healthy",
  "uptime_seconds": 3600,
  "version": "1.0.0",
  "agents_active": 5,
  "brokers_connected": 2,
  "database": "healthy"
}
Log Monitoring
Backend logs:
bashtail -f ~/.labourious/logs/labourious.log
Check for errors:
bashgrep ERROR ~/.labourious/logs/labourious.log
Alerts
Set up alerts for:

High CPU usage (>80%)
High memory usage (>1.5GB)
Database errors
Broker connection failures
Agent crashes

Database Management
Backup
bash# SQLite backup
sqlite3 ~/.labourious/labourious.db ".backup '/path/to/backup.db'"

# Or with tar
tar -czf labourious-backup-$(date +%Y%m%d).tar.gz ~/.labourious/
Restore
bashsqlite3 ~/.labourious/labourious.db ".restore '/path/to/backup.db'"
Optimization
bash# Analyze and optimize
sqlite3 ~/.labourious/labourious.db "ANALYZE; VACUUM;"
Environment Variables
Create .env file:
bash# LLM
LOCAL_LLM=true
OLLAMA_PORT=11434
OLLAMA_MODEL=mistral

# Backend
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
FRONTEND_PORT=3000
DEBUG=false

# Database
DB_PATH=./data/labourious.db

# Logging
LOG_LEVEL=INFO

# Trading
PAPER_TRADING=true

# Security
VAULT_PASSWORD=  # User sets during setup
Update Process
Update to new version:
bash# Stop running instance
pkill -f "python main.py"
pkill -f "npm start"

# Pull latest changes
git pull origin main

# Update dependencies
pip install -r backend/requirements.txt
cd frontend && npm install

# Run migrations if needed
python backend/migrations/run.py

# Restart
python main.py &
cd frontend && npm start &
Rollback if needed:
bashgit checkout <previous-tag>
pip install -r backend/requirements.txt
Troubleshooting Deployment
Port already in use:
bash# Find what's using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
export BACKEND_PORT=8001
python main.py
Connection refused:

Check backend is running
Check firewall rules
Check port forwarding (if remote)

Database locked:

Stop all instances
Check for stray processes
Restart

Out of memory:

Close unnecessary applications
Reduce number of agents
Increase swap space

Performance Optimization
For production:
bash# Enable compression in Nginx
gzip on;
gzip_min_length 1000;
gzip_types text/plain application/json;

# Increase file limits
ulimit -n 65536

# Enable TCP optimization
sysctl -w net.ipv4.tcp_tw_reuse=1

<a name="glossary"></a>
GLOSSARY.md
Labourious Glossary
Complete definitions of trading and technical terms used in Labourious.
Trading Terms
Agent
An autonomous AI system that automatically executes trades based on pre-defined rules (context files). Agents run on schedules (every 5 minutes to weekly) and can execute trades autonomously or with human approval.
Backtest
Testing a trading strategy on historical data to evaluate performance. Shows what would have happened if the strategy was run in the past.
Entry Signal
A condition that triggers a BUY order. Example: "Price breaks above 20-day moving average."
Exit Signal
A condition that closes a position. Examples: "Take profit at +15%," "Stop loss at -5%," "Sell when RSI > 70."
P&L (Profit and Loss)
The dollar amount gained or lost on a trade. Positive P&L = profit, negative = loss.
Example: Bought BTC at $45,000, sold at $46,800 = +$1,800 P&L
Position
A currently open trade. Example: "I have a long position in BTC/USD of 0.5 coins."
Position Size
The quantity of an asset in a trade. Can be expressed as:

Absolute: "Buy 0.5 BTC"
Percentage: "Allocate 2% of account capital"

Stop Loss
A price level at which a losing position is automatically sold to limit losses.
Example: Bought BTC at $45,000 with stop loss at $43,000 (-$2,000 = -4.4% loss limit)
Take Profit
A price level at which a winning position is automatically closed to lock in gains.
Example: Bought BTC at $45,000 with take profit at $48,000 (+$3,000 = +6.7% gain)
Win Rate
Percentage of trades that were profitable.
Example: 8 winning trades out of 12 total = 67% win rate
Sharpe Ratio
Measure of risk-adjusted returns. Higher is better.

< 0.5 = Poor risk-adjusted returns
0.5-1.0 = Acceptable
1.0-2.0 = Good


2.0 = Excellent



Maximum Drawdown
Largest peak-to-trough decline in portfolio value.
Example: Portfolio at $100k, drops to $85k = -15% max drawdown
Slippage
The difference between expected execution price and actual execution price, usually due to market movement.
Example: Place order to buy at $100, actually fills at $101 = 1% slippage
Market Order
Buy/sell immediately at current market price.
Limit Order
Buy/sell only at a specific price or better.
Example: "Buy BTC only if price is $45,000 or lower"
Volatility
How much an asset's price fluctuates. High volatility = bigger swings.
Momentum
Direction and speed of price movement. "Bullish momentum" = price rising quickly.
Mean Reversion
Theory that prices tend to return to their average after extreme moves.
Example: Stock down 20% might "mean revert" (bounce back up) toward average.
Arbitrage
Exploiting price differences between markets.
Example: BTC at $45,000 on Exchange A, $45,100 on Exchange B = arbitrage opportunity ($100 profit per coin if transaction costs < $100)
Paper Trading
Simulated trading with no real money at risk. Shows what agent WOULD do without risking capital.
Live Trading
Real trades with real money at risk.
Risk Management
Techniques to limit losses: stop losses, position sizing, diversification, drawdown limits.
Technical Terms
API Key
Unique identifier to authenticate with a service (broker, LLM provider).
Example: api_key=aB1cD2eF3gH4iJ5kL6mN7oP8
API Secret
Like a password for an API key. Must be kept secret.
Encryption
Converting data into unreadable code so only authorized people can decrypt it.
Labourious uses: AES-256 (military-grade encryption)
Vault
Encrypted storage for sensitive data (API keys, secrets).
Vault Password
User-created password that unlocks the vault. 8+ characters, mixed case, numbers, symbols.
Example: MyLabourious#2024
Context File
User-written file defining trading rules in plain English or JSON.
Example:
BUY if:
  - Price > 20-day moving average
  - RSI < 30
  - Volume > average

SELL if:
  - RSI > 70
  - Profit >= 15%
  - Loss <= -5%
LLM (Large Language Model)
AI system that understands text and can make decisions.
Examples: Claude (Anthropic), GPT-4 (OpenAI), Mistral (Ollama - local)
Ollama
Free, local LLM that runs on your computer. No API key needed.
WebSocket
Real-time bidirectional communication between app and server.
Used for: Live P&L updates, trade notifications, agent status changes.
REST API
Request-response protocol for communication between apps.
Used for: Fetching agent data, placing trades, updating settings.
Broker
Financial institution that executes trades.
Examples: Interactive Brokers (stocks), Kraken (crypto), Coinbase (crypto)
Broker Integration
Connecting Labourious to a specific broker's API.
Orchestration
Coordinating multiple agents to run on schedule.
Example: Agent 1 checks every 5 minutes, Agent 2 checks daily, all coordinated by orchestrator.
Thread Pool
Multiple workers processing tasks in parallel.
Used for: Running multiple agents simultaneously without blocking.
Backtesting
Running a strategy on historical data to see past performance.
Symbol Formats
Stock Tickers (Interactive Brokers)

AAPL (Apple)
MSFT (Microsoft)
TSLA (Tesla)
SPY (S&P 500 ETF)

Cryptocurrency Pairs (Kraken, Coinbase)

BTC/USD (Bitcoin to US Dollar)
ETH/USD (Ethereum to US Dollar)
XRP/USD (Ripple to US Dollar)

Format varies by broker:

IB: AAPL
Kraken: XBTUSDT (Bitcoin/Tether)
Coinbase: BTC-USD

Command Reference
Starting Services
bash# Backend
python main.py

# Frontend
npm start

# Ollama
ollama serve
Common Commands
bash# Run tests
pytest backend/tests/

# Check installation
python verify_install.py

# Backtest agent
labourious backtest agent.json --start=2024-01-01 --end=2024-06-30

# Manage vault
labourious manage-vault

# Export trades
labourious export-trades --format=csv
Acronyms
AcronymMeaningAPIApplication Programming InterfaceAESAdvanced Encryption StandardATRAverage True Range (volatility indicator)BTCBitcoinCSVComma-Separated ValuesETFExchange-Traded FundETHEthereumGUIGraphical User InterfaceHTTPSHyperText Transfer Protocol SecureLLMLarge Language ModelMACDMoving Average Convergence DivergenceP&LProfit and LossRESTRepresentational State TransferRSIRelative Strength IndexSQLStructured Query LanguageUSBUniversal Serial BusUSDUS DollarVPNVirtual Private Network

<a name="performance"></a>
PERFORMANCE_TUNING.md
Performance Tuning Guide
Strategies to optimize Labourious for high-frequency agent execution and scaling.
Database Optimization
Indexing
Add indexes for frequently queried columns:
python# backend/database/models.py

class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(String, primary_key=True, index=True)
    room = Column(String, nullable=False, index=True)
    enabled = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(String, primary_key=True, index=True)
    agent_id = Column(String, ForeignKey("agents.id"), index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String, index=True)
Create compound indexes for common queries:
pythonfrom sqlalchemy import Index

trade_index = Index('idx_agent_status_date',
    Trade.agent_id,
    Trade.status,
    Trade.created_at
)
Query Optimization
Bad: N+1 query problem
pythonagents = db.query(Agent).all()
for agent in agents:
    trades = db.query(Trade).filter(Trade.agent_id == agent.id).all()
    # Runs 1 query for agents + 1 query per agent = N+1 queries
Good: Use eager loading
pythonfrom sqlalchemy.orm import joinedload

agents = db.query(Agent).options(joinedload(Agent.trades)).all()
# Runs 1-2 queries total
Archive old trades:
python# Delete trades older than 1 year
cutoff_date = datetime.utcnow() - timedelta(days=365)
old_trades = db.query(Trade).filter(Trade.created_at < cutoff_date)
# Save to archive first, then delete
archive_trades(old_trades)
old_trades.delete()
db.commit()
Database Maintenance
Regular optimization:
bash# SQLite optimization
sqlite3 ~/.labourious/labourious.db << EOF
ANALYZE;
VACUUM;
PRAGMA optimize;
EOF
Monitor database size:
bashdu -sh ~/.labourious/labourious.db
# Archive and prune if > 500MB
Agent Execution Optimization
Parallel Execution
Use ThreadPoolExecutor for concurrent agent runs:
python# backend/orchestrator/agent_orchestrator.py

from concurrent.futures import ThreadPoolExecutor
import asyncio

class AgentOrchestrator:
    def __init__(self, max_workers=10):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def run_all_agents(self):
        """Run all enabled agents in parallel"""
        loop = asyncio.get_event_loop()
        
        tasks = []
        for agent in self.agents.values():
            if agent.enabled:
                task = loop.run_in_executor(
                    self.executor,
                    self.run_agent_sync,
                    agent.id
                )
                tasks.append(task)
        
        await asyncio.gather(*tasks)
Configure worker count based on CPU:
pythonimport multiprocessing

max_workers = max(2, multiprocessing.cpu_count() - 1)
# Use N-1 cores, leave one for system
Agent Scheduling Optimization
Stagger agent execution to avoid thundering herd:
python# Spread agents evenly across check interval

agents = ['agent1', 'agent2', 'agent3', 'agent4', 'agent5']
check_interval_seconds = 300  # 5 minutes

# Schedule agents at staggered times
for i, agent_id in enumerate(agents):
    offset_seconds = (i / len(agents)) * check_interval_seconds
    scheduler.add_job(
        run_agent,
        'interval',
        seconds=check_interval_seconds,
        start_date=datetime.now() + timedelta(seconds=offset_seconds),
        args=[agent_id]
    )
Example:

Agent 1: 0s, 300s, 600s, ...
Agent 2: 60s, 360s, 660s, ...
Agent 3: 120s, 420s, 720s, ...
Spreads load evenly

Caching
Cache market data to reduce API calls:
python# backend/utils/cache.py

from cachetools import TTLCache
import asyncio

class MarketDataCache:
    def __init__(self, ttl_seconds=60):
        self.cache = TTLCache(maxsize=1000, ttl=ttl_seconds)
    
    async def get_market_data(self, symbol, broker):
        """Get cached market data or fetch fresh"""
        cache_key = f"{symbol}_{broker}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Fetch fresh data
        data = await broker.get_market_data(symbol)
        self.cache[cache_key] = data
        
        return data
Cache context:
pythoncontext_cache = {}  # {agent_id: (timestamp, context)}

def get_context(agent_id, cache_max_age_seconds=3600):
    if agent_id in context_cache:
        timestamp, context = context_cache[agent_id]
        if time.time() - timestamp < cache_max_age_seconds:
            return context  # Use cached version
    
    # Load fresh context
    context = load_context_file(agent_id)
    context_cache[agent_id] = (time.time(), context)
    
    return context
LLM Optimization
Batch Processing
Send multiple decisions to LLM in one request (if supported):
pythonasync def batch_decide(self, agent_data_list):
    """Get LLM decisions for multiple agents at once"""
    
    prompts = [
        self.build_prompt(data['market_data'], data['context'])
        for data in agent_data_list
    ]
    
    # Send batch request (if LLM supports)
    responses = await self.llm.batch_complete(prompts)
    
    decisions = [self.parse_decision(r) for r in responses]
    
    return decisions
Request Caching
Cache identical prompts:
pythonimport hashlib

prompt_cache = {}

async def decide_cached(self, market_data, context):
    prompt = self.build_prompt(market_data, context)
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
    
    if prompt_hash in prompt_cache:
        return prompt_cache[prompt_hash]
    
    decision = await self.llm.decide(prompt)
    prompt_cache[prompt_hash] = decision
    
    return decision
Model Selection
Use faster model for simple decisions:
pythondef choose_model(self, agent_type):
    if agent_type == 'day_trading':
        # Fast decision needed
        return 'claude-haiku-4-5'  # Fastest
    elif agent_type == 'swing_trading':
        return 'claude-sonnet-4-6'  # Balanced
    else:  # long_term
        return 'claude-opus-4-6'  # Most capable
API Optimization
Connection Pooling
Reuse HTTP connections:
pythonimport httpx

# Create persistent client
client = httpx.AsyncClient(
    limits=httpx.Limits(max_connections=10),
    timeout=30.0
)

# Reuse for all requests
async def get_market_data(symbol):
    response = await client.get(f"https://api.broker.com/quote/{symbol}")
    return response.json()
Rate Limiting
Respect broker rate limits:
pythonfrom aiolimiter import AsyncLimiter

class RateLimitedBroker:
    def __init__(self, calls_per_minute=60):
        self.limiter = AsyncLimiter(max_rate=calls_per_minute, time_period=60)
    
    async def place_order(self, symbol, side, quantity):
        async with self.limiter:
            return await self._place_order(symbol, side, quantity)
WebSocket Optimization
Batch Updates
Send multiple updates in one message:
python# Instead of emitting per trade:
# socket.emit('trade_executed', trade1)
# socket.emit('trade_executed', trade2)

# Emit batch:
socket.emit('trades_executed', {
    'trades': [trade1, trade2, ...],
    'portfolio': portfolio_update,
    'timestamp': now()
})
Selective Broadcasting
Only send updates to interested clients:
python@socketio.on('subscribe_agent')
async def subscribe_agent(data):
    agent_id = data['agent_id']
    join_room(f"agent_{agent_id}")
    
    # Later, only send to subscribed clients
    emit('agent_update', agent_data, room=f"agent_{agent_id}")
Frontend Optimization
Code Splitting
Load code on demand:
javascript// frontend/src/App.jsx

const Warroom = lazy(() => import('./pages/Warroom'));
const ControlRoom = lazy(() => import('./pages/ControlRoom'));

function App() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/warroom/:room" element={<Warroom />} />
        <Route path="/control" element={<ControlRoom />} />
      </Routes>
    </Suspense>
  );
}
Memoization
Prevent unnecessary re-renders:
javascriptconst AgentCard = React.memo(({ agent, onSelect }) => {
  return (
    <div onClick={() => onSelect(agent.id)}>
      {agent.name}
    </div>
  );
});
Virtual Scrolling
For large lists (50+ agents):
javascriptimport { FixedSizeList } from 'react-window';

function AgentList({ agents }) {
  return (
    <FixedSizeList
      height={600}
      itemCount={agents.length}
      itemSize={80}
    >
      {({ index, style }) => (
        <div style={style}>
          <AgentCard agent={agents[index]} />
        </div>
      )}
    </FixedSizeList>
  );
}
Monitoring Performance
Metrics to Track
python# backend/monitoring/metrics.py

from prometheus_client import Counter, Histogram

# Count trades
trades_executed = Counter('trades_executed_total', 'Total trades executed')

# Track execution time
execution_time = Histogram('agent_execution_seconds', 'Agent execution time')

# Track errors
agent_errors = Counter('agent_errors_total', 'Agent execution errors')

# Example usage:
@execution_time.time()
async def run_agent(agent_id):
    try:
        # Execute agent
        trades_executed.inc()
    except Exception as e:
        agent_errors.inc()
Dashboard
Expose metrics for monitoring:
pythonfrom prometheus_client import start_http_server

# Start metrics server on port 8001
start_http_server(8001)

# Access at http://localhost:8001/metrics
Load Testing
Simulate High Load
bash# Test with 20 concurrent agents
k6 run backend/performance/load_test.js --vus 20 --duration 5m
Expected Performance

Single machine: 5-10 agents at 5-min frequency = <1% CPU
Single machine: 50+ agents = Consider distributed setup
API response time: <500ms (p95)
Database query time: <100ms (p95)

Scaling Strategy
Single Machine (Phase 1):

Up to 20 concurrent agents
Upgrade to SSD if needed
Increase RAM to 4GB+

Multi-Machine (Phase 2+):

Separate backend instances (load balanced)
PostgreSQL instead of SQLite
Redis for caching and sessions
Separate Ollama instances

Debugging Performance Issues
Identify bottleneck:
pythonimport cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Run agent execution
run_agent(agent_id)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 slowest calls
Memory profiling:
bashpip install memory-profiler

python -m memory_profiler backend/main.py
Database query profiling:
pythonfrom sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, params, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(Engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, params, context, executemany):
    total_time = time.time() - conn.info['query_start_time'].pop(-1)
    logger.info(f"Query time: {total_time:.4f}s")
Summary
Quick wins:

Add database indexes
Cache market data
Stagger agent execution
Use connection pooling

Medium effort:

Batch LLM requests
Code splitting (frontend)
Memoization
Prometheus monitoring

Long-term:

Distributed architecture
Move to PostgreSQL
Redis caching layer
Load balancing


END OF PHASE 1 DOCUMENTATION
All Phase 1 documents have been included above. Use these as reference during development and deployment of Labourious MVP.
Last updated: June 2026
