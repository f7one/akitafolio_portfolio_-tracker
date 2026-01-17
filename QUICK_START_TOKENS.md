# 🚀 Quick Start Guide - Token & DeFi Features

## New to Token & DeFi Tracking?

This guide will get you started with the new features in 5 minutes!

---

## Step 1: Check Your Portfolio (Already Setup)

If you already have ETH addresses saved:

```
/portfolio
```

You'll now see:
- ✅ Your ETH balance
- ✅ Your BTC balance
- ✅ **NEW:** Your ERC20 token balances
- ✅ **NEW:** Your DeFi positions
- ✅ Total value including everything!

---

## Step 2: View Your Tokens

```
/tokens
```

**What you'll see:**
- All ERC20 tokens you hold (USDT, USDC, DAI, WETH, etc.)
- Grouped by blockchain
- USD value for each token
- Total token value

**Automatically tracked tokens:**
- USDT, USDC, DAI (Stablecoins)
- WETH, WBTC (Wrapped assets)
- LINK, UNI, AAVE (Popular tokens)

---

## Step 3: Check Your DeFi Positions

```
/defi
```

**What you'll see:**
- Aave V3 lending positions
- Collateral and debt amounts
- Health factor warnings
- Net position value

**Supported chains:**
- Ethereum, Arbitrum, Optimism, Base, Polygon

---

## Step 4: Add a Custom Token (Optional)

Want to track a token not in the default list?

```
/add_token ethereum 0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984 uniswap
```

**Format:**
```
/add_token <chain> <contract_address> <coingecko_id>
```

**Finding the CoinGecko ID:**
1. Go to https://www.coingecko.com/
2. Search for your token
3. Look at the URL: `coingecko.com/en/coins/{id}`
4. Use that `{id}` in the command

---

## Step 5: Speed Optimization (Optional)

If you don't use DeFi, you can disable position tracking to speed up portfolio calculations:

```
/toggle_defi
```

This will toggle DeFi tracking on/off.

---

## Example Session

```bash
# 1. View complete portfolio
/portfolio

💼 YOUR PORTFOLIO
🎯 TOTAL VALUE: $52,345.67

⟠ Ethereum: 15.456 ETH ($25,967.12)
₿ Bitcoin: 1.5 BTC ($58,000.00)
🪙 Tokens: $15,000.00 (8 tokens)
🏦 DeFi: $3,378.55 (2 positions)

📊 Allocation
ETH: 49.6%
BTC: 31.1%
Tokens: 28.7%
DeFi: 6.5%

# 2. See token details
/tokens

🪙 YOUR TOKEN HOLDINGS
💰 Total Value: $15,000.00

⟠ Ethereum
  • 10000.0000 USDT ($10,000.00)
  • 3.0000 WETH ($5,040.00)

# 3. Check DeFi positions
/defi

🏦 YOUR DeFi POSITIONS
💰 Net Value: $3,378.55

⟠ Aave V3 - Ethereum
  Collateral: $5,000.00
  Debt: $1,621.45
  Net: $3,378.55
  ✅ Health Factor: 2.45

# 4. Add custom token
/add_token ethereum 0x6B3595068778DD592e39A122f4f5a5cF09C90fE2 sushi

✅ Token added successfully!
Token: SUSHI
Chain: Ethereum
```

---

## Frequently Asked Questions

### Q: Will this slow down my portfolio?
**A:** The bot uses parallel processing. Portfolio calculation takes 10-15 seconds total, regardless of how many tokens you have.

### Q: Which tokens are automatically tracked?
**A:** USDT, USDC, DAI, WETH, WBTC, LINK, UNI, AAVE on Ethereum. Plus USDC/USDT on other chains.

### Q: What if I don't have any tokens?
**A:** The bot will simply show "No token balances found" and your portfolio will only show ETH/BTC.

### Q: Can I remove the token tracking?
**A:** You can't disable automatic token tracking, but you can disable DeFi tracking with `/toggle_defi`.

### Q: Which DeFi protocols are supported?
**A:** Currently only Aave V3. More protocols (Compound, Uniswap) coming in future updates.

### Q: What is "health factor"?
**A:** It's a risk metric for lending positions:
- **> 2.0** = Healthy ✅
- **1.5-2.0** = Low (caution) ⚡
- **< 1.5** = Risky (liquidation risk) ⚠️

### Q: Does this use my private keys?
**A:** No! The bot only reads public blockchain data. It never needs or stores private keys.

---

## All New Commands

| Command | What It Does |
|---------|--------------|
| `/tokens` | View all your ERC20 token balances |
| `/defi` | View your DeFi lending positions |
| `/add_token` | Add a custom ERC20 token to track |
| `/toggle_defi` | Turn DeFi tracking on/off |

---

## Tips & Tricks

1. **Check regularly:** Run `/portfolio` daily to track your 24h changes
2. **Monitor health factors:** Check `/defi` if you have lending positions
3. **Add important tokens:** Use `/add_token` for tokens you care about
4. **Optimize for speed:** Disable DeFi if you don't use it
5. **Cross-chain awareness:** Tokens are checked on ALL chains automatically

---

## What's Included in Portfolio Now?

Your `/portfolio` command now shows:

```
🎯 TOTAL VALUE
   └─ ETH (all chains combined)
   └─ BTC (addresses + xpub)
   └─ ERC20 Tokens (all chains)
   └─ DeFi Positions (net value)

📊 Allocation
   └─ % of ETH
   └─ % of BTC
   └─ % of Tokens
   └─ % of DeFi
```

---

## Need More Help?

- **Detailed Guide:** See `TOKEN_DEFI_FEATURES.md`
- **Bot Help:** Send `/help` in Telegram
- **Command List:** Send `/start` in Telegram

---

**Ready to try it? Just send `/portfolio` to your bot! 🚀**
