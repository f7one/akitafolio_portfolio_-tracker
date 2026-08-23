"""
Rich terminal output formatting for Akitafolio CLI.

Provides formatted display functions matching all TG bot message formats
using the rich library for tables, panels, and colored output.
"""

from typing import Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from akitafolio.config import settings
from akitafolio.models import (
    AggregatedBalance,
    CryptoPrices,
    DefiPortfolio,
    Portfolio,
    PortfolioChange,
    TokenPortfolio,
    UserAddresses,
)

console = Console()


def print_error(message: str) -> None:
    console.print(f"[bold red]Error:[/bold red] {message}")


def print_success(message: str) -> None:
    console.print(f"[bold green]{message}[/bold green]")


def print_warning(message: str) -> None:
    console.print(f"[bold yellow]{message}[/bold yellow]")


def print_chains() -> None:
    """Display all supported blockchain networks."""
    eth_chains = settings.get_eth_chains()
    other_chains = settings.get_other_chains()

    table = Table(title="Supported Blockchain Networks", box=box.ROUNDED)
    table.add_column("Chain", style="bold")
    table.add_column("Symbol", style="cyan")
    table.add_column("Type", style="green")

    for _chain, config in eth_chains.items():
        table.add_row(
            f"{config['emoji']} {config['name']}",
            config["symbol"],
            "ETH (counted in total)",
        )

    for _chain, config in other_chains.items():
        table.add_row(
            f"{config['emoji']} {config['name']}",
            config["symbol"],
            "Other",
        )

    table.add_row("₿ Bitcoin", "BTC", "Bitcoin")

    console.print(table)
    all_chains = settings.get_all_chains()
    console.print(f"\nTotal: {len(all_chains)} EVM chains + Bitcoin")


def print_convert_result(
    xpub: str,
    current_format: str,
    conversions: dict[str, Optional[str]],
) -> None:
    """Display xpub format conversion results."""
    console.print(
        Panel(
            f"[bold]Input:[/bold] {xpub[:20]}...\n"
            f"[bold]Current format:[/bold] {current_format}",
            title="xpub Format Conversion",
        )
    )

    for target, converted in conversions.items():
        if target == current_format:
            console.print(f"\n[bold]{target}[/bold] (original):")
            console.print(f"  {xpub}")
        elif converted:
            console.print(f"\n[bold]{target}[/bold]:")
            console.print(f"  {converted}")
        else:
            console.print(f"\n[bold]{target}[/bold]: [red]Conversion failed[/red]")

    console.print("\nCopy the format you need and use it in block explorers or wallets.")


def print_eth_balance(
    address: str,
    result: AggregatedBalance,
    prices: CryptoPrices,
) -> None:
    """Display ETH balance across all chains."""
    if result.error:
        print_error(result.error)
        return

    total_usd = result.total_eth * prices.eth if prices.eth > 0 else 0

    console.print(
        Panel(
            f"Address: {address[:10]}...{address[-8:]}",
            title="Multi-Chain Balance Summary",
        )
    )

    summary = Table(box=box.SIMPLE)
    summary.add_column("Metric", style="bold")
    summary.add_column("Value", justify="right")

    summary.add_row("Total ETH", f"{result.total_eth:.6f} ETH")
    if prices.eth > 0:
        summary.add_row("USD Value", f"${total_usd:,.2f}")
        summary.add_row("ETH Price", f"${prices.eth:,.2f}")

    console.print(summary)

    chain_table = Table(title="Balance by Chain", box=box.ROUNDED)
    chain_table.add_column("Chain", style="bold")
    chain_table.add_column("Balance", justify="right")
    chain_table.add_column("Currency", style="cyan")

    has_balance = False
    for chain_data in result.chain_balances:
        if chain_data.balance > 0:
            has_balance = True
            chain_table.add_row(
                f"{chain_data.emoji} {chain_data.network}",
                f"{chain_data.balance:.6f}",
                chain_data.currency,
            )

    if has_balance:
        console.print(chain_table)
    else:
        console.print("[dim]No balances found on any chain.[/dim]")


