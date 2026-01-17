# 🚀 Quick Start Guide

## Get Up and Running in 5 Minutes!

### Prerequisites
- Python 3.8+ installed
- Telegram account
- Infura account (free)

---

## Step 1: Get Your API Keys (2 minutes)

### A. Get Telegram Bot Token
1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Follow instructions to create your bot
4. **Copy the token** (looks like: `8504247082:AAEKl2s9qdTl52AudRTUEQRGdzRYpc7WlfI`)

### B. Get Infura Project ID
1. Go to [infura.io](https://infura.io/)
2. Sign up for free account
3. Create a new project
4. **Copy your Project ID** (looks like: `df20b3f6760a45ea87562328e8b02e19`)

---

## Step 2: Install & Configure (2 minutes)

### A. Install Dependencies
```bash
cd tg-balance-bot
pip install -r requirements.txt
```

### B. Create .env File
Create a file named `.env` with this content:
```bash
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
INFURA_PROJECT_ID=your_infura_project_id_here
```

**Replace** `your_telegram_bot_token_here` and `your_infura_project_id_here` with your actual keys!

---

## Step 3: Start the Bot (1 minute)

```bash
python bot.py
```

You should see:
```
🤖 Bot is running...
📡 Monitoring 8 EVM chains + Bitcoin
💼 Portfolio tracking enabled
```

✅ **Done!** Your bot is now live!

---

## Step 4: Use Your Bot (30 seconds)

### Open Telegram
1. Search for your bot name (the one you created with @BotFather)
2. Send `/start`
3. You'll see the welcome message!

### Try These Commands:

**Save an address:**
```
/add_eth 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb
```

**Check your portfolio:**
```
/portfolio
```

**Quick balance check:**
```
/eth 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb
```

---

## 🎯 What Can You Do Now?

### 💼 Portfolio Tracking
```
/add_eth 0xYourAddress    → Save ETH address
/add_btc YourBtcAddress   → Save BTC address
/portfolio                 → See total USD value
/addresses                 → List saved addresses
```

### 🔍 Quick Checks
```
/eth 0xAddress            → Check ETH on all chains
/btc BtcAddress           → Check BTC balance
/chains                   → List all networks
```

---

## 📱 Example Workflow

### Your First Portfolio Check:

1️⃣ **Save your addresses:**
```
You: /add_eth 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb
Bot: ✅ ETH address saved!

You: /add_btc 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
Bot: ✅ BTC address saved!
```

2️⃣ **Check your portfolio:**
```
You: /portfolio
Bot: 
💼 YOUR PORTFOLIO
══════════════════════════════
🎯 TOTAL VALUE: $52,345.67
──────────────────────────────
⟠ Ethereum
Total: 2.456789 ETH
Value: $4,567.89
Addresses: 1

₿ Bitcoin
Total: 1.23456789 BTC
Value: $47,777.78
Addresses: 1
──────────────────────────────
📊 Allocation
ETH: 8.7%
BTC: 91.3%
```

3️⃣ **That's it!** 🎉

---

## 🛠️ Troubleshooting

### Bot doesn't start?
```bash
# Check if dependencies are installed
pip install -r requirements.txt

# Verify .env file exists
ls -la .env

# Check for syntax errors
python -m py_compile bot.py
```

### Can't find bot on Telegram?
- Make sure you got the bot username from @BotFather
- Search by the **exact username** (with @)
- Try refreshing Telegram

### Getting API errors?
- Verify your Infura Project ID is correct
- Check your Telegram Bot Token
- Make sure `.env` file is in the project root

### Bot responds slowly?
- Normal! Querying 8+ chains takes 2-5 seconds
- Wait for the "fetching..." message to complete

---

## 📚 Next Steps

### Learn More:
- **[COMMANDS.md](COMMANDS.md)** - Complete command reference
- **[PORTFOLIO_FEATURES.md](PORTFOLIO_FEATURES.md)** - Portfolio system details
- **[README.md](README.md)** - Full documentation

### Advanced Features:
- Save multiple addresses for each asset
- Track wallets across all chains
- Monitor total portfolio value
- See asset allocation

### Customize:
- Add more chains (edit `bot.py`)
- Modify response format
- Add custom commands
- Integrate with other services

---

## 🎯 Common Use Cases

### Personal Portfolio Tracking
```
/add_eth 0xMyWallet
/add_btc MyBitcoinWallet
/portfolio  (check anytime!)
```

### Monitor Multiple Wallets
```
/add_eth 0xWallet1
/add_eth 0xWallet2
/add_eth 0xWallet3
/portfolio  (see combined value)
```

### Quick Balance Check
```
/eth 0xSomeAddress
(without saving)
```

### Verify Bridge Transactions
```
/eth 0xMyAddress
(check if funds arrived on L2)
```

---

## 🎊 You're All Set!

Your bot is now tracking crypto across:
- ⟠ Ethereum Mainnet
- 🔵 Base
- 🟢 Linea
- 🔴 Optimism
- 🔷 Arbitrum
- 🦄 Unichain
- 🟣 Polygon
- 🟡 BSC
- ₿ Bitcoin

**Total:** 8 EVM chains + Bitcoin = 9 networks!

---

## 💡 Pro Tips

1. **Save addresses you check often** - Use portfolio management
2. **Check `/portfolio` daily** - Monitor your holdings
3. **Add multiple addresses** - Track all your wallets
4. **Use `/chains`** - See all supported networks
5. **Read `/help`** - Discover all features

---

**Need help? Send `/help` in your bot!** 🤖

**Found a bug? Have a feature request? Open an issue on GitHub!** 🐛

---

**Congratulations! You now have a professional crypto portfolio tracker! 🎉**
