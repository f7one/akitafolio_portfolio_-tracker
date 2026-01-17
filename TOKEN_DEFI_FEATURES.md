# 🪙 ERC20 Tokens & DeFi Position Tracking

## ✨ New Features

Your Telegram bot now supports comprehensive **ERC20 token tracking** and **DeFi position monitoring** across multiple chains!

---

## 🎯 What's New

### 1. **ERC20 Token Tracking**
- Automatic tracking of popular tokens (USDT, USDC, DAI, WETH, WBTC, LINK, UNI, AAVE)
- Support for custom token additions
- Multi-chain token balances (Ethereum, Base, Arbitrum, Optimism, Polygon)
- Real-time USD valuation via CoinGecko API
- Token balances included in total portfolio value

### 2. **DeFi Position Tracking**
- Aave V3 lending positions across 5 chains
- Shows collateral, debt, and net value
- Health factor monitoring with warnings
- Positions included in total portfolio value
- Toggle on/off as needed

### 3. **Enhanced Portfolio View**
- Total value now includes: ETH + BTC + Tokens + DeFi
- Percentage allocation across all asset types
- Top token holdings displayed
- DeFi position summary
- 24-hour change tracking for entire portfolio

---

## 📋 New Commands

### Token Commands

#### `/tokens` - View All Token Balances
Displays all your ERC20 token holdings across all chains with USD values.

**Example Response:**
```
🪙 YOUR TOKEN HOLDINGS

══════════════════════════════

💰 Total Value: $45,234.56
📊 Tokens: 8

──────────────────────────────

⟠ Ethereum
  • 15000.0000 USDT
    $15,000.00 (@ $1.0000)
  • 10000.0000 USDC
    $10,000.00 (@ $1.0000)
  • 5.5000 WETH
    $9,240.00 (@ $1,680.00)

🔵 Base
  • 5000.0000 USDC
    $5,000.00 (@ $1.0000)
```

#### `/add_token` - Add Custom Token
Track any ERC20 token by providing its contract address.

**Usage:**
```
/add_token <chain> <contract_address> <coingecko_id>
```

**Example:**
```
/add_token ethereum 0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984 uniswap
```

**Supported Chains:**
- ethereum
- base
- arbitrum
- optimism
- polygon

**Finding CoinGecko ID:**
1. Go to https://www.coingecko.com/
2. Search for your token
3. Look at the URL: `coingecko.com/en/coins/{coingecko_id}`

### DeFi Commands

#### `/defi` - View DeFi Positions
Shows all your DeFi lending/borrowing positions.

**Example Response:**
```
🏦 YOUR DeFi POSITIONS

══════════════════════════════

💰 Net Value: $8,450.00
📊 Positions: 2

🔒 Total Collateral: $10,000.00
💳 Total Debt: $1,550.00

──────────────────────────────

⟠ Aave V3 - Ethereum
  Collateral: $6,000.00
  Debt: $1,200.00
  Net: $4,800.00
  ✅ Health Factor: 3.45

🔷 Aave V3 - Arbitrum
  Collateral: $4,000.00
  Debt: $350.00
  Net: $3,650.00
  ✅ Health Factor: 8.12
```

#### `/toggle_defi` - Enable/Disable DeFi Tracking
Turn DeFi position tracking on or off to speed up portfolio calculations.

**Usage:**
```
/toggle_defi
```

---

## 🔄 Updated Commands

### `/portfolio` - Enhanced Portfolio View

Now includes tokens and DeFi positions!

**Example Response:**
```
💼 YOUR PORTFOLIO

══════════════════════════════

🎯 TOTAL VALUE: $152,345.67

📈 24h Change: +$2,450.00 (+1.63%)
🟢 Previous: $149,895.67

──────────────────────────────

⟠ Ethereum
Total: 15.456789 ETH
Value: $25,967.12
Price: $1,680.00
Addresses: 2

₿ Bitcoin
Total: 2.50000000 BTC
Value: $96,625.00
Price: $38,650.00
Addresses: 1

🪙 ERC20 Tokens
Total Value: $21,303.55
Tokens: 12

Top Holdings:
  • 15000.0000 USDT ($15,000.00)
  • 5.5000 WETH ($9,240.00)
  • 500.0000 LINK ($7,350.00)
  • 100.0000 UNI ($650.00)
  • 10.0000 AAVE ($1,050.00)
  ... and 7 more

💡 Use /tokens to see all tokens

🏦 DeFi Positions
Net Value: $8,450.00
Collateral: $10,000.00
Debt: $1,550.00
Positions: 2

💡 Use /defi to see details

──────────────────────────────

📊 Allocation
ETH: 17.0%
BTC: 63.4%
Tokens: 14.0%
DeFi: 5.6%
```

