"""
CLI command logic for Akitafolio.

Each function calls the shared akitafolio services layer and returns
structured data. No Telegram dependencies — pure async business logic
wrappers for the CLI interface.
"""

from typing import Optional

from akitafolio.config import settings
from akitafolio.models import UserAddresses
from akitafolio.storage import load_user_addresses, save_user_addresses
from akitafolio.services.prices import PriceService
from akitafolio.services.blockchain import BlockchainService
from akitafolio.services.bitcoin import BitcoinService, convert_xpub
from akitafolio.services.tokens import TokenService
from akitafolio.services.defi import DefiService
from akitafolio.services.portfolio import PortfolioService
from akitafolio.http_client import HTTPClient

from cli import output


async def cmd_chains() -> None:
    output.print_chains()


async def cmd_convert(xpub: str) -> None:
    valid_prefixes = ("xpub", "ypub", "zpub")
    if not any(xpub.startswith(p) for p in valid_prefixes):
        output.print_error("Invalid key format. Key must start with xpub, ypub, or zpub.")
        return

    if not (100 <= len(xpub) <= 120):
        output.print_error("Invalid key length.")
        return

    current_format: Optional[str] = None
    for prefix in valid_prefixes:
        if xpub.startswith(prefix):
            current_format = prefix
            break

    conversions: dict[str, Optional[str]] = {}
    for target in valid_prefixes:
        if target == current_format:
            conversions[target] = xpub
        else:
            conversions[target] = convert_xpub(xpub, target)

    output.print_convert_result(xpub, current_format, conversions)


async def cmd_eth(address: str) -> None:
    result = await BlockchainService.get_all_chain_balances(address)
    prices = await PriceService.get_crypto_prices()
    output.print_eth_balance(address, result, prices)


async def cmd_btc(address: str) -> None:
    result = await BitcoinService.get_address_balance(address)
    prices = await PriceService.get_crypto_prices()

    if result.get("error"):
        output.print_error(result["error"])
        return

    output.print_btc_balance(address, result["balance"], prices)


async def cmd_xpub(xpub: str) -> None:
    result = await BitcoinService.get_xpub_balance(xpub)
    prices = await PriceService.get_crypto_prices()

    if result.get("error"):
        output.print_error(result["error"])
        return

    output.print_xpub_balance(xpub, result, prices)


async def cmd_add_eth(user_id: int, addrs: tuple[str, ...]) -> None:
    addresses = load_user_addresses(user_id)
    added, skipped, invalid = [], [], []

    for addr in addrs:
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

    output.print_address_add_result("ETH", added, skipped, invalid, len(addresses.eth))


async def cmd_add_btc(user_id: int, addrs: tuple[str, ...]) -> None:
    addresses = load_user_addresses(user_id)
    added, skipped, invalid = [], [], []

    for addr in addrs:
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

    output.print_address_add_result("BTC", added, skipped, invalid, len(addresses.btc))


async def cmd_add_xpub(user_id: int, keys: tuple[str, ...]) -> None:
    addresses = load_user_addresses(user_id)
    added, skipped, invalid = [], [], []

    for xpub in keys:
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

    output.print_address_add_result("xpub", added, skipped, invalid, len(addresses.xpub))


async def cmd_remove_eth(user_id: int, address: str) -> None:
    addresses = load_user_addresses(user_id)
    removed = False
    for saved_addr in addresses.eth[:]:
        if saved_addr.lower() == address.lower():
            addresses.eth.remove(saved_addr)
            removed = True
            break

    if removed:
        save_user_addresses(user_id, addresses)
        output.print_success("Removed ETH address")
    else:
        output.print_error("Address not found in your saved addresses")


async def cmd_remove_btc(user_id: int, address: str) -> None:
    addresses = load_user_addresses(user_id)
    if address in addresses.btc:
        addresses.btc.remove(address)
        save_user_addresses(user_id, addresses)
        output.print_success("Removed BTC address")
    else:
        output.print_error("Address not found in your saved addresses")


async def cmd_remove_xpub(user_id: int, xpub: str) -> None:
    addresses = load_user_addresses(user_id)
    if xpub in addresses.xpub:
        addresses.xpub.remove(xpub)
        save_user_addresses(user_id, addresses)
        output.print_success("Removed xpub key")
    else:
        output.print_error("xpub not found in your saved keys")


async def cmd_addresses(user_id: int) -> None:
    addresses = load_user_addresses(user_id)
    output.print_addresses(addresses)


async def cmd_portfolio(user_id: int) -> None:
    addresses = load_user_addresses(user_id)

    if not addresses.has_addresses():
        output.console.print("[dim]No saved addresses yet.[/dim]")
        output.console.print(
            "Use [bold]add-eth[/bold], [bold]add-btc[/bold], or "
            "[bold]add-xpub[/bold] to add addresses."
        )
        return

    with output.console.status("Calculating portfolio value..."):
        portfolio = await PortfolioService.get_portfolio(
            addresses,
            include_tokens=True,
            include_defi=addresses.track_defi,
        )

    change = PortfolioService.calculate_24h_change(user_id, portfolio.total_portfolio_usd)
    PortfolioService.save_snapshot(user_id, portfolio)

    output.print_portfolio(portfolio, change)


async def cmd_tokens(user_id: int) -> None:
    addresses = load_user_addresses(user_id)

    if not addresses.eth:
        output.console.print("[dim]No ETH addresses saved. Add addresses with [bold]add-eth[/bold] to track tokens.[/dim]")
        return

    with output.console.status("Fetching token balances..."):
        token_portfolio = await TokenService.get_all_token_balances(
            addresses.eth, addresses.tokens
        )

    output.print_tokens(token_portfolio)


async def cmd_defi(user_id: int) -> None:
    addresses = load_user_addresses(user_id)

    if not addresses.eth:
        output.console.print("[dim]No ETH addresses saved. Add addresses with [bold]add-eth[/bold] to track DeFi.[/dim]")
        return

    with output.console.status("Fetching DeFi positions..."):
        defi_portfolio = await DefiService.get_all_defi_positions(addresses.eth)

    output.print_defi(defi_portfolio)


async def cmd_add_token(
    user_id: int,
    chain: str,
    token_address: str,
    coingecko_id: str,
) -> None:
    all_chains = settings.get_all_chains()
    if chain not in all_chains:
        output.print_error(f"Unsupported chain: {chain}")
        return

    if not BlockchainService.is_valid_address(token_address):
        output.print_error("Invalid token contract address")
        return

    addresses = load_user_addresses(user_id)
    new_token = {
        "chain": chain,
        "address": BlockchainService.checksum_address(token_address),
        "coingecko_id": coingecko_id,
        "decimals": 18,
        "symbol": coingecko_id.upper(),
    }
    addresses.tokens.append(new_token)
    save_user_addresses(user_id, addresses)

    output.print_success(f"Added custom token! Chain: {chain}, CoinGecko ID: {coingecko_id}")


async def cmd_toggle_defi(user_id: int) -> None:
    addresses = load_user_addresses(user_id)
    addresses.track_defi = not addresses.track_defi
    save_user_addresses(user_id, addresses)

    status = "[green]Enabled[/green]" if addresses.track_defi else "[red]Disabled[/red]"
    output.console.print(f"DeFi Tracking: {status}")


async def cleanup() -> None:
    """Close HTTP session after CLI command completes."""
    await HTTPClient.close()
