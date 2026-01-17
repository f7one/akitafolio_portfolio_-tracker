# Akitafolio 🐕💰

A powerful Telegram bot that tracks your complete crypto portfolio across multiple blockchain networks with **address saving**, **ERC20 token tracking**, **DeFi position monitoring**, and **total portfolio value** calculation. Built with Python using the `python-telegram-bot` library, `web3.py` for blockchain interactions, and real-time price APIs.

## ✨ Key Features

### 💼 Portfolio Management
- 🎯 **Save Multiple Addresses** - Track ETH and BTC addresses in one place
- 🪙 **ERC20 Token Tracking** - Automatic tracking of popular tokens (USDT, USDC, DAI, etc.)
- 🏦 **DeFi Position Monitoring** - Track Aave V3 lending positions across 5 chains
- 📊 **Total Portfolio Value** - Combined USD value of ETH + BTC + Tokens + DeFi
- 💰 **Asset Allocation** - See your ETH/BTC/Tokens/DeFi percentage breakdown
- 🔄 **Easy Management** - Add/remove addresses anytime

### 🔍 Balance Checking
- 🔥 **Aggregated ETH Balance** - Total ETH across ALL chains with one command
- ₿ **Bitcoin Balance** - BTC balance with USD value (including xpub support)
- 🪙 **Token Balances** - All ERC20 tokens across multiple chains
- 🏦 **DeFi Positions** - Lending/borrowing positions with health factors
- 💵 **Real-time USD Conversion** - Live prices from CoinGecko
- 📊 **8 EVM Chains Supported** - Ethereum, Base, Linea, Optimism, Arbitrum, Unichain, Polygon, BSC
- ⚡ **Parallel Processing** - Fetches all chain balances simultaneously
- 🚀 **Single Infura Project ID** - One API key for all chains

## Prerequisites

- Python 3.8 or higher
- A Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- (Optional) Infura API key for Ethereum RPC access

## Installation

### 1. Clone or download this repository

```bash
cd tg-balance-bot
```

### 2. Create a virtual environment (recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Infura Project ID (used for all EVM chains)
INFURA_PROJECT_ID=your_infura_project_id
```

**That's it!** One Infura Project ID works for all 8 chains:
- ⟠ Ethereum Mainnet
- 🔵 Base
- 🟢 Linea
- 🔴 Optimism
- 🔷 Arbitrum
- 🦄 Unichain
- 🟣 Polygon
- 🟡 BSC

#### Getting a Telegram Bot Token:

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the token and paste it in your `.env` file

#### Ethereum RPC URL (Optional):

The bot uses a free public RPC by default. For better reliability, you can use:
- [Infura](https://infura.io/) - Create a free account and get your project ID
- [Alchemy](https://www.alchemy.com/) - Another reliable provider
- Keep the default public RPC: `https://eth.llamarpc.com`

## Usage

### Start the bot

```bash
python bot.py
```

You should see:
```
🤖 Bot is running...
```

### Available Commands

Open your Telegram bot and use these commands:

**Balance Commands:**
- `/eth <address>` - Check **TOTAL ETH balance across ALL chains** (aggregated with USD value)
- `/btc <address>` - Check Bitcoin balance with USD value
- `/xpub <xpub_key>` - Check **HD Wallet balance** (xpub/ypub/zpub) with USD value
- `/tokens` - View all **ERC20 token balances** across chains
- `/defi` - View **DeFi positions** (Aave V3) with health factors
- `/chains` - List all supported blockchain networks

**Portfolio Management:**
- `/add_eth <addr1> <addr2> ...` - Save Ethereum address(es) (single or multiple)
- `/add_btc <addr1> <addr2> ...` - Save Bitcoin address(es) (single or multiple)
- `/add_xpub <key1> <key2> ...` - Save HD wallet(s) (single or multiple)
- `/add_token <chain> <address> <coingecko_id>` - Add custom ERC20 token to track
- `/portfolio` - View your **COMPLETE PORTFOLIO VALUE** (ETH + BTC + Tokens + DeFi in USD)
- `/addresses` - List all your saved addresses and xpub keys
- `/remove_eth <address>` - Remove an ETH address from portfolio
- `/remove_btc <address>` - Remove a BTC address from portfolio
- `/remove_xpub <xpub_key>` - Remove an HD wallet from portfolio
- `/toggle_defi` - Enable/disable DeFi position tracking

**Other Commands:**
- `/start` - Welcome message
- `/help` - Detailed help information

### Examples

#### 1. Portfolio Management (Recommended Workflow)

**Step 1: Save Your Addresses**
```
/add_eth 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb
/add_btc 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
```

**Step 2: View Your Portfolio**
```
/portfolio
```

**Example Portfolio Response:**
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
  ... and 9 more

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

#### 2. Quick Balance Checks

**Check ETH Across All Chains:**
```
/eth 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb
```

Returns:
- Total ETH across all 6 ETH-based chains
- USD value
- Breakdown by chain (Ethereum, Base, Linea, Optimism, Arbitrum, Unichain)
- Also shows MATIC on Polygon and BNB on BSC

**Check Bitcoin Balance:**
```
/btc 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
```

Returns:
- BTC balance
- USD value
- Current BTC price

#### 3. Manage Saved Addresses

**List All Addresses:**
```
/addresses
```

