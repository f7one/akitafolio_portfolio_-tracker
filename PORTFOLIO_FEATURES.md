# 💼 Portfolio Tracking Features

## Overview

Your Telegram bot now includes a complete **portfolio management system** that allows you to:
- Save multiple Ethereum and Bitcoin addresses
- Track total portfolio value (ETH + BTC) in USD
- View asset allocation breakdown
- Manage addresses easily

## 🎯 Key Features

### 1. Address Management

**Save Addresses:**
```
/add_eth 0xYourEthAddress
/add_btc YourBtcAddress
```

**View Saved Addresses:**
```
/addresses
```

**Remove Addresses:**
```
/remove_eth 0xYourEthAddress
/remove_btc YourBtcAddress
```

### 2. Portfolio Valuation

The `/portfolio` command gives you:

✅ **Total Portfolio Value in USD**
- Combines all ETH from all chains
- Combines all BTC from all addresses
- Shows total in dollars

✅ **Individual Asset Breakdown**
- Total ETH amount and USD value
- Total BTC amount and USD value
- Current prices for both assets
- Number of addresses tracked

✅ **Asset Allocation**
- Percentage of portfolio in ETH
- Percentage of portfolio in BTC

### 3. Multi-Address Support

You can save **multiple addresses** for each asset type:
- Track different wallets (hot wallet, cold wallet, etc.)
- Monitor family/business addresses
- Aggregate holdings from multiple sources

## 📊 Example Portfolio Response

```
💼 YOUR PORTFOLIO

══════════════════════════════

🎯 TOTAL VALUE: $52,345.67

──────────────────────────────

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

──────────────────────────────

📊 Allocation
ETH: 8.7%
BTC: 91.3%
```

## 🔧 Technical Details

### Data Storage

- **File**: `saved_addresses.json`
- **Format**: JSON with user ID as key
- **Structure**:
```json
{
  "123456789": {
    "eth": [
      "0xAddress1...",
      "0xAddress2..."
    ],
    "btc": [
      "1BtcAddress1...",
      "bc1BtcAddress2..."
    ]
  }
}
```
- **Privacy**: File is gitignored and stored locally
- **Per-User**: Each Telegram user has isolated data

### Portfolio Calculation Flow

1. **Load Saved Addresses** → Retrieve user's saved ETH/BTC addresses
2. **Parallel Queries** → Fetch balances from all addresses simultaneously
3. **ETH Aggregation** → For each ETH address, query all 8 chains and sum
4. **BTC Aggregation** → For each BTC address, fetch balance
5. **Price Fetch** → Get current ETH and BTC prices from CoinGecko
6. **USD Conversion** → Calculate USD value for each asset
7. **Total Calculation** → Sum ETH + BTC for total portfolio value
8. **Allocation** → Calculate percentage breakdown

### Performance

- **Parallel Processing**: All addresses queried simultaneously using `asyncio`
- **Fast Responses**: Typical response time 2-5 seconds even with multiple addresses
- **Efficient**: Single API call for both ETH and BTC prices

## 💡 Use Cases

### Personal Portfolio Tracking
Save your personal ETH and BTC addresses to quickly check your total crypto holdings:
```
/add_eth 0xMyMainWallet
/add_eth 0xMyColdWallet
/add_btc 1MyBitcoinAddress
/portfolio
```

### Multi-Wallet Management
Track balances across different wallets:
- Hardware wallet
- Exchange wallet
- Hot wallet
- Paper wallet

### Family/Business Tracking
Monitor multiple people's wallets or business holdings (with permission):
```
/add_eth 0xWallet1
/add_eth 0xWallet2
/add_eth 0xWallet3
/add_btc 1BtcWallet1
/add_btc 1BtcWallet2
/portfolio
```

### Investment Monitoring
Track your investment performance over time by regularly checking `/portfolio`

## 🎨 Features Summary

| Feature | Command | Description |
|---------|---------|-------------|
| Save ETH Address | `/add_eth <addr>` | Add Ethereum address to portfolio |
| Save BTC Address | `/add_btc <addr>` | Add Bitcoin address to portfolio |
| View Portfolio | `/portfolio` | See total value (ETH + BTC in USD) |
| List Addresses | `/addresses` | Show all saved addresses |
| Remove ETH | `/remove_eth <addr>` | Remove ETH address |
| Remove BTC | `/remove_btc <addr>` | Remove BTC address |
| Quick Check | `/eth <addr>` | Check single address (no save) |
| Quick Check | `/btc <addr>` | Check single address (no save) |

## 🔐 Privacy & Security

**What's Stored:**
- ✅ Public wallet addresses only
- ✅ User's Telegram ID (for data isolation)

**What's NOT Stored:**
- ❌ Private keys
- ❌ Seed phrases
- ❌ Personal information
- ❌ Transaction history

**Security Best Practices:**
- The bot only reads blockchain data (read-only)
- `saved_addresses.json` is gitignored
- Data stored locally on your server
- Each user's data is isolated
- No cloud storage or external databases

## 🚀 Getting Started

### Quick Start (3 Steps)

1. **Save your addresses:**
```
/add_eth 0xYourAddress
/add_btc YourBtcAddress
```

2. **Check your portfolio:**
```
/portfolio
```

3. **That's it!** Your portfolio is now tracked and ready.

### Advanced Usage

**Track Multiple Addresses:**
```
/add_eth 0xWallet1
/add_eth 0xWallet2
/add_eth 0xWallet3
/portfolio
```

**Manage Addresses:**
```
/addresses              # See what's saved
/remove_eth 0xWallet2  # Remove one
/portfolio             # Check updated portfolio
```

## 📈 Benefits

1. **Convenience** - One command to see everything
2. **Aggregation** - ETH from all chains combined
3. **USD Value** - Real-time dollar valuation
4. **Multi-Address** - Track multiple wallets
5. **Allocation** - See ETH/BTC breakdown
6. **Privacy** - Your data stays on your server
7. **Fast** - Parallel processing for speed

---

**Your complete crypto portfolio, one command away! 💼**
