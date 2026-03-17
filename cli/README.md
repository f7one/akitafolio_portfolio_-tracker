# Akitafolio CLI

Command-line interface for the multi-chain crypto portfolio tracker. Provides the same features as the Telegram bot.

## Prerequisites

- Python 3.11+
- `INFURA_PROJECT_ID` set in `.env` at the project root

## Installation

From the project root:

```bash
pip install -r requirements.txt
```

## Usage

Run commands via the Python module:

```bash
python -m cli.main <command> [arguments]
```

On the server (after deployment via `deploy.sh`), the `akitafolio` wrapper is available system-wide:

```bash
akitafolio <command> [arguments]
```

## Connecting to your Telegram portfolio

If you already use the Telegram bot, the CLI can access the same saved addresses and portfolio history. Pass your Telegram user ID with the `--user-id` flag:

```bash
akitafolio --user-id <your_telegram_id> portfolio
```

To find your Telegram user ID:

1. Open Telegram and message [@userinfobot](https://t.me/userinfobot) — it replies with your ID instantly.
2. Or check the storage file on the server: `cat /opt/tg-balance-bot/saved_addresses.json | python3 -m json.tool` — the top-level keys are Telegram user IDs.

Without `--user-id`, the CLI uses a standalone profile (user ID `1`).

## Commands

### Balance checks

```bash
akitafolio eth <address>             # ETH balance across all chains
akitafolio btc <address>             # Bitcoin balance
akitafolio xpub <key>                # HD wallet balance (xpub/ypub/zpub)
```

### Address management

```bash
akitafolio add-eth <addr1> [addr2 ...]       # Save ETH address(es)
akitafolio add-btc <addr1> [addr2 ...]       # Save BTC address(es)
akitafolio add-xpub <key1> [key2 ...]        # Save HD wallet key(s)
akitafolio remove-eth <address>              # Remove ETH address
akitafolio remove-btc <address>              # Remove BTC address
akitafolio remove-xpub <key>                 # Remove HD wallet key
akitafolio addresses                         # List all saved addresses
```

### Portfolio

```bash
akitafolio portfolio                 # Full portfolio with 24h change
akitafolio tokens                    # ERC20 token balances
akitafolio defi                      # DeFi positions (Aave V3)
akitafolio toggle-defi               # Toggle DeFi tracking on/off
akitafolio add-token <chain> <contract_address> <coingecko_id>  # Add custom token
```

### Utilities

```bash
akitafolio chains                    # List supported blockchain networks
akitafolio convert <xpub_key>        # Convert between xpub/ypub/zpub formats
```

## Supported chains

| Chain    | Symbol | Notes                  |
|----------|--------|------------------------|
| Ethereum | ETH    | Counted in ETH total   |
| Base     | ETH    | Counted in ETH total   |
| Linea    | ETH    | Counted in ETH total   |
| Optimism | ETH    | Counted in ETH total   |
| Arbitrum | ETH    | Counted in ETH total   |
| Unichain | ETH    | Counted in ETH total   |
| Polygon  | MATIC  | Separate balance       |
| BSC      | BNB    | Separate balance       |
| Bitcoin  | BTC    | Via Blockchain.info    |
