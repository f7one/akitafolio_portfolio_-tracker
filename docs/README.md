# Akitafolio 🐕💰

A powerful Telegram bot that tracks your complete crypto portfolio across multiple blockchain networks with **ERC20 token tracking**, **DeFi position monitoring**, and **total portfolio value** calculation.

## ✨ Features

### 💼 Portfolio Management
- 🎯 **Multi-Address Tracking** - Track unlimited ETH and BTC addresses
- 🔑 **HD Wallet Support** - xpub/ypub/zpub for Bitcoin wallets
- 🪙 **ERC20 Token Tracking** - Automatic tracking of popular tokens
- 🏦 **DeFi Monitoring** - Track Aave V3 lending positions across 5 chains
- 📊 **Total Portfolio Value** - Combined USD value of all assets
- 📈 **24h Change Tracking** - Monitor portfolio performance

### 🔗 Supported Networks
- **EVM Chains (8)**: Ethereum, Base, Linea, Optimism, Arbitrum, Unichain, Polygon, BSC
- **Bitcoin**: Address and xpub/ypub/zpub support
- **DeFi**: Aave V3 on Ethereum, Arbitrum, Optimism, Base, Polygon

## 🚀 Quick Start

### Prerequisites
- Python 3.12
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Infura Project ID (free at [infura.io](https://infura.io))

### Installation

```bash
# Clone the repository
git clone https://github.com/f7one/akitafolio_portfolio_-tracker.git
cd tg-balance-bot

# Install locked runtime and development dependencies
uv sync --all-groups

# Configure environment
cp config_example.txt .env
# Edit .env with your tokens
```

### Configuration

Create a `.env` file:

```bash
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
INFURA_PROJECT_ID=your_infura_project_id
```

### Run the Bot

```bash
uv run python bot.py
```

## 📋 Commands

### Balance Commands
| Command | Description |
|---------|-------------|
| `/eth <address>` | Check ETH balance across all chains |
| `/btc <address>` | Check Bitcoin balance |
| `/xpub <key>` | Check HD wallet balance |
| `/tokens` | View all ERC20 token balances |
| `/defi` | View DeFi positions |
| `/chains` | List supported chains |

### Portfolio Management
| Command | Description |
|---------|-------------|
| `/add_eth <address>` | Save ETH address(es) |
| `/add_btc <address>` | Save BTC address(es) |
| `/add_xpub <key>` | Save HD wallet(s) |
| `/portfolio` | View complete portfolio |
| `/addresses` | List saved addresses |
| `/remove_eth <address>` | Remove ETH address |
| `/remove_btc <address>` | Remove BTC address |
| `/remove_xpub <key>` | Remove HD wallet |

### Token & DeFi
| Command | Description |
|---------|-------------|
| `/add_token <chain> <address> <id>` | Add custom token |
| `/toggle_defi` | Enable/disable DeFi tracking |

## 📊 Example Portfolio Output

```
💼 YOUR PORTFOLIO

══════════════════════════════

🎯 TOTAL VALUE: $152,345.67

📈 24h Change: +$2,450.00 (+1.63%)

──────────────────────────────

⟠ Ethereum
Total: 15.456789 ETH
Value: $25,967.12

₿ Bitcoin
Total: 2.50000000 BTC
Value: $96,625.00

🪙 ERC20 Tokens
Total Value: $21,303.55
Tokens: 12

🏦 DeFi Positions
Net Value: $8,450.00
Collateral: $10,000.00
Debt: $1,550.00

──────────────────────────────

📊 Allocation
ETH: 17.0%  BTC: 63.4%  Tokens: 14.0%  DeFi: 5.6%
```

## 🏗️ Architecture (v2.0)

The bot uses a modular package structure:

```
akitafolio/
├── cache.py          # TTL caching layer
├── config.py         # Pydantic settings
├── models.py         # Data models
├── http_client.py    # Rate-limited HTTP client
├── storage.py        # Secure JSON storage
├── handlers/         # Telegram command handlers
└── services/         # Business logic
    ├── blockchain.py # EVM chain interactions
    ├── bitcoin.py    # BTC & xpub
    ├── tokens.py     # ERC20 tokens
    ├── defi.py       # Aave V3
    ├── prices.py     # CoinGecko
    └── portfolio.py  # Aggregation
```

## 🔒 Security

- ✅ Read-only blockchain queries
- ✅ No private keys required
- ✅ Local data storage (gitignored)
- ✅ Per-user data isolation
- ✅ Rate limiting for API calls
- ✅ Input validation and sanitization

## 📚 Documentation

- [Deployment Guide](./DEPLOYMENT.md) - Server deployment instructions
- [Engineering Roadmap](./ROADMAP.md) - Code review master plan and epic status
- [Epic 0 Execution Plan](./EPIC_0_EXECUTION_PLAN.md) - Production migration plan
- [ADR-0001](./adr/0001-separate-production-vps.md) - Separate production VPS decision
- [Changelog](./CHANGELOG.md) - Version history
- [Development Guide](./DEVELOPMENT.md) - Developer documentation

## 🤝 Contributing

Contributions are welcome! Please read the development guide before submitting PRs.

## 📄 License

This project is open source and available for personal and educational use.

## ⚠️ Disclaimer

This bot is for informational purposes only. Always verify wallet balances through official sources before making any financial decisions.
