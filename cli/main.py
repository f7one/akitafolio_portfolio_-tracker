#!/usr/bin/env python3
"""
Akitafolio CLI - Multi-Chain Crypto Portfolio Tracker.

Command-line interface that provides the same portfolio features
as the Telegram bot, using the shared akitafolio services layer.
"""

import asyncio
import os
import sys
from functools import wraps

import click

from cli import commands


def async_command(f):
    """Decorator to run an async click command function."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            asyncio.run(_run_and_cleanup(f, *args, **kwargs))
        except KeyboardInterrupt:
            click.echo("\nInterrupted.")
            sys.exit(130)
    return wrapper


async def _run_and_cleanup(f, *args, **kwargs):
    try:
        await f(*args, **kwargs)
    finally:
        await commands.cleanup()


@click.group(help="Akitafolio - Multi-chain crypto portfolio tracker CLI.")
@click.option(
    "--user-id",
    type=int,
    default=None,
    envvar="CLI_USER_ID",
    help="User ID for storage (default: CLI_USER_ID env or 1).",
)
@click.pass_context
def app(ctx: click.Context, user_id: int | None) -> None:
    ctx.ensure_object(dict)
    ctx.obj["user_id"] = user_id or int(os.getenv("CLI_USER_ID", "1"))


# ============================================================================
# INFO COMMANDS
# ============================================================================


@app.command()
def chains() -> None:
    """List all supported blockchain networks."""
    asyncio.run(commands.cmd_chains())


@app.command()
@click.argument("xpub")
def convert(xpub: str) -> None:
    """Convert xpub between formats (xpub/ypub/zpub)."""
    asyncio.run(commands.cmd_convert(xpub))


# ============================================================================
# BALANCE COMMANDS
# ============================================================================


@app.command()
@click.argument("address")
@async_command
async def eth(address: str) -> None:
    """Check ETH balance across all chains."""
    await commands.cmd_eth(address)


@app.command()
@click.argument("address")
@async_command
async def btc(address: str) -> None:
    """Check Bitcoin balance."""
    await commands.cmd_btc(address)


@app.command()
@click.argument("key")
@async_command
async def xpub(key: str) -> None:
    """Check HD wallet balance using xpub/ypub/zpub."""
    await commands.cmd_xpub(key)


# ============================================================================
# ADDRESS MANAGEMENT
# ============================================================================


@app.command("add-eth")
@click.argument("addresses", nargs=-1, required=True)
@click.pass_context
@async_command
async def add_eth(ctx: click.Context, addresses: tuple[str, ...]) -> None:
    """Add ETH address(es) to portfolio."""
    await commands.cmd_add_eth(ctx.obj["user_id"], addresses)


@app.command("add-btc")
@click.argument("addresses", nargs=-1, required=True)
@click.pass_context
@async_command
async def add_btc(ctx: click.Context, addresses: tuple[str, ...]) -> None:
    """Add BTC address(es) to portfolio."""
    await commands.cmd_add_btc(ctx.obj["user_id"], addresses)


@app.command("add-xpub")
@click.argument("keys", nargs=-1, required=True)
@click.pass_context
@async_command
async def add_xpub(ctx: click.Context, keys: tuple[str, ...]) -> None:
    """Add xpub key(s) to portfolio."""
    await commands.cmd_add_xpub(ctx.obj["user_id"], keys)


@app.command("remove-eth")
@click.argument("address")
@click.pass_context
@async_command
async def remove_eth(ctx: click.Context, address: str) -> None:
    """Remove ETH address from portfolio."""
    await commands.cmd_remove_eth(ctx.obj["user_id"], address)


@app.command("remove-btc")
@click.argument("address")
@click.pass_context
@async_command
async def remove_btc(ctx: click.Context, address: str) -> None:
    """Remove BTC address from portfolio."""
    await commands.cmd_remove_btc(ctx.obj["user_id"], address)


@app.command("remove-xpub")
@click.argument("key")
@click.pass_context
@async_command
async def remove_xpub(ctx: click.Context, key: str) -> None:
    """Remove xpub key from portfolio."""
    await commands.cmd_remove_xpub(ctx.obj["user_id"], key)


@app.command()
@click.pass_context
@async_command
async def addresses(ctx: click.Context) -> None:
    """List all saved addresses."""
    await commands.cmd_addresses(ctx.obj["user_id"])


# ============================================================================
# PORTFOLIO
# ============================================================================


@app.command()
@click.pass_context
@async_command
async def portfolio(ctx: click.Context) -> None:
    """Show complete portfolio value."""
    await commands.cmd_portfolio(ctx.obj["user_id"])


# ============================================================================
# TOKENS & DEFI
# ============================================================================


@app.command()
@click.pass_context
@async_command
async def tokens(ctx: click.Context) -> None:
    """Show all ERC20 token balances."""
    await commands.cmd_tokens(ctx.obj["user_id"])


@app.command()
@click.pass_context
@async_command
async def defi(ctx: click.Context) -> None:
    """Show DeFi positions."""
    await commands.cmd_defi(ctx.obj["user_id"])


@app.command("add-token")
@click.argument("chain")
@click.argument("token_address")
@click.argument("coingecko_id")
@click.pass_context
@async_command
async def add_token(
    ctx: click.Context,
    chain: str,
    token_address: str,
    coingecko_id: str,
) -> None:
    """Add custom ERC20 token to track.

    CHAIN: blockchain name (e.g. ethereum, base, arbitrum)
    TOKEN_ADDRESS: contract address of the token
    COINGECKO_ID: CoinGecko identifier for price lookup
    """
    await commands.cmd_add_token(
        ctx.obj["user_id"],
        chain.lower(),
        token_address,
        coingecko_id.lower(),
    )


@app.command("toggle-defi")
@click.pass_context
@async_command
async def toggle_defi(ctx: click.Context) -> None:
    """Toggle DeFi tracking on/off."""
    await commands.cmd_toggle_defi(ctx.obj["user_id"])


if __name__ == "__main__":
    app()
