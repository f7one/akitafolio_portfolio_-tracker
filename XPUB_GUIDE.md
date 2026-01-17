# 🔑 HD Wallet (xpub) Support Guide

## What is an xpub?

An **xpub (Extended Public Key)** is a master public key for a **Hierarchical Deterministic (HD) wallet**. It allows you to:
- Derive unlimited Bitcoin addresses
- Check balances across all derived addresses
- Track your entire HD wallet without exposing private keys

### xpub Types

| Type | Format | Address Type | Example |
|------|--------|--------------|---------|
| **xpub** | Legacy | P2PKH (1...) | `xpub6CUGRUonZSQ4TWtTMmz...` |
| **ypub** | SegWit | P2SH-P2WPKH (3...) | `ypub6XiW9nhToS1gjVsFKzgmtWZuqo6V1...` |
| **zpub** | Native SegWit | P2WPKH (bc1...) | `zpub6rFR7y4Q2AijBEqTUquhVz398htDFrtymD9...` |

## 🚀 How to Use xpub in Your Bot

### 1. Quick Balance Check

Check the total balance of an HD wallet:

```
/xpub xpub6CUGRUonZSQ4TWtTMmzXdrXDtypWKiKrhko4egpiMZbpiaQL2jkwSB1icqYh2cfDfVxdx4df189oLKnC5fSwqPfgyP3hooxujYzAu3fDVmz
```

**Response:**
```
🔑 HD Wallet Summary

xpub: xpub6CUGRUon...u3fDVmz

══════════════════════════════

💰 Total Balance
1.23456789 BTC
$47,777.78 USD
(@ $38,650.00/BTC)

──────────────────────────────

📊 Statistics
📥 Received: 5.50000000 BTC
📤 Sent: 4.26543211 BTC
🔄 Transactions: 142
```

### 2. Save to Portfolio

Save your xpub for easy tracking:

```
/add_xpub xpub6CUGRUonZSQ4TWtTMmz...
```

Then check your complete portfolio:

```
/portfolio
```

**Portfolio includes:**
- All ETH from saved addresses (across 8 chains)
- All BTC from saved addresses
- All BTC from saved xpub keys (HD wallets)
- **Total combined value in USD**

### 3. Manage HD Wallets

**List saved xpub keys:**
```
/addresses
```

**Remove an xpub:**
```
/remove_xpub xpub6CUGRUonZSQ4TWtTMmz...
```

## 🔍 How It Works

### Behind the Scenes

1. **You provide xpub** → Bot receives your extended public key
2. **API Query** → Bot sends xpub to Blockchain.info API
3. **Address Derivation** → API derives all addresses (m/0/0, m/0/1, m/0/2...)
4. **Balance Aggregation** → API checks balance of each derived address
5. **Total Calculation** → Bot receives total balance across all addresses
6. **USD Conversion** → Bot fetches BTC price and calculates USD value

### What Gets Checked

An xpub can derive addresses in two chains:
- **External chain (m/0/x)**: Receiving addresses (m/0/0, m/0/1, m/0/2...)
- **Internal chain (m/1/x)**: Change addresses (m/1/0, m/1/1, m/1/2...)

The bot checks **all addresses** until it finds 20 consecutive empty ones (gap limit).

## 🔐 Security & Privacy

### ✅ Safe to Share xpub

Your xpub is **safe to use** with this bot because:
- ✅ **Read-only** - Cannot spend funds
- ✅ **No private keys** - Only derives public addresses
- ✅ **View-only access** - Can only check balances
- ✅ **Standard practice** - Used by all Bitcoin wallets for watch-only mode

### ⚠️ Privacy Considerations

While xpub is safe, be aware:
- ⚠️ **Address linkage** - Anyone with your xpub can see all your addresses
- ⚠️ **Balance visibility** - Total balance across all addresses is visible
- ⚠️ **Transaction history** - All transactions are visible

**Recommendation:** Only share xpub with trusted services or for personal tracking.

## 📊 Use Cases

### 1. Hardware Wallet Tracking
Track your Ledger/Trezor balance without connecting device:
```
/add_xpub <your_hardware_wallet_xpub>
/portfolio
```