---

## 🪙 Automatically Tracked Tokens

The bot automatically checks for these popular tokens:

### Ethereum Mainnet
- **USDT** (Tether) - Stablecoin
- **USDC** (USD Coin) - Stablecoin
- **DAI** (Dai) - Stablecoin
- **WETH** (Wrapped ETH)
- **WBTC** (Wrapped Bitcoin)
- **LINK** (Chainlink)
- **UNI** (Uniswap)
- **AAVE** (Aave)

### Base
- **USDC** (USD Coin)

### Arbitrum
- **USDC** (USD Coin)
- **USDT** (Tether)

### Optimism
- **USDC** (USD Coin)
- **USDT** (Tether)

### Polygon
- **USDC** (USD Coin)
- **USDT** (Tether)

**Note:** Only tokens with non-zero balances are displayed. Balances under 0.0001 are filtered out as "dust."

---

## 🏦 Supported DeFi Protocols

### Aave V3
Supported on:
- ⟠ **Ethereum** Mainnet
- 🔷 **Arbitrum**
- 🔴 **Optimism**
- 🔵 **Base**
- 🟣 **Polygon**

**Features:**
- Total collateral value
- Total debt value
- Net position value
- Health factor monitoring
- Risk warnings (health factor < 2.0)

**Health Factor Indicators:**
- ✅ **>2.0** - Healthy
- ⚡ **1.5-2.0** - Low (caution advised)
- ⚠️ **<1.5** - RISKY! (risk of liquidation)

---

## 💡 Use Cases

### 1. Complete Portfolio Tracking
Track everything in one place:
```
/add_eth 0xYourAddress
/portfolio
```
See ETH + BTC + all tokens + DeFi positions with total USD value.

### 2. Token Portfolio Management
Monitor your token holdings:
```
/tokens
```
View all tokens grouped by chain with current values.

### 3. DeFi Risk Management
Monitor lending positions and health factors:
```
/defi
```
Get alerts when positions become risky.

### 4. Asset Allocation Analysis
See how your portfolio is distributed:
```
/portfolio
```
View percentage breakdown: ETH vs BTC vs Tokens vs DeFi.

### 5. Track Specific Tokens
Add tokens not in the default list:
```
/add_token ethereum 0xTokenAddress token-id
```

### 6. Speed Optimization
Disable DeFi tracking if you don't use it:
```
/toggle_defi
```

---

## 🔧 Technical Details

### Token Balance Fetching
- Uses standard ERC20 ABI
- Queries `balanceOf()`, `decimals()`, and `symbol()`
- Parallel processing across all chains
- Filters out dust balances (< 0.0001)

### Price Data
- Fetched from CoinGecko API
- Real-time USD prices
- Batch fetching for efficiency
- Automatic fallback for missing prices

### DeFi Integration
- Direct smart contract calls via Web3.py
- Queries `getUserAccountData()` for Aave V3
- Values in USD (8 decimal precision)
- Health factor calculated by protocol

### Performance
- Token balances: 5-10 seconds (parallel queries)
- DeFi positions: 3-5 seconds (parallel queries)
- Full portfolio: 10-15 seconds (everything combined)

---

## 📊 Example Workflows

### Workflow 1: Complete Setup
```bash
# Step 1: Add your ETH addresses
/add_eth 0xYourWallet1 0xYourWallet2

# Step 2: View everything
/portfolio

# Step 3: Check token details
/tokens

# Step 4: Monitor DeFi positions
/defi
```

### Workflow 2: Add Custom Token
```bash
# Find token on CoinGecko
# Copy contract address and CoinGecko ID

# Add token
/add_token ethereum 0x6B3595068778DD592e39A122f4f5a5cF09C90fE2 sushi

# View in portfolio
/portfolio
```

### Workflow 3: DeFi Monitoring
```bash
# Enable DeFi tracking (if disabled)
/toggle_defi

# Check positions
/defi

# View health factors
# If < 2.0, consider adding collateral or paying debt
```

### Workflow 4: Portfolio Optimization
```bash
# Check full portfolio
/portfolio

# See allocation percentages
# Rebalance if needed

# Track changes over 24 hours
```

---

## ⚙️ Storage Structure

