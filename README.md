# Akitafolio 🐕💰

Multi-chain crypto portfolio tracker for Telegram.

Track your ETH, BTC, ERC20 tokens, and DeFi positions across 8 EVM chains + Bitcoin.

## ✨ Features

- 📊 **Portfolio Tracking** - Combined value of all assets in USD
- 🔗 **8 EVM Chains** - Ethereum, Base, Linea, Optimism, Arbitrum, Unichain, Polygon, BSC
- ₿ **Bitcoin** - Address and xpub/ypub/zpub support
- 🪙 **ERC20 Tokens** - Auto-track popular tokens
- 🏦 **DeFi Monitoring** - Aave V3 positions with health factors
- 📈 **24h Change** - Track portfolio performance

## 🚀 Quick Start

```bash
# Install locked runtime and development dependencies
uv sync --all-groups

# Configure
cp config_example.txt .env
# Edit .env with your TELEGRAM_BOT_TOKEN and INFURA_PROJECT_ID

# Run
uv run python bot.py
```

## ✅ Development checks

```bash
uv run ruff check .
uv run mypy
uv run pytest --cov
```

## 📋 Commands

| Command | Description |
|---------|-------------|
| `/portfolio` | View complete portfolio value |
| `/eth <address>` | Check ETH across all chains |
| `/btc <address>` | Check Bitcoin balance |
| `/tokens` | View ERC20 token balances |
| `/defi` | View DeFi positions |
| `/add_eth <addr>` | Save ETH address |
| `/add_btc <addr>` | Save BTC address |
| `/help` | Full command list |

## 📚 Documentation

- **[Main Documentation](./docs/README.md)** - Full feature guide
- **[Deployment Guide](./docs/DEPLOYMENT.md)** - Server deployment
- **[Changelog](./docs/CHANGELOG.md)** - Version history
- **[Development Guide](./docs/DEVELOPMENT.md)** - For contributors
- **[ADR-0002](./docs/adr/0002-python-312-and-uv.md)** - Python and dependency workflow

## 🏗️ Architecture

```
akitafolio/
├── handlers/     # Telegram commands
├── services/     # Business logic
├── models.py     # Pydantic data models
├── cache.py      # TTL caching
└── config.py     # Settings
```

## 📄 License

Open source for personal and educational use.

---

**[Full Documentation →](./docs/README.md)**
