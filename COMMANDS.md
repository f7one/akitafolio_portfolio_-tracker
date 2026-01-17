# 📋 Bot Commands Reference

## Quick Command List

### 💼 Portfolio Management (Main Features)

| Command | Usage | Description |
|---------|-------|-------------|
| `/add_eth` | `/add_eth 0xAddress` | Save Ethereum address to your portfolio |
| `/add_btc` | `/add_btc 1BtcAddress` | Save Bitcoin address to your portfolio |
| `/add_xpub` | `/add_xpub xpub6CUG...` | Save HD wallet (xpub) to your portfolio |
| `/portfolio` | `/portfolio` | **View total portfolio value (ETH + BTC in USD)** |
| `/addresses` | `/addresses` | List all your saved addresses and xpub keys |
| `/remove_eth` | `/remove_eth 0xAddress` | Remove ETH address from portfolio |
| `/remove_btc` | `/remove_btc 1BtcAddress` | Remove BTC address from portfolio |
| `/remove_xpub` | `/remove_xpub xpub6CUG...` | Remove HD wallet from portfolio |

### 🔍 Quick Balance Checks

| Command | Usage | Description |
|---------|-------|-------------|
| `/eth` | `/eth 0xAddress` | Check ETH balance across all chains (with USD) |
| `/btc` | `/btc 1BtcAddress` | Check Bitcoin balance (with USD) |
| `/xpub` | `/xpub xpub6CUG...` | Check HD wallet balance (with USD) |

### ℹ️ Information Commands

| Command | Usage | Description |
|---------|-------|-------------|
| `/start` | `/start` | Welcome message and command overview |
| `/help` | `/help` | Detailed help and instructions |
| `/chains` | `/chains` | List all 8 supported EVM chains |

---

## Detailed Command Examples

### Portfolio Workflow

#### Step 1: Add Your Addresses
```
/add_eth 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb
✅ ETH address saved!
You now have 1 ETH address(es) tracked.

/add_btc 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
✅ BTC address saved!
You now have 1 BTC address(es) tracked.
```

#### Step 2: View Your Portfolio
```
/portfolio

💼 YOUR PORTFOLIO
══════════════════════════════
🎯 TOTAL VALUE: $52,345.67
──────────────────────────────
⟠ Ethereum
Total: 2.456789 ETH
Value: $4,567.89
Price: $1,859.23
Addresses: 1

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

#### Step 3: Manage Addresses
```
/addresses

📋 YOUR SAVED ADDRESSES

⟠ Ethereum (1 address):
1. 0x742d35...595f0bEb

₿ Bitcoin (1 address):
1. 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa

💡 Use /portfolio to see your total value
```

### Quick Balance Check (Without Saving)

```
/eth 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb

💰 Multi-Chain Balance Summary

Address: 0x742d35...595f0bEb

📊 TOTAL ETH: 2.456789 ETH
💵 USD Value: $4,567.89
📈 ETH Price: $1,862.45

──────────────────────────────

Balance by Chain:

⟠ Ethereum: 1.234567 ETH
🔵 Base: 0.987654 ETH
🔴 Optimism: 0.234568 ETH
```

```
/btc 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa

₿ Bitcoin Balance

Address: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
Balance: 1.23456789 BTC
💵 USD Value: $47,777.78
📈 BTC Price: $38,650.00
```

### Remove Addresses

```
/remove_eth 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb
✅ ETH address removed from your portfolio.
Remaining addresses: 0
```

```
/remove_btc 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
✅ BTC address removed from your portfolio.
Remaining addresses: 0
```

---

## Feature Comparison

### Quick Check vs Portfolio

| Feature | `/eth <addr>` | `/add_eth` + `/portfolio` |
|---------|---------------|---------------------------|
| Check single address | ✅ | ✅ |
| Check multiple addresses | ❌ | ✅ |
| USD value shown | ✅ | ✅ |
| Save address | ❌ | ✅ |
| Combined ETH + BTC | ❌ | ✅ |
| Asset allocation | ❌ | ✅ |
| One command check | Needs address | Just `/portfolio` |

**Recommendation:** Use portfolio management for addresses you check regularly!

---

## Supported Networks

When you use `/eth <address>`, the bot checks:

| Chain | Type | Native Token | Icon |
|-------|------|--------------|------|
| Ethereum | L1 | ETH | ⟠ |
| Base | L2 | ETH | 🔵 |
| Linea | L2 | ETH | 🟢 |
| Optimism | L2 | ETH | 🔴 |
| Arbitrum | L2 | ETH | 🔷 |
| Unichain | L2 | ETH | 🦄 |
| Polygon | L1 | MATIC | 🟣 |
| BSC | L1 | BNB | 🟡 |

**Total**: 8 EVM chains + Bitcoin

---

## Tips & Tricks

### 💡 Pro Tips

1. **Save addresses you check often** - Use `/add_eth` and `/add_btc` for wallets you monitor regularly
2. **Quick portfolio check** - Just type `/portfolio` anytime to see your total value
3. **Multiple addresses** - Add as many addresses as you want for each asset
4. **No limits** - Track unlimited ETH and BTC addresses
5. **Private & secure** - Addresses stored locally, never shared

### ⚡ Speed Tips

- Portfolio calculation uses parallel processing - even with 10+ addresses it's fast!
- Typical response time: 2-5 seconds
- All chains queried simultaneously

### 🔐 Security Reminders

- ✅ Only public addresses are stored
- ✅ No private keys needed
- ✅ Read-only blockchain access
- ✅ Your data stays on your server
- ⚠️ Never share your bot token

---

## Common Workflows

### Workflow 1: Daily Portfolio Check
```
1. /portfolio
   (See your total value instantly)
```

### Workflow 2: New Wallet Setup
```
1. /add_eth 0xNewWalletAddress
2. /portfolio
   (Now includes the new wallet)
```

### Workflow 3: Check Before Trading
```
1. /portfolio
   (Check current holdings and allocation)
2. Make trading decision based on allocation
```

### Workflow 4: Verify Transaction
```
1. /eth 0xYourAddress
   (Quick check if funds arrived)
2. /add_eth 0xYourAddress
   (If you want to track it permanently)
```

---

**Need help? Send `/help` in the bot!** 🤖
