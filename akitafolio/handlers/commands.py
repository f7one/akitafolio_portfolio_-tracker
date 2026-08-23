"""
Telegram command handlers for Akitafolio.

All bot command handlers are defined here, using the services layer
for data fetching and business logic.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from akitafolio.config import settings
from akitafolio.models import Portfolio, PortfolioChange, TokenPortfolio
from akitafolio.services.bitcoin import BitcoinService
from akitafolio.services.blockchain import BlockchainService
from akitafolio.services.defi import DefiService
from akitafolio.services.portfolio import PortfolioService
from akitafolio.services.prices import PriceService
from akitafolio.services.tokens import TokenService
from akitafolio.storage import load_user_addresses, save_user_addresses

logger = logging.getLogger(__name__)


# ============================================================================
# BASIC COMMANDS
# ============================================================================


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when /start is issued."""
    welcome_message = (
        "👋 Welcome to Akitafolio!\n\n"
        "Your multi-chain crypto portfolio tracker.\n\n"
        "📊 **Balance Commands:**\n"
        "/eth <address> - Check ETH balance across all chains\n"
        "/btc <address> - Check Bitcoin balance\n"
        "/xpub <xpub\\_key> - Check HD wallet balance\n\n"
        "💼 **Portfolio Management:**\n"
        "/add\\_eth <addr1> <addr2> ... - Save ETH address(es)\n"
        "/add\\_btc <addr1> <addr2> ... - Save BTC address(es)\n"
        "/add\\_xpub <key1> <key2> ... - Save HD wallet(s)\n"
        "/portfolio - View total portfolio value\n"
        "/addresses - List your saved addresses\n"
        "/remove\\_eth <address> - Remove ETH address\n"
        "/remove\\_btc <address> - Remove BTC address\n"
        "/remove\\_xpub <xpub\\_key> - Remove HD wallet\n\n"
        "🪙 **Token & DeFi Tracking:**\n"
        "/tokens - View all ERC20 token balances\n"
        "/defi - View DeFi positions (Aave, etc.)\n"
        "/add\\_token - Add custom ERC20 token\n"
        "/toggle\\_defi - Enable/disable DeFi tracking\n\n"
        "ℹ️ **Other Commands:**\n"
        "/chains - List all supported chains\n"
        "/convert <xpub> - Convert xpub/ypub/zpub formats\n"
        "/help - Show detailed help\n\n"
        "💡 Tip: You can add multiple addresses at once!"
    )
    await update.message.reply_text(welcome_message, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message when /help is issued."""
    help_message = (
        "🔍 **How to use Akitafolio:**\n\n"
        "**1️⃣ Quick Balance Check**\n"
        "   /eth <address> - Check ETH across all chains\n"
        "   /btc <address> - Check Bitcoin balance\n"
        "   /xpub <xpub\\_key> - Check HD wallet balance\n\n"
        "**2️⃣ Portfolio Tracking**\n"
        "   a) Save your addresses:\n"
        "      /add\\_eth 0xAddr1 0xAddr2 0xAddr3\n"
        "      /add\\_btc btcAddr1 btcAddr2\n"
        "      /add\\_xpub xpub6... ypub6...\n\n"
        "   b) View total portfolio:\n"
        "      /portfolio\n"
        "      Shows total ETH + BTC + Tokens + DeFi!\n"
        "      Includes 24h price change tracking!\n\n"
        "**3️⃣ ERC20 Tokens**\n"
        "   /tokens - View all token balances\n"
        "   Automatically tracks popular tokens\n\n"
        "**4️⃣ DeFi Positions**\n"
        "   /defi - View lending/borrowing positions\n"
        "   /toggle\\_defi - Enable/disable DeFi tracking\n"
        "   Supports: Aave V3 on multiple chains\n\n"
        "**5️⃣ Tools**\n"
        "   /convert <xpub> - Convert xpub/ypub/zpub\n"
        "   (Ledger users: auto-detection built-in!)\n\n"
        "💰 **Features:**\n"
        "• Track multiple addresses\n"
        "• Aggregated ETH from all L1/L2 chains\n"
        "• ERC20 tokens (USDT, USDC, DAI, etc.)\n"
        "• DeFi positions (Aave V3)\n"
        "• 24-hour portfolio change tracking\n"
        "• Real-time prices from CoinGecko\n"
        "• Auto-detect SegWit format for xpub"
    )
    await update.message.reply_text(help_message, parse_mode="Markdown")


async def chains_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all supported chains."""
    eth_chains = settings.get_eth_chains()
    other_chains = settings.get_other_chains()
    all_chains = settings.get_all_chains()

    chains_info = "🔗 **Supported Blockchain Networks**\n\n"

    chains_info += "**ETH Chains (counted in total):**\n"
    for chain, config in eth_chains.items():
        chains_info += f"{config['emoji']} {config['name']} ({config['symbol']})\n"

    chains_info += "\n**Other Chains:**\n"
    for chain, config in other_chains.items():
        chains_info += f"{config['emoji']} {config['name']} ({config['symbol']})\n"

    chains_info += "\n₿ **Bitcoin** (BTC)\n"
    chains_info += f"\n📊 Total: {len(all_chains)} EVM chains + Bitcoin"

    await update.message.reply_text(chains_info, parse_mode="Markdown")


async def convert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Convert xpub between different formats (xpub/ypub/zpub)."""
    from akitafolio.services.bitcoin import convert_xpub

    if not context.args:
        await update.message.reply_text(
            "🔄 **xpub Format Converter**\n\n"
            "Convert extended public keys between formats.\n\n"
            "**Usage:** /convert <xpub\\_key>\n\n"
            "**Supported formats:**\n"
            "• `xpub` - Legacy (P2PKH)\n"
            "• `ypub` - SegWit wrapped (P2SH-P2WPKH)\n"
            "• `zpub` - Native SegWit (P2WPKH)\n\n"
            "💡 Ledger exports xpub, but SegWit wallets need zpub/ypub "
            "for correct balance lookup.",
            parse_mode="Markdown",
        )
        return

    xpub = context.args[0]

    # Validate input
    valid_prefixes = ("xpub", "ypub", "zpub")
    if not any(xpub.startswith(p) for p in valid_prefixes):
        await update.message.reply_text(
            "❌ Invalid key format.\n" "Key must start with xpub, ypub, or zpub."
        )
        return

    if not (100 <= len(xpub) <= 120):
        await update.message.reply_text("❌ Invalid key length.")
        return

    # Detect current format
    current_format = None
    for prefix in valid_prefixes:
        if xpub.startswith(prefix):
            current_format = prefix
            break

    # Convert to all formats
    response = "🔄 **xpub Format Conversion**\n\n"
    response += f"**Input:** `{xpub[:20]}...`\n"
    response += f"**Current format:** {current_format}\n\n"
    response += "**Converted keys:**\n\n"

    for target in valid_prefixes:
        if target == current_format:
            response += f"**{target}** (original):\n"
            response += f"`{xpub}`\n\n"
        else:
            converted = convert_xpub(xpub, target)
            if converted:
                response += f"**{target}**:\n"
                response += f"`{converted}`\n\n"
            else:
                response += f"**{target}**: ❌ Conversion failed\n\n"

    response += "💡 Copy the format you need and use it in block explorers or wallets."

    await update.message.reply_text(response, parse_mode="Markdown")


# ============================================================================
# BALANCE COMMANDS
# ============================================================================


async def eth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check ETH balance across all chains."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide an Ethereum address.\n"
            "Usage: /eth <address>\n"
            "Example: /eth 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
        )
        return

    address = context.args[0]

    processing_msg = await update.message.reply_text("🔄 Fetching balances across all chains... ⏳")

    result = await BlockchainService.get_all_chain_balances(address)
    prices = await PriceService.get_crypto_prices()

    if result.error:
        await processing_msg.edit_text(f"❌ Error: {result.error}")
        return

    # Build response
    response = "💰 **Multi-Chain Balance Summary**\n\n"
    response += f"Address: `{address[:10]}...{address[-8:]}`\n\n"

    total_usd = result.total_eth * prices.eth if prices.eth > 0 else 0

    response += f"📊 **TOTAL ETH: {result.total_eth:.6f} ETH**\n"
    if prices.eth > 0:
        response += f"💵 **USD Value: ${total_usd:,.2f}**\n"
        response += f"📈 ETH Price: ${prices.eth:,.2f}\n"
    response += "\n" + "─" * 30 + "\n\n"

    response += "**Balance by Chain:**\n\n"

    for chain_data in result.chain_balances:
        if chain_data.balance > 0:
            response += f"{chain_data.emoji} **{chain_data.network}**: {chain_data.balance:.6f} {chain_data.currency}\n"

    if result.total_eth == 0:
        response += "📊 No balances found on any chain.\n"

    await processing_msg.edit_text(response, parse_mode="Markdown")


async def btc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check Bitcoin balance."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide a Bitcoin address.\n"
            "Usage: /btc <bitcoin_address>\n"
            "Example: /btc 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        )
        return

    address = context.args[0]

    processing_msg = await update.message.reply_text("🔄 Fetching Bitcoin balance... ⏳")

    result = await BitcoinService.get_address_balance(address)
    prices = await PriceService.get_crypto_prices()

    if result.get("error"):
        await processing_msg.edit_text(f"❌ Error: {result['error']}")
        return

    balance = result["balance"]
    usd_value = balance * prices.btc if prices.btc > 0 else 0

    response = "₿ **Bitcoin Balance**\n\n"
    response += f"Address: `{address[:10]}...{address[-8:]}`\n\n"
    response += f"💰 **Balance: {balance:.8f} BTC**\n"
    if prices.btc > 0:
        response += f"💵 **USD Value: ${usd_value:,.2f}**\n"
        response += f"📈 BTC Price: ${prices.btc:,.2f}"

    await processing_msg.edit_text(response, parse_mode="Markdown")


async def xpub_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check HD wallet balance using xpub."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide an xpub/ypub/zpub key.\n"
            "Usage: /xpub <xpub\\_key>\n"
            "Example: /xpub xpub6CUG...\n\n"
            "💡 Tip: Ledger users can use their xpub directly - "
            "the bot will auto-detect SegWit format!"
        )
        return

    xpub = context.args[0]

    processing_msg = await update.message.reply_text(
        "🔄 Fetching HD wallet balance...\n" "Trying different address formats ⏳"
    )

    result = await BitcoinService.get_xpub_balance(xpub)
    prices = await PriceService.get_crypto_prices()

    if result.get("error"):
        await processing_msg.edit_text(f"❌ Error: {result['error']}")
        return

    balance = result["balance"]
    usd_value = balance * prices.btc if prices.btc > 0 else 0

    response = "🔑 **HD Wallet Balance**\n\n"
    response += f"Key: `{xpub[:15]}...{xpub[-10:]}`\n"

    # Show which format was used if conversion happened
    used_format = result.get("used_format")
    if used_format and result.get("converted_key"):
        response += f"📍 Format: {used_format} (auto-detected)\n"
    elif used_format:
        response += f"📍 Format: {used_format}\n"

    response += f"\n💰 **Balance: {balance:.8f} BTC**\n"
    if prices.btc > 0:
        response += f"💵 **USD Value: ${usd_value:,.2f}**\n"
    response += f"\n📊 Transactions: {result.get('transaction_count', 0)}"

    await processing_msg.edit_text(response, parse_mode="Markdown")


# ============================================================================
# ADDRESS MANAGEMENT
# ============================================================================


async def add_eth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add ETH address(es) to portfolio."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide ETH address(es).\n" "Usage: /add_eth <address1> <address2> ..."
        )
        return

    user_id = update.effective_user.id
    addresses = load_user_addresses(user_id)

    added = []
    skipped = []
    invalid = []

    for addr in context.args:
        if not BlockchainService.is_valid_address(addr):
            invalid.append(addr)
            continue

        checksum_addr = BlockchainService.checksum_address(addr)
        if checksum_addr in addresses.eth:
            skipped.append(addr)
        else:
            addresses.eth.append(checksum_addr)
            added.append(checksum_addr)

    if added:
        save_user_addresses(user_id, addresses)

    response = ""
    if added:
        response += f"✅ Added {len(added)} address(es)\n"
    if skipped:
        response += f"⏭️ Skipped {len(skipped)} (already saved)\n"
    if invalid:
        response += f"❌ Invalid: {len(invalid)} address(es)\n"

    response += f"\n📊 Total ETH addresses: {len(addresses.eth)}"

    await update.message.reply_text(response)


async def add_btc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add BTC address(es) to portfolio."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide BTC address(es).\n" "Usage: /add_btc <address1> <address2> ..."
        )
        return

    user_id = update.effective_user.id
    addresses = load_user_addresses(user_id)

    added = []
    skipped = []
    invalid = []

    for addr in context.args:
        if not BitcoinService.is_valid_btc_address(addr):
            invalid.append(addr)
            continue

        if addr in addresses.btc:
            skipped.append(addr)
        else:
            addresses.btc.append(addr)
            added.append(addr)

    if added:
        save_user_addresses(user_id, addresses)

    response = ""
    if added:
        response += f"✅ Added {len(added)} address(es)\n"
    if skipped:
        response += f"⏭️ Skipped {len(skipped)} (already saved)\n"
    if invalid:
        response += f"❌ Invalid: {len(invalid)} address(es)\n"

    response += f"\n📊 Total BTC addresses: {len(addresses.btc)}"

    await update.message.reply_text(response)


async def add_xpub_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add xpub key(s) to portfolio."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide xpub key(s).\n" "Usage: /add_xpub <xpub1> <xpub2> ..."
        )
        return

    user_id = update.effective_user.id
    addresses = load_user_addresses(user_id)

    added = []
    skipped = []
    invalid = []

    for xpub in context.args:
        if not BitcoinService.is_valid_xpub(xpub):
            invalid.append(xpub)
            continue

        if xpub in addresses.xpub:
            skipped.append(xpub)
        else:
            addresses.xpub.append(xpub)
            added.append(xpub)

    if added:
        save_user_addresses(user_id, addresses)

    response = ""
    if added:
        response += f"✅ Added {len(added)} xpub key(s)\n"
    if skipped:
        response += f"⏭️ Skipped {len(skipped)} (already saved)\n"
    if invalid:
        response += f"❌ Invalid: {len(invalid)} xpub key(s)\n"

    response += f"\n📊 Total xpub keys: {len(addresses.xpub)}"

    await update.message.reply_text(response)


async def remove_eth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove ETH address from portfolio."""
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /remove_eth <address>")
        return

    user_id = update.effective_user.id
    addresses = load_user_addresses(user_id)
    address = context.args[0]

    # Try to find and remove (case-insensitive)
    removed = False
    for saved_addr in addresses.eth[:]:
        if saved_addr.lower() == address.lower():
            addresses.eth.remove(saved_addr)
            removed = True
            break

    if removed:
        save_user_addresses(user_id, addresses)
        await update.message.reply_text("✅ Removed ETH address")
    else:
        await update.message.reply_text("❌ Address not found in your saved addresses")


async def remove_btc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove BTC address from portfolio."""
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /remove_btc <address>")
        return

    user_id = update.effective_user.id
    addresses = load_user_addresses(user_id)
    address = context.args[0]

    if address in addresses.btc:
        addresses.btc.remove(address)
        save_user_addresses(user_id, addresses)
        await update.message.reply_text("✅ Removed BTC address")
    else:
        await update.message.reply_text("❌ Address not found in your saved addresses")


async def remove_xpub_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove xpub key from portfolio."""
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /remove_xpub <xpub>")
        return

    user_id = update.effective_user.id
    addresses = load_user_addresses(user_id)
    xpub = context.args[0]

    if xpub in addresses.xpub:
        addresses.xpub.remove(xpub)
        save_user_addresses(user_id, addresses)
        await update.message.reply_text("✅ Removed xpub key")
    else:
        await update.message.reply_text("❌ xpub not found in your saved keys")


async def addresses_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all saved addresses."""
    user_id = update.effective_user.id
    addresses = load_user_addresses(user_id)

    if not addresses.has_addresses():
        await update.message.reply_text(
            "📭 No saved addresses yet.\n\n"
            "Use /add_eth, /add_btc, or /add_xpub to add addresses."
        )
        return

    response = "📋 **Your Saved Addresses**\n\n"

    if addresses.eth:
        response += f"**ETH Addresses ({len(addresses.eth)}):**\n"
        for addr in addresses.eth:
            response += f"• `{addr[:10]}...{addr[-8:]}`\n"
        response += "\n"

    if addresses.btc:
        response += f"**BTC Addresses ({len(addresses.btc)}):**\n"
        for addr in addresses.btc:
            response += f"• `{addr[:10]}...{addr[-8:]}`\n"
        response += "\n"

    if addresses.xpub:
        response += f"**HD Wallets ({len(addresses.xpub)}):**\n"
        for xpub in addresses.xpub:
            response += f"• `{xpub[:15]}...{xpub[-10:]}`\n"

    response += f"\n🔧 DeFi Tracking: {'✅ Enabled' if addresses.track_defi else '❌ Disabled'}"

    await update.message.reply_text(response, parse_mode="Markdown")


# ============================================================================
# PORTFOLIO COMMAND
# ============================================================================


def format_portfolio_message(portfolio: Portfolio, change: PortfolioChange) -> str:
    """Format a complete portfolio response without Telegram side effects."""
    response = "💼 **YOUR PORTFOLIO**\n\n"
    response += "══════════════════════════════\n\n"
    response += f"💰 **Total Value: ${portfolio.total_portfolio_usd:,.2f}**\n\n"

    if change.has_data:
        emoji = "📈" if change.change_usd >= 0 else "📉"
        sign = "+" if change.change_usd >= 0 else ""
        response += (
            f"{emoji} 24h Change: {sign}${change.change_usd:,.2f} "
            f"({sign}{change.change_percent:.2f}%)\n\n"
        )

    response += "──────────────────────────────\n\n"

    if portfolio.total_eth > 0:
        response += "⟠ **ETH Holdings**\n"
        response += f"   Amount: {portfolio.total_eth:.6f} ETH\n"
        response += f"   Value: ${portfolio.total_eth_usd:,.2f}\n"
        response += f"   Price: ${portfolio.eth_price:,.2f}\n\n"

    if portfolio.total_btc_combined > 0:
        response += "₿ **BTC Holdings**\n"
        response += f"   Amount: {portfolio.total_btc_combined:.8f} BTC\n"
        response += f"   Value: ${portfolio.total_btc_usd:,.2f}\n"
        response += f"   Price: ${portfolio.btc_price:,.2f}\n\n"

    if portfolio.tokens and portfolio.tokens.token_count > 0:
        response += "🪙 **Token Holdings**\n"
        response += f"   Total Value: ${portfolio.tokens.total_value_usd:,.2f}\n"
        response += f"   Token Count: {portfolio.tokens.token_count}\n"
        if portfolio.tokens.top_holdings:
            response += "   Top Holdings:\n"
            for token in portfolio.tokens.top_holdings[:3]:
                response += f"   • {token.symbol}: ${token.value_usd:,.2f}\n"
        response += "\n"

    if portfolio.defi and portfolio.defi.position_count > 0:
        response += "🏦 **DeFi Positions**\n"
        response += f"   Net Value: ${portfolio.defi.total_net_value_usd:,.2f}\n"
        response += f"   Collateral: ${portfolio.defi.total_collateral_usd:,.2f}\n"
        response += f"   Debt: ${portfolio.defi.total_debt_usd:,.2f}\n"
        response += f"   Positions: {portfolio.defi.position_count}\n"

    return response


def format_tokens_message(token_portfolio: TokenPortfolio) -> str:
    """Format visible token balances without Telegram side effects."""
    response = "🪙 **YOUR TOKEN BALANCES**\n\n"
    response += f"💰 Total Value: ${token_portfolio.total_value_usd:,.2f}\n"
    response += f"📊 Tokens: {token_portfolio.token_count}\n\n"
    response += "──────────────────────────────\n\n"

    for token in token_portfolio.tokens[:15]:
        response += f"**{token.symbol}** ({token.chain})\n"
        response += f"   Balance: {token.balance:.6f}\n"
        response += f"   Value: ${token.value_usd:,.2f}\n\n"

    if token_portfolio.token_count > 15:
        response += f"...and {token_portfolio.token_count - 15} more tokens\n"

    if token_portfolio.hidden_dust_count > 0:
        response += (
            f"\n🔹 {token_portfolio.hidden_dust_count} token(s) hidden "
            f"(< $1.00, total ${token_portfolio.hidden_dust_value_usd:,.2f})"
        )

    return response


async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show complete portfolio value."""
    user_id = update.effective_user.id
    addresses = load_user_addresses(user_id)

    if not addresses.has_addresses():
        await update.message.reply_text(
            "📭 No saved addresses yet.\n\n"
            "Use /add_eth, /add_btc, or /add_xpub to add addresses."
        )
        return

    processing_msg = await update.message.reply_text(
        "🔄 Calculating portfolio value...\n" "Fetching from all chains, tokens, and DeFi ⏳"
    )

    # Get portfolio data
    portfolio = await PortfolioService.get_portfolio(
        addresses, include_tokens=True, include_defi=addresses.track_defi
    )

    # Calculate 24h change
    change = PortfolioService.calculate_24h_change(user_id, portfolio.total_portfolio_usd)

    # Save snapshot
    PortfolioService.save_snapshot(user_id, portfolio)

    response = format_portfolio_message(portfolio, change)
    await processing_msg.edit_text(response, parse_mode="Markdown")


# ============================================================================
# TOKEN & DEFI COMMANDS
# ============================================================================


async def tokens_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all ERC20 token balances."""
    user_id = update.effective_user.id
    addresses = load_user_addresses(user_id)

    if not addresses.eth:
        await update.message.reply_text(
            "📭 No ETH addresses saved.\n" "Add addresses with /add_eth to track tokens."
        )
        return

    processing_msg = await update.message.reply_text("🔄 Fetching token balances... ⏳")

    token_portfolio = await TokenService.get_all_token_balances(addresses.eth, addresses.tokens)

    if token_portfolio.token_count == 0:
        await processing_msg.edit_text("📊 No token balances found.")
        return

    response = format_tokens_message(token_portfolio)
    await processing_msg.edit_text(response, parse_mode="Markdown")


async def defi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show DeFi positions."""
    user_id = update.effective_user.id
    addresses = load_user_addresses(user_id)

    if not addresses.eth:
        await update.message.reply_text(
            "📭 No ETH addresses saved.\n" "Add addresses with /add_eth to track DeFi positions."
        )
        return

    processing_msg = await update.message.reply_text("🔄 Fetching DeFi positions... ⏳")

    defi_portfolio = await DefiService.get_all_defi_positions(addresses.eth)

    if defi_portfolio.position_count == 0:
        await processing_msg.edit_text("📊 No DeFi positions found.")
        return

    response = "🏦 **YOUR DeFi POSITIONS**\n\n"
    response += "══════════════════════════════\n\n"
    response += f"💰 Net Value: ${defi_portfolio.total_net_value_usd:,.2f}\n"
    response += f"📊 Positions: {defi_portfolio.position_count}\n\n"
    response += f"🔒 Total Collateral: ${defi_portfolio.total_collateral_usd:,.2f}\n"
    response += f"💳 Total Debt: ${defi_portfolio.total_debt_usd:,.2f}\n\n"
    response += "──────────────────────────────\n\n"

    for pos in defi_portfolio.positions:
        all_chains = settings.get_all_chains()
        chain_emoji = all_chains.get(pos.chain, {}).get("emoji", "•")
        response += f"{chain_emoji} **{pos.protocol} - {pos.chain.title()}**\n"
        response += f"   Collateral: ${pos.collateral_usd:,.2f}\n"
        response += f"   Debt: ${pos.debt_usd:,.2f}\n"
        response += f"   Net: ${pos.net_value_usd:,.2f}\n"
        response += f"   Health Factor: {pos.health_factor_display}\n\n"

    await processing_msg.edit_text(response, parse_mode="Markdown")


async def add_token_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add custom token to track."""
    if len(context.args) < 3:
        await update.message.reply_text(
            "⚠️ Usage: /add_token <chain> <contract_address> <coingecko_id>\n\n"
            "Example:\n"
            "/add_token ethereum 0x1234... uniswap"
        )
        return

    chain = context.args[0].lower()
    token_address = context.args[1]
    coingecko_id = context.args[2].lower()

    all_chains = settings.get_all_chains()
    if chain not in all_chains:
        await update.message.reply_text(f"❌ Unsupported chain: {chain}")
        return

    if not BlockchainService.is_valid_address(token_address):
        await update.message.reply_text("❌ Invalid token contract address")
        return

    user_id = update.effective_user.id
    addresses = load_user_addresses(user_id)

    new_token = {
        "chain": chain,
        "address": BlockchainService.checksum_address(token_address),
        "coingecko_id": coingecko_id,
        "decimals": 18,  # Default, will be auto-detected
        "symbol": coingecko_id.upper(),
    }

    addresses.tokens.append(new_token)
    save_user_addresses(user_id, addresses)

    await update.message.reply_text(
        f"✅ Added custom token!\n" f"Chain: {chain}\n" f"CoinGecko ID: {coingecko_id}"
    )


async def toggle_defi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle DeFi tracking on/off."""
    user_id = update.effective_user.id
    addresses = load_user_addresses(user_id)

    addresses.track_defi = not addresses.track_defi
    save_user_addresses(user_id, addresses)

    status = "✅ Enabled" if addresses.track_defi else "❌ Disabled"
    await update.message.reply_text(f"🏦 DeFi Tracking: {status}")


# ============================================================================
# ERROR HANDLER
# ============================================================================


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in the bot."""
    logger.error(f"Exception while handling an update: {context.error}")

    if update and hasattr(update, "effective_message") and update.effective_message:
        await update.effective_message.reply_text("❌ An error occurred. Please try again later.")