### 2. Cold Storage Monitoring
Monitor your cold storage without exposing private keys:
```
/xpub <cold_storage_xpub>
```

### 3. Business Wallet Management
Track company Bitcoin holdings:
```
/add_xpub <company_wallet_xpub>
/portfolio  # Check total company holdings
```

### 4. Multi-Wallet Portfolio
Combine multiple HD wallets:
```
/add_xpub <wallet1_xpub>
/add_xpub <wallet2_xpub>
/add_xpub <wallet3_xpub>
/portfolio  # See combined balance
```

## 🎯 Getting Your xpub

### From Popular Wallets

#### Ledger Live
1. Open Ledger Live
2. Go to Account → Settings
3. Click "Advanced"
4. Copy "Extended Public Key"

#### Trezor Suite
1. Open Trezor Suite
2. Select account
3. Go to Details
4. Copy "Public Key (XPUB)"

#### Electrum
1. Open Electrum
2. Wallet → Information
3. Copy "Master Public Key"

#### BlueWallet
1. Open wallet
2. Settings → Export/Backup
3. Copy "Wallet XPUB"

## 📋 Command Reference

| Command | Usage | Description |
|---------|-------|-------------|
| `/xpub <key>` | `/xpub xpub6CUG...` | Check HD wallet balance |
| `/add_xpub <key>` | `/add_xpub xpub6CUG...` | Save to portfolio |
| `/remove_xpub <key>` | `/remove_xpub xpub6CUG...` | Remove from portfolio |
| `/addresses` | `/addresses` | List all saved xpubs |
| `/portfolio` | `/portfolio` | View total (includes xpubs) |

## 🔧 Technical Details

### API Used
- **Blockchain.info Balance API**
- Endpoint: `https://blockchain.info/balance?active={xpub}`
- Rate limit: 1 request per 10 seconds per IP
- Free tier: Unlimited requests (with rate limit)

### Response Time
- Typical: 10-20 seconds
- Depends on number of derived addresses
- More transactions = longer processing time

### Accuracy
- ✅ **100% accurate** - Direct from blockchain nodes
- ✅ **Real-time** - Up-to-date balance
- ✅ **Comprehensive** - Checks all derived addresses

## ❓ FAQ

### Q: What if I have multiple xpubs?
**A:** Add them all! The bot will track each separately and combine them in your portfolio.

### Q: Can I use ypub or zpub?
**A:** Yes! The bot supports xpub, ypub, and zpub formats.

### Q: How often should I check?
**A:** Anytime! But note the 10-second rate limit between requests.

### Q: Will this work with testnet?
**A:** The bot currently supports mainnet only (xpub, ypub, zpub). Testnet keys (tpub, upub, vpub) are validated but may not return accurate data.

### Q: Is my xpub stored securely?
**A:** Yes, it's stored in a local JSON file (`saved_addresses.json`) on your server, which is gitignored.

### Q: Can someone steal my Bitcoin with my xpub?
**A:** No! xpub is read-only. It cannot sign transactions or spend funds.

## 🎉 Example Workflow

### Complete HD Wallet Tracking Setup

1. **Get your xpub from your wallet**
```
(From Ledger Live or Trezor Suite)
```

2. **Check balance once**
```
/xpub xpub6CUGRUonZSQ4TWtTMmz...
```

3. **Save for ongoing tracking**
```
/add_xpub xpub6CUGRUonZSQ4TWtTMmz...
✅ HD Wallet (xpub) saved!
```

4. **Check portfolio anytime**
```
/portfolio

💼 YOUR PORTFOLIO
═══════════════════════
🎯 TOTAL VALUE: $52,345.67

₿ Bitcoin
Total: 1.23456789 BTC
Value: $47,777.78
HD Wallets: 1
```

5. **Add more wallets**
```
/add_eth 0xYourEthAddress
/add_btc 1YourBtcAddress
/add_xpub ypub6XiW9nhToS1gjVsFKzgmtWZuqo...
/portfolio  # Now shows everything!
```

---

**Your complete crypto portfolio, including HD wallets, all in one place! 🔑💰**
