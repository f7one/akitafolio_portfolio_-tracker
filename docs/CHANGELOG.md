# 📝 Changelog

All notable changes to Akitafolio are documented here.

---

## [2.1.0] - 2026-01-21

### 🏗️ Major Refactoring

#### Package Structure
- **Modular Architecture**: Split monolithic `bot.py` into `akitafolio/` package
- **Service Layer**: Separated business logic into dedicated services
- **Pydantic Models**: Added type-safe data models for all domain objects
- **Caching Layer**: Implemented TTL caching for API responses

#### New Package Structure
```
akitafolio/
├── __init__.py
├── cache.py          # TTL caching with LRU eviction
├── config.py         # Pydantic settings management
├── exceptions.py     # Custom exception classes
├── http_client.py    # Rate-limited async HTTP client
├── models.py         # 15+ Pydantic data models
├── storage.py        # Secure JSON file storage
├── handlers/
│   └── commands.py   # Telegram command handlers
└── services/
    ├── bitcoin.py    # BTC & xpub services
    ├── blockchain.py # EVM chain interactions
    ├── defi.py       # Aave V3 positions
    ├── portfolio.py  # Portfolio aggregation
    ├── prices.py     # CoinGecko prices
    └── tokens.py     # ERC20 token balances
```

#### Security Improvements (Phase 1 & 2)
- ✅ Async HTTP with `aiohttp` (replaced sync `requests`)
- ✅ Rate limiting with token bucket algorithm
- ✅ Per-endpoint rate limits (CoinGecko, Blockchain.info, Infura)
- ✅ Secrets masking in logs
- ✅ Input validation and sanitization
- ✅ Secure file storage with path validation
- ✅ Atomic file writes
- ✅ Consistent request timeouts
- ✅ Proper application shutdown hooks

#### Caching Features
- Price cache: 30s TTL
- Balance cache: 60s TTL
- Token cache: 60s TTL
- DeFi cache: 120s TTL
- LRU eviction with configurable max size
- Cache statistics tracking

---

## [2.0.0] - 2026-01-20

### 🎉 Token & DeFi Tracking

#### New Features
- **ERC20 Token Tracking**: Automatic tracking of popular tokens
- **DeFi Position Monitoring**: Aave V3 support across 5 chains
- **Health Factor Monitoring**: Risk warnings for lending positions
- **Enhanced Portfolio**: Now includes tokens and DeFi in total value

#### New Commands
| Command | Description |
|---------|-------------|
| `/tokens` | View all ERC20 token balances |
| `/defi` | View DeFi positions with health factors |
| `/add_token` | Add custom ERC20 token to track |
| `/toggle_defi` | Enable/disable DeFi tracking |

#### Supported Tokens (Auto-tracked)
- Ethereum: USDT, USDC, DAI, WETH, WBTC, LINK, UNI, AAVE
- Base: USDC
- Arbitrum: USDC, USDT
- Optimism: USDC, USDT
- Polygon: USDC, USDT

#### DeFi Support
- Aave V3 on: Ethereum, Arbitrum, Optimism, Base, Polygon
- Tracks: Collateral, Debt, Net Value, Health Factor
- Health factor warnings: ✅ Safe, ⚠️ Low, 🚨 RISKY!

---

## [1.5.0] - 2026-01-15

### 🔑 HD Wallet Support

#### New Features
- **xpub/ypub/zpub Support**: Track Bitcoin HD wallets
- **Multi-Address Batch**: Add multiple addresses at once
- **24h Change Tracking**: Portfolio value change over time

#### New Commands
| Command | Description |
|---------|-------------|
| `/xpub <key>` | Check HD wallet balance |
| `/add_xpub <key>` | Save HD wallet(s) |
| `/remove_xpub <key>` | Remove HD wallet |

---

## [1.0.0] - 2026-01-13

### 🚀 Initial Release

#### Core Features
- **Multi-Chain Support**: 8 EVM chains + Bitcoin
- **Portfolio Tracking**: Save and track multiple addresses
- **Real-time Prices**: ETH and BTC from CoinGecko
- **Parallel Processing**: Fast balance fetching

#### Supported Chains
- Ethereum, Base, Linea, Optimism, Arbitrum, Unichain, Polygon, BSC

#### Commands
- `/eth`, `/btc` - Balance checking
- `/add_eth`, `/add_btc` - Address management
- `/portfolio` - Portfolio overview
- `/chains` - List supported networks

---

## Upgrade Path

### From v1.x to v2.x

**No breaking changes!** All existing commands work the same.

To use new features:
1. Update to latest code
2. Install new dependencies: `pip install -r requirements.txt`
3. Restart the bot

### From bot.py to bot_refactored.py

The refactored version uses the new package structure:

```bash
# Old
python bot.py

# New (recommended)
python bot_refactored.py
```

Both entry points are supported during the transition period.

---

## Roadmap

### Planned Features
- [ ] More DeFi protocols (Compound, Uniswap LP)
- [ ] NFT portfolio tracking
- [ ] Price alerts and notifications
- [ ] Historical portfolio charts
- [ ] Export to CSV/Excel
- [ ] Web dashboard
- [ ] Multi-language support

---

**For questions or feature requests, please open an issue on GitHub!**