def print_btc_balance(
    address: str,
    balance: float,
    prices: CryptoPrices,
) -> None:
    """Display Bitcoin balance."""
    usd_value = balance * prices.btc if prices.btc > 0 else 0

    console.print(
        Panel(
            f"Address: {address[:10]}...{address[-8:]}",
            title="Bitcoin Balance",
        )
    )

    table = Table(box=box.SIMPLE)
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Balance", f"{balance:.8f} BTC")
    if prices.btc > 0:
        table.add_row("USD Value", f"${usd_value:,.2f}")
        table.add_row("BTC Price", f"${prices.btc:,.2f}")

    console.print(table)


def print_xpub_balance(
    xpub: str,
    result: dict,
    prices: CryptoPrices,
) -> None:
    """Display HD wallet balance."""
    balance = result.get("balance", 0)
    usd_value = balance * prices.btc if prices.btc > 0 else 0

    info_lines = [f"Key: {xpub[:15]}...{xpub[-10:]}"]
    used_format = result.get("used_format")
    if used_format and result.get("converted_key"):
        info_lines.append(f"Format: {used_format} (auto-detected)")
    elif used_format:
        info_lines.append(f"Format: {used_format}")

    console.print(Panel("\n".join(info_lines), title="HD Wallet Balance"))

    table = Table(box=box.SIMPLE)
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Balance", f"{balance:.8f} BTC")
    if prices.btc > 0:
        table.add_row("USD Value", f"${usd_value:,.2f}")
    table.add_row("Transactions", str(result.get("transaction_count", 0)))

    console.print(table)


def print_address_add_result(
    asset_type: str,
    added: list[str],
    skipped: list[str],
    invalid: list[str],
    total: int,
) -> None:
    """Display result of adding addresses."""
    if added:
        print_success(f"Added {len(added)} {asset_type} address(es)")
    if skipped:
        print_warning(f"Skipped {len(skipped)} (already saved)")
    if invalid:
        print_error(f"Invalid: {len(invalid)} address(es)")

    console.print(f"\nTotal {asset_type} addresses: {total}")


def print_addresses(addresses: UserAddresses) -> None:
    """Display all saved addresses."""
    if not addresses.has_addresses():
        console.print("[dim]No saved addresses yet.[/dim]")
        console.print(
            "Use [bold]add-eth[/bold], [bold]add-btc[/bold], or [bold]add-xpub[/bold] to add addresses."
        )
        return

    console.print(Panel.fit("[bold]Your Saved Addresses[/bold]"))

    if addresses.eth:
        console.print(f"\n[bold]ETH Addresses ({len(addresses.eth)}):[/bold]")
        for addr in addresses.eth:
            console.print(f"  {addr[:10]}...{addr[-8:]}")

    if addresses.btc:
        console.print(f"\n[bold]BTC Addresses ({len(addresses.btc)}):[/bold]")
        for addr in addresses.btc:
            console.print(f"  {addr[:10]}...{addr[-8:]}")

    if addresses.xpub:
        console.print(f"\n[bold]HD Wallets ({len(addresses.xpub)}):[/bold]")
        for xpub in addresses.xpub:
            console.print(f"  {xpub[:15]}...{xpub[-10:]}")

    defi_status = "[green]Enabled[/green]" if addresses.track_defi else "[red]Disabled[/red]"
    console.print(f"\nDeFi Tracking: {defi_status}")


