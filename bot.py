#!/usr/bin/env python3
"""
Akitafolio - Multi-Chain Crypto Portfolio Tracker

A Telegram bot for tracking cryptocurrency portfolios across multiple EVM chains,
Bitcoin addresses, and DeFi positions.

This is the refactored entry point using the modular package structure.
"""

import logging
import asyncio

from telegram import Update
from telegram.ext import Application, CommandHandler

from akitafolio.config import settings
from akitafolio.http_client import HTTPClient, SecretsFilter
from akitafolio.cache import cache_manager
from akitafolio.handlers import (
    start_command,
    help_command,
    chains_command,
    convert_command,
    eth_command,
    btc_command,
    xpub_command,
    add_eth_command,
    add_btc_command,
    add_xpub_command,
    remove_eth_command,
    remove_btc_command,
    remove_xpub_command,
    addresses_command,
    portfolio_command,
    tokens_command,
    defi_command,
    add_token_command,
    toggle_defi_command,
    error_handler,
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logger.addFilter(SecretsFilter())


async def post_init(application: Application) -> None:
    """Post-initialization hook - start background tasks."""
    logger.info("Application initialized successfully")
    # Start cache cleanup task
    await cache_manager.start_cleanup_task(interval=300.0)


async def post_shutdown(application: Application) -> None:
    """Post-shutdown hook - cleanup resources."""
    logger.info("Cleaning up resources...")
    await cache_manager.stop_cleanup_task()
    await HTTPClient.close()
    logger.info("Cleanup complete")


def main():
    """Start the Akitafolio bot."""
    # Validate configuration
    errors = settings.validate_required()
    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        print("❌ Error: Missing required configuration")
        for error in errors:
            print(f"   - {error}")
        return
    
    # Create the Application with lifecycle handlers
    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    
    # Register command handlers
    handlers = [
        ("start", start_command),
        ("help", help_command),
        ("chains", chains_command),
        ("convert", convert_command),
        ("eth", eth_command),
        ("btc", btc_command),
        ("xpub", xpub_command),
        ("add_eth", add_eth_command),
        ("add_btc", add_btc_command),
        ("add_xpub", add_xpub_command),
        ("remove_eth", remove_eth_command),
        ("remove_btc", remove_btc_command),
        ("remove_xpub", remove_xpub_command),
        ("addresses", addresses_command),
        ("portfolio", portfolio_command),
        ("tokens", tokens_command),
        ("defi", defi_command),
        ("add_token", add_token_command),
        ("toggle_defi", toggle_defi_command),
    ]
    
    for command, handler in handlers:
        application.add_handler(CommandHandler(command, handler))
    
    # Register error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    all_chains = settings.get_all_chains()
    
    logger.info("Starting Akitafolio...")
    print("🐕 Akitafolio is running...")
    print(f"📡 Monitoring {len(all_chains)} EVM chains + Bitcoin")
    print(f"💼 Portfolio tracking enabled (ETH, BTC, xpub)")
    print(f"🔑 HD Wallet support via Blockchain.info API")
    print(f"📊 24h portfolio change tracking enabled")
    print(f"🪙 ERC20 token tracking enabled")
    print(f"🏦 DeFi position tracking enabled (Aave V3)")
    print(f"⚡ Caching layer active")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
