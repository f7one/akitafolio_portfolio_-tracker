# 🛠️ Development Guide

Complete guide for developers contributing to Akitafolio.

## 📋 Table of Contents

- [Getting Started](#getting-started)
- [Architecture](#architecture)
- [Package Structure](#package-structure)
- [Adding Features](#adding-features)
- [Testing](#testing)
- [Code Style](#code-style)
- [API Reference](#api-reference)

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- pip and virtualenv
- Git

### Development Setup

```bash
# Clone repository
git clone https://github.com/f7one/akitafolio_portfolio_-tracker.git
cd tg-balance-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies (optional)
pip install pydantic pydantic-settings

# Create .env file
cp config_example.txt .env
# Edit .env with your API keys

# Run the bot
python bot_refactored.py
```

---

## 🏗️ Architecture

### Overview

Akitafolio uses a layered architecture:

```
┌─────────────────────────────────────┐
│           Telegram API              │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│       Handlers (commands.py)        │
│   - Parse user input                │
│   - Format responses                │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│         Services Layer              │
│   - Business logic                  │
│   - Data aggregation                │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│      Infrastructure Layer           │
│   - HTTP client                     │
│   - Cache                           │
│   - Storage                         │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│       External APIs                 │
│   - Infura (EVM chains)             │
│   - CoinGecko (prices)              │
│   - Blockchain.info (Bitcoin)       │
└─────────────────────────────────────┘
```

### Key Components

| Component | Description |
|-----------|-------------|
| **Handlers** | Telegram command handlers, user interaction |
| **Services** | Business logic, data fetching, aggregation |
| **Models** | Pydantic data models for validation |
| **Cache** | TTL-based caching for API responses |
| **Storage** | Secure JSON file storage |
| **HTTP Client** | Rate-limited async HTTP requests |

---

## 📁 Package Structure

```
akitafolio/
├── __init__.py          # Package exports
├── cache.py             # TTL caching with LRU
├── config.py            # Pydantic settings
├── exceptions.py        # Custom exceptions
├── http_client.py       # Rate-limited HTTP client
├── models.py            # Pydantic data models
├── storage.py           # Secure file storage
│
├── handlers/
│   ├── __init__.py
│   └── commands.py      # All Telegram handlers
│
└── services/
    ├── __init__.py
    ├── bitcoin.py       # BTC & xpub
    ├── blockchain.py    # EVM chains
    ├── defi.py          # Aave V3
    ├── portfolio.py     # Aggregation
    ├── prices.py        # CoinGecko
    └── tokens.py        # ERC20 tokens
```

---

## ➕ Adding Features

### Adding a New Command

1. **Add handler in `handlers/commands.py`:**

```python
async def my_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mycommand."""
    user_id = update.effective_user.id
    
    # Your logic here
    result = await SomeService.do_something()
    
    await update.message.reply_text(f"Result: {result}")
```

2. **Register in `handlers/__init__.py`:**

```python
from akitafolio.handlers.commands import (
    # ... existing imports
    my_command,
)
```

3. **Add to `bot_refactored.py`:**

```python
handlers = [
    # ... existing handlers
    ("mycommand", my_command),
]
```

### Adding a New Service

1. **Create service file `services/myservice.py`:**

```python
"""My new service."""

import logging
from akitafolio.http_client import HTTPClient
from akitafolio.cache import cached, balance_cache
from akitafolio.models import MyModel

logger = logging.getLogger(__name__)


class MyService:
    """Service for doing something."""
    
    @classmethod
    @cached(cache=balance_cache, ttl=60.0, key_prefix="my_data")
    async def get_data(cls, param: str) -> MyModel:
        """Fetch data with caching."""
        try:
            url = f"https://api.example.com/{param}"
            data = await HTTPClient.get(url)
            return MyModel(**data)
        except Exception as e:
            logger.error(f"Error: {e}")
            return MyModel(error=str(e))
```

2. **Export in `services/__init__.py`:**

```python
from akitafolio.services.myservice import MyService
```

### Adding a New Data Model

Add to `models.py`:

```python
class MyModel(BaseModel):
    """My data model."""
    field1: str
    field2: float = 0.0
    optional_field: Optional[str] = None
    error: Optional[str] = None
    
    @property
    def is_valid(self) -> bool:
        return self.error is None
```

---

## 🧪 Testing

### Manual Testing

```bash
# Run the bot
python bot_refactored.py

# In Telegram, test commands:
/start
/eth 0xYourAddress
/portfolio
```

### Import Testing

```bash
python -c "
from akitafolio.handlers import start_command
from akitafolio.services import PortfolioService
from akitafolio.models import Portfolio
print('✅ All imports successful')
"
```

### Syntax Check

```bash
python -m py_compile bot_refactored.py
python -m py_compile akitafolio/handlers/commands.py
```

---

## 📝 Code Style

### General Guidelines

- Use type hints for all function parameters and returns
- Use Pydantic models for data validation
- Add docstrings to all public functions and classes
- Log errors with appropriate log levels
- Use async/await for all I/O operations

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `PortfolioService` |
| Functions | snake_case | `get_portfolio` |
| Constants | UPPER_CASE | `DEFAULT_TTL` |
| Private | _underscore | `_internal_method` |

### Example Code

```python
"""Module docstring."""

import logging
from typing import Optional, List
from pydantic import BaseModel

from akitafolio.cache import cached, balance_cache
from akitafolio.http_client import HTTPClient
from akitafolio.exceptions import APIError

logger = logging.getLogger(__name__)


class MyModel(BaseModel):
    """Model docstring."""
    value: float = 0.0
    error: Optional[str] = None


class MyService:
    """Service docstring."""
    
    @classmethod
    @cached(cache=balance_cache, ttl=60.0)
    async def fetch_data(cls, param: str) -> MyModel:
        """
        Fetch data from external API.
        
        Args:
            param: The parameter to fetch.
            
        Returns:
            MyModel with the result or error.
        """
        try:
            data = await HTTPClient.get(f"https://api.example.com/{param}")
            return MyModel(value=data.get('value', 0))
        except APIError as e:
            logger.error(f"API error: {e}")
            return MyModel(error=str(e))
```

---

## 📚 API Reference

### HTTPClient

```python
from akitafolio.http_client import HTTPClient

# GET request returning JSON
data = await HTTPClient.get(url, timeout=10)

# GET request returning text
text = await HTTPClient.get_text(url, timeout=10)

# Close session (on shutdown)
await HTTPClient.close()
```

### Cache

```python
from akitafolio.cache import cached, price_cache, balance_cache

# Decorator for caching
@cached(cache=price_cache, ttl=30.0, key_prefix="my_func")
async def my_function(param: str) -> dict:
    # ... expensive operation
    return result

# Manual cache operations
await price_cache.get(key)
await price_cache.set(key, value, ttl=60.0)
await price_cache.delete(key)
await price_cache.clear()
```

### Storage

```python
from akitafolio.storage import (
    load_user_addresses,
    save_user_addresses,
    load_portfolio_history,
    save_portfolio_snapshot,
)

# Load user data
addresses = load_user_addresses(user_id)

# Save user data
save_user_addresses(user_id, addresses)

# Portfolio history
history = load_portfolio_history(user_id)
save_portfolio_snapshot(user_id, total_usd, eth, btc, eth_price, btc_price)
```

### Models

```python
from akitafolio.models import (
    Portfolio,
    UserAddresses,
    ChainBalance,
    TokenBalance,
    DefiPosition,
    CryptoPrices,
)

# Create model
portfolio = Portfolio(
    total_eth=10.5,
    total_btc_combined=1.5,
    eth_price=1800.0,
    btc_price=40000.0,
)

# Access computed properties
print(portfolio.total_portfolio_usd)
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | Yes |
| `INFURA_PROJECT_ID` | Infura project ID | Yes |
| `AKITAFOLIO_DEBUG` | Enable debug mode | No |
| `AKITAFOLIO_LOG_LEVEL` | Log level (INFO, DEBUG) | No |

### Pydantic Settings

Configuration is managed in `config.py`:

```python
from akitafolio.config import settings

# Access settings
token = settings.telegram_bot_token
chains = settings.get_all_chains()
tokens = settings.get_default_tokens()
```

---

## 🐛 Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Cache Stats

```python
from akitafolio.cache import cache_manager

stats = cache_manager.get_stats()
print(stats)
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Import errors | Check `__init__.py` exports |
| Cache not working | Verify `@cached` decorator placement |
| Rate limiting | Check rate limiter settings |
| Timeout errors | Increase timeout in HTTPClient call |

---

## 📦 Dependencies

### Core Dependencies

| Package | Purpose |
|---------|---------|
| `python-telegram-bot` | Telegram Bot API |
| `web3` | Ethereum interactions |
| `aiohttp` | Async HTTP client |
| `pydantic` | Data validation |
| `pydantic-settings` | Settings management |
| `python-dotenv` | Environment variables |

### Installing Dependencies

```bash
pip install -r requirements.txt
```

---

**Happy coding! 🚀**