def print_portfolio(portfolio: Portfolio, change: PortfolioChange) -> None:
    """Display complete portfolio."""
    console.print(Panel.fit("[bold]YOUR PORTFOLIO[/bold]"))
    console.print()

    console.print(f"[bold]Total Value: ${portfolio.total_portfolio_usd:,.2f}[/bold]")

    if change.has_data:
        color = "green" if change.change_usd >= 0 else "red"
        sign = "+" if change.change_usd >= 0 else ""
        arrow = "▲" if change.change_usd >= 0 else "▼"
        console.print(
            f"[{color}]{arrow} 24h Change: {sign}${change.change_usd:,.2f} "
            f"({sign}{change.change_percent:.2f}%)[/{color}]"
        )

    console.print()

    table = Table(title="Holdings", box=box.ROUNDED)
    table.add_column("Asset", style="bold")
    table.add_column("Amount", justify="right")
    table.add_column("USD Value", justify="right", style="green")
    table.add_column("Price", justify="right", style="dim")

    if portfolio.total_eth > 0:
        table.add_row(
            "ETH",
            f"{portfolio.total_eth:.6f}",
            f"${portfolio.total_eth_usd:,.2f}",
            f"${portfolio.eth_price:,.2f}",
        )

    if portfolio.total_btc_combined > 0:
        table.add_row(
            "BTC",
            f"{portfolio.total_btc_combined:.8f}",
            f"${portfolio.total_btc_usd:,.2f}",
            f"${portfolio.btc_price:,.2f}",
        )

    if portfolio.tokens and portfolio.tokens.token_count > 0:
        table.add_row(
            f"Tokens ({portfolio.tokens.token_count})",
            "",
            f"${portfolio.tokens.total_value_usd:,.2f}",
            "",
        )

    if portfolio.defi and portfolio.defi.position_count > 0:
        table.add_row(
            f"DeFi ({portfolio.defi.position_count})",
            "",
            f"${portfolio.defi.total_net_value_usd:,.2f}",
            "",
        )

    console.print(table)

    if portfolio.tokens and portfolio.tokens.top_holdings:
        console.print("\n[bold]Top Token Holdings:[/bold]")
        for token in portfolio.tokens.top_holdings[:3]:
            console.print(f"  {token.symbol}: ${token.value_usd:,.2f}")

    if portfolio.defi and portfolio.defi.position_count > 0:
        console.print("\n[bold]DeFi Summary:[/bold]")
        console.print(f"  Collateral: ${portfolio.defi.total_collateral_usd:,.2f}")
        console.print(f"  Debt: ${portfolio.defi.total_debt_usd:,.2f}")
        console.print(f"  Net: ${portfolio.defi.total_net_value_usd:,.2f}")


def print_tokens(token_portfolio: TokenPortfolio) -> None:
    """Display ERC20 token balances."""
    if token_portfolio.token_count == 0:
        console.print("[dim]No token balances found.[/dim]")
        return

    console.print(
        Panel.fit(
            f"[bold]Total Value: ${token_portfolio.total_value_usd:,.2f}[/bold]  |  "
            f"Tokens: {token_portfolio.token_count}",
            title="Your Token Balances",
        )
    )

    table = Table(box=box.ROUNDED)
    table.add_column("Token", style="bold")
    table.add_column("Chain", style="dim")
    table.add_column("Balance", justify="right")
    table.add_column("USD Value", justify="right", style="green")

    for token in token_portfolio.tokens[:15]:
        table.add_row(
            token.symbol,
            token.chain,
            f"{token.balance:.6f}",
            f"${token.value_usd:,.2f}",
        )

    console.print(table)

    if token_portfolio.token_count > 15:
        console.print(f"[dim]...and {token_portfolio.token_count - 15} more tokens[/dim]")

    if token_portfolio.hidden_dust_count > 0:
        console.print(
            f"[dim]{token_portfolio.hidden_dust_count} token(s) hidden "
            f"(< $1.00, total ${token_portfolio.hidden_dust_value_usd:,.2f})[/dim]"
        )


def print_defi(defi_portfolio: DefiPortfolio) -> None:
    """Display DeFi positions."""
    if defi_portfolio.position_count == 0:
        console.print("[dim]No DeFi positions found.[/dim]")
        return

    console.print(
        Panel.fit(
            f"[bold]Net Value: ${defi_portfolio.total_net_value_usd:,.2f}[/bold]  |  "
            f"Positions: {defi_portfolio.position_count}",
            title="Your DeFi Positions",
        )
    )

    console.print(
        f"  Collateral: ${defi_portfolio.total_collateral_usd:,.2f}  |  "
        f"Debt: ${defi_portfolio.total_debt_usd:,.2f}"
    )
    console.print()

    all_chains = settings.get_all_chains()

    table = Table(box=box.ROUNDED)
    table.add_column("Protocol", style="bold")
    table.add_column("Chain")
    table.add_column("Collateral", justify="right", style="green")
    table.add_column("Debt", justify="right", style="red")
    table.add_column("Net", justify="right")
    table.add_column("Health", justify="right")

    for pos in defi_portfolio.positions:
        chain_emoji = all_chains.get(pos.chain, {}).get("emoji", "")
        table.add_row(
            pos.protocol,
            f"{chain_emoji} {pos.chain.title()}",
            f"${pos.collateral_usd:,.2f}",
            f"${pos.debt_usd:,.2f}",
            f"${pos.net_value_usd:,.2f}",
            pos.health_factor_display,
        )

    console.print(table)
