# 📝 Changelog

## Version 2.0.0 - Portfolio Tracking Update (2026-01-13)

### 🎉 Major New Features

#### 💼 Portfolio Management System
- **Save Multiple Addresses**: Save unlimited ETH and BTC addresses to your personal portfolio
- **Total Portfolio Value**: View combined ETH + BTC value in USD with one command (`/portfolio`)
- **Asset Allocation**: See percentage breakdown of your ETH vs BTC holdings
- **Multi-Address Support**: Track multiple wallets for each asset type
- **Persistent Storage**: Addresses saved in `saved_addresses.json` (per-user, gitignored)

#### 💰 Enhanced Balance Features
- **BTC USD Value**: Bitcoin balances now show USD value in addition to BTC amount
- **Combined Portfolio**: Calculate total portfolio value (ETH + BTC) in USD
- **ETH + BTC Prices**: Fetch both crypto prices from CoinGecko in one API call
- **Smart Aggregation**: Automatically sum ETH across all addresses and chains

### 📋 New Commands

| Command | Description |
|---------|-------------|
| `/add_eth <address>` | Save Ethereum address to portfolio |
| `/add_btc <address>` | Save Bitcoin address to portfolio |
| `/portfolio` | View complete portfolio value (ETH + BTC in USD) |
| `/addresses` | List all saved addresses |
| `/remove_eth <address>` | Remove ETH address from portfolio |
| `/remove_btc <address>` | Remove BTC address from portfolio |

### 🔧 Technical Improvements

- **Parallel Multi-Address Processing**: Query multiple addresses simultaneously
- **Dual Price Fetching**: Get ETH and BTC prices in single API call
- **JSON Storage System**: User data stored in `saved_addresses.json`
- **Per-User Isolation**: Each Telegram user has separate address storage
- **Enhanced Error Handling**: Better validation and error messages

### 📊 Enhanced Output

#### Portfolio Command Output
```
💼 YOUR PORTFOLIO
═══════════════════════
🎯 TOTAL VALUE: $52,345.67

⟠ Ethereum
Total: 2.456789 ETH
Value: $4,567.89
Price: $1,859.23
Addresses: 2

₿ Bitcoin
Total: 1.23456789 BTC
Value: $47,777.78
Price: $38,650.00
Addresses: 1

📊 Allocation
ETH: 8.7%
BTC: 91.3%
```

### 📚 Documentation

- **PORTFOLIO_FEATURES.md**: Complete portfolio feature documentation
- **COMMANDS.md**: Command reference guide with examples
- **Updated README.md**: New features and portfolio workflow
- **Updated .gitignore**: Added `saved_addresses.json` exclusion

### 🔐 Security & Privacy

- ✅ Local storage only (no cloud)
- ✅ Per-user data isolation
- ✅ Public addresses only (no private keys)
- ✅ Read-only blockchain queries
- ✅ Gitignored storage file

---

## Version 1.0.0 - Multi-Chain Balance Checker (2026-01-13)

### Initial Release Features

#### 🔗 Multi-Chain Support
- **8 EVM Chains**: Ethereum, Base, Linea, Optimism, Arbitrum, Unichain, Polygon, BSC
- **Bitcoin Support**: BTC balance checking via Blockchain.info API
- **Aggregated ETH Balance**: Total ETH across all ETH-based chains
- **Parallel Processing**: Query all chains simultaneously for speed

#### 💵 Price Integration
- **Real-time Prices**: ETH price from CoinGecko API
- **USD Conversion**: Automatic conversion to USD for ETH balances
- **Per-Chain Breakdown**: Individual balance for each network

#### 🎯 Core Features
- **Address Validation**: Validate ETH and BTC addresses before querying
- **Single Infura ID**: One project ID for all 8 EVM chains
- **Rich Responses**: Formatted output with emojis and clear structure
- **Error Handling**: Comprehensive error handling and logging

#### 📋 Commands (v1.0)
- `/start` - Welcome message
- `/help` - Help information
- `/eth <address>` - Check ETH balance across all chains
- `/btc <address>` - Check Bitcoin balance
- `/chains` - List supported chains

#### 🛠️ Technical Stack
- Python 3.8+
- python-telegram-bot 20.7
- web3.py 6.15.1
- Infura RPC endpoints
- CoinGecko API (free tier)
- Blockchain.info API

#### 📚 Documentation
- README.md with setup instructions
- MULTI_CHAIN_FEATURES.md
- config_example.txt
- Comprehensive inline code comments

---

## Upgrade Path

### From v1.0 to v2.0

**No breaking changes!** All v1.0 commands still work exactly the same.

**New features are additive:**
- Old workflow (`/eth`, `/btc`) → Still works perfectly
- New workflow (`/add_eth`, `/portfolio`) → Additional option

**To use new features:**
1. Pull latest code
2. Start using `/add_eth` and `/add_btc` to save addresses
3. Use `/portfolio` to see total value
4. Optional: Use `/addresses` to manage saved addresses

**Data Migration:**
- None needed - fresh start with portfolio tracking
- Existing users can start using new commands immediately

---

## Roadmap

### Planned Features (v3.0)
- [ ] Token balances (ERC-20, BEP-20)
- [ ] NFT portfolio tracking
- [ ] Price alerts and notifications
- [ ] Historical portfolio charts
- [ ] Export portfolio to CSV/Excel
- [ ] More chains (Avalanche, Fantom, Solana)
- [ ] Portfolio statistics (24h change, ATH, etc.)
- [ ] Multi-currency support (EUR, GBP, etc.)

### Potential Enhancements
- [ ] Web dashboard for portfolio visualization
- [ ] Scheduled portfolio reports (daily/weekly)
- [ ] Transaction history tracking
- [ ] DeFi position tracking
- [ ] Tax reporting features
- [ ] Mobile app integration

---

**For questions or feature requests, please open an issue on GitHub!**