Updated `saved_addresses.json` format:
```json
{
  "user_id": {
    "eth": ["0xAddress1", "0xAddress2"],
    "btc": ["btcAddress1"],
    "xpub": ["xpub..."],
    "tokens": [
      {
        "chain": "ethereum",
        "address": "0xTokenAddress",
        "symbol": "TOKEN",
        "decimals": 18,
        "coingecko_id": "token-id"
      }
    ],
    "track_defi": true
  }
}
```

---

## 🔐 Security & Privacy

**What's Queried:**
- ✅ Public token balances (read-only)
- ✅ Public DeFi positions (read-only)
- ✅ No transaction history
- ✅ No private keys needed

**Data Storage:**
- ✅ Stored locally in gitignored file
- ✅ No cloud storage
- ✅ Per-user data isolation
- ✅ Contract addresses only

**Smart Contract Calls:**
- ✅ Read-only function calls
- ✅ Standard ERC20 interface
- ✅ Official protocol contracts (Aave V3)
- ✅ No write operations

---

## 🚀 Future Enhancements

Potential additions:
- [ ] Compound V3 support
- [ ] Uniswap V2/V3 LP positions
- [ ] Curve Finance positions
- [ ] NFT balance tracking
- [ ] Historical token performance
- [ ] Token price alerts
- [ ] DeFi yield tracking
- [ ] Gas cost estimation
- [ ] More L2 chains (zkSync, Scroll, etc.)

---

## 🐛 Troubleshooting

### "No token balances found"
**Possible causes:**
1. You don't hold any of the tracked tokens
2. Your balances are below 0.0001 (filtered as dust)
3. Network error

**Solutions:**
- Add custom tokens with `/add_token`
- Check your addresses with block explorer
- Try again in a moment

### "Failed to validate token"
**Possible causes:**
1. Invalid contract address
2. Not an ERC20 token
3. Wrong chain selected

**Solutions:**
- Verify contract address on block explorer
- Ensure token implements ERC20 standard
- Check chain name (lowercase)

### "No DeFi positions found"
**Possible causes:**
1. You don't have positions on supported protocols
2. DeFi tracking is disabled
3. Only Aave V3 is currently supported

**Solutions:**
- Check if you have Aave V3 positions
- Run `/toggle_defi` to enable tracking
- Wait for more protocol support

### Slow performance
**Solutions:**
- Disable DeFi tracking if not needed: `/toggle_defi`
- Reduce number of custom tokens
- Wait a few seconds between commands (API rate limits)

---

## 📚 API Documentation

### CoinGecko API
- **Endpoint:** `https://api.coingecko.com/api/v3/simple/price`
- **Rate Limit:** 50 calls/minute (free tier)
- **Cost:** Free
- **Data:** Real-time token prices in USD

### Infura RPC
- **Chains:** All 8 EVM chains
- **Rate Limit:** 100,000 requests/day (free tier)
- **Cost:** Free for basic usage
- **Data:** Token balances, DeFi positions

### Blockchain.info
- **Used for:** Bitcoin balances only
- **Rate Limit:** 1 request/10 seconds
- **Cost:** Free
- **Data:** BTC and xpub balances

---

## ✅ Testing Checklist

- [x] ERC20 balance fetching works
- [x] Token prices fetched from CoinGecko
- [x] Custom token addition works
- [x] Aave V3 position fetching works
- [x] Portfolio includes tokens and DeFi
- [x] `/tokens` command displays correctly
- [x] `/defi` command displays correctly
- [x] `/toggle_defi` enables/disables tracking
- [x] Health factor warnings display
- [x] Multi-chain token support
- [x] Dust filtering works
- [x] Allocation percentages calculated correctly
- [x] No linter errors
- [x] Backward compatible with existing data

---

## 🎉 Summary

**Your bot now tracks:**
- ✅ ETH across 8 chains
- ✅ Bitcoin (addresses + xpub)
- ✅ ERC20 tokens (auto + custom)
- ✅ Aave V3 DeFi positions
- ✅ Complete USD valuation
- ✅ 24-hour change tracking
- ✅ Asset allocation

**New commands:**
- `/tokens` - View all tokens
- `/defi` - View DeFi positions
- `/add_token` - Add custom token
- `/toggle_defi` - Toggle DeFi tracking

**Updated commands:**
- `/portfolio` - Now includes tokens & DeFi
- `/start` - Updated with new commands
- `/help` - Comprehensive guide

---

**Your portfolio tracking is now complete! 🚀**