**Remove Address:**
```
/remove_eth 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb
/remove_btc 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
```

## Project Structure

```
tg-balance-bot/
│
├── bot.py                      # Main bot application with portfolio features
├── requirements.txt            # Python dependencies
├── .env                       # Environment variables (create this)
├── config_example.txt         # Configuration example
├── saved_addresses.json       # User portfolio data (auto-created, gitignored)
├── portfolio_history.json     # 24h change tracking (auto-created, gitignored)
├── .gitignore                # Git ignore rules
├── README.md                 # This file
├── TOKEN_DEFI_FEATURES.md    # Token & DeFi documentation
├── MULTI_CHAIN_FEATURES.md   # Multi-chain feature documentation
├── XPUB_GUIDE.md             # HD wallet guide
└── XPUB_IMPLEMENTATION.md    # xpub technical details
```

## Data Storage

The bot stores user data in JSON files:

### saved_addresses.json
- **Format**: JSON file with user ID as key
- **Structure**: Each user has `eth`, `btc`, `xpub`, `tokens`, and `track_defi` fields
- **Privacy**: File is gitignored and only accessible locally
- **Per-User**: Each Telegram user has their own isolated data

Example:
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

### portfolio_history.json
- Stores 30 days of portfolio snapshots
- Used for 24-hour change calculation
- Automatically cleaned up (keeps last 30 days)

## Dependencies

- `python-telegram-bot` - Telegram Bot API wrapper
- `web3` - Ethereum blockchain interaction
- `python-dotenv` - Environment variable management
- `requests` - HTTP library for API calls
- `aiohttp` - Async HTTP client

## APIs Used

- **EVM Chains (8 networks)**: Web3.py with Infura RPC endpoints
  - Ethereum Mainnet
  - Base (L2)
  - Linea (L2)
  - Optimism (L2)
  - Arbitrum (L2)
  - Unichain
  - Polygon
  - BSC
- **Price Data**: CoinGecko API (ETH, BTC, and token prices - free, no key required)
- **Bitcoin**: Blockchain.info public API
- **DeFi Protocols**: Direct smart contract calls (Aave V3 Pool contracts)

## 📊 Use Cases

1. **🎯 Portfolio Tracking** - Monitor your complete crypto portfolio value (ETH + BTC + Tokens + DeFi)
2. **💼 Multi-Address Management** - Track multiple wallets in one place
3. **🪙 Token Holdings** - View all ERC20 token balances across chains
4. **🏦 DeFi Monitoring** - Track lending positions and health factors
5. **📈 Asset Allocation** - See your crypto allocation breakdown
6. **🔍 Cross-Chain Visibility** - View ETH across all L1/L2 chains
7. **💰 USD Valuation** - Real-time portfolio value in dollars
8. **📊 Risk Management** - Monitor DeFi health factors

## 🔐 Privacy & Security

- ✅ Addresses stored locally (not on cloud)
- ✅ `saved_addresses.json` is gitignored
- ✅ No private keys required or stored
- ✅ Read-only blockchain queries
- ✅ Per-user data isolation
- ⚠️ Keep your Telegram bot token secure

## How It Works

### Balance Checking
1. **Single Command** → User sends `/eth <address>` or `/btc <address>`
2. **Parallel Queries** → Bot queries all 8 chains simultaneously for ETH
3. **Smart Aggregation** → Adds up ETH from all ETH-based chains
4. **Price Conversion** → Fetches live prices from CoinGecko (ETH & BTC)
5. **Rich Response** → Shows total, USD value, and per-chain breakdown

### Portfolio Tracking
1. **Save Addresses** → User saves ETH/BTC addresses with `/add_eth` and `/add_btc`
2. **Persistent Storage** → Addresses stored in `saved_addresses.json` (per user)
3. **Portfolio Command** → User sends `/portfolio`
4. **Multi-Chain Query** → Bot fetches balances for ALL saved addresses
5. **Token Balances** → Bot checks popular ERC20 tokens across chains
6. **DeFi Positions** → Bot queries Aave V3 positions (if enabled)
7. **Aggregation** → Calculates total ETH + BTC + Tokens + DeFi in USD
8. **Allocation** → Shows percentage breakdown across asset types
9. **24h Change** → Displays portfolio value change over 24 hours

## Error Handling

The bot includes comprehensive error handling for:
- Invalid addresses
- Network errors
- API failures
- Missing configuration

## Security Notes

⚠️ **Important:**
- Never commit your `.env` file to version control
- Keep your `TELEGRAM_BOT_TOKEN` private
- The `.gitignore` file is configured to exclude `.env` automatically

## Troubleshooting

### Bot doesn't start
- Check that `TELEGRAM_BOT_TOKEN` is set correctly in `.env`
- Ensure all dependencies are installed: `pip install -r requirements.txt`

### Ethereum balance not fetching
- Try using a different RPC URL (Infura, Alchemy, or another public RPC)
- Check your internet connection

### Bitcoin balance not fetching
- The Blockchain.info API might be rate-limited
- Try again after a few moments
- Check if the address is valid

## Contributing

Feel free to fork this project and submit pull requests for any improvements!

## License

This project is open source and available for personal and educational use.

## Disclaimer

This bot is for informational purposes only. Always verify wallet balances through official sources before making any financial decisions.
