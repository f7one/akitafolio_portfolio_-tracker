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
# Install
pip install -r requirements.txt

# Configure
cp config_example.txt .env
# Edit .env with your TELEGRAM_BOT_TOKEN and INFURA_PROJECT_ID

# Run
python bot_refactored.py
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
