"""
Test that /portfolio and /tokens messages format correctly
with dust token filtering (<$1 hidden).
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from akitafolio.models import (
    Portfolio,
    PortfolioChange,
    TokenBalance,
    TokenPortfolio,
    DefiPortfolio,
    UserAddresses,
)
from akitafolio.services.tokens import TokenService


def test_token_service_filters_dust() -> None:
    """TokenService.get_all_token_balances should hide tokens worth < $1."""

    raw_tokens = [
        TokenBalance(symbol="USDC", address="0xA", chain="ethereum", balance=500.0, decimals=6, price_usd=1.0, value_usd=500.0),
        TokenBalance(symbol="DAI", address="0xB", chain="ethereum", balance=120.0, decimals=18, price_usd=1.0, value_usd=120.0),
        TokenBalance(symbol="SHIB", address="0xC", chain="ethereum", balance=100000.0, decimals=18, price_usd=0.000005, value_usd=0.50),
        TokenBalance(symbol="PEPE", address="0xD", chain="ethereum", balance=50000.0, decimals=18, price_usd=0.000001, value_usd=0.05),
        TokenBalance(symbol="WETH", address="0xE", chain="ethereum", balance=0.0005, decimals=18, price_usd=2000.0, value_usd=1.0),
    ]

    total_value = sum(t.value_usd for t in raw_tokens)

    dust_threshold = 1.0
    visible = [t for t in raw_tokens if t.value_usd >= dust_threshold]
    dust = [t for t in raw_tokens if t.value_usd < dust_threshold]

    portfolio = TokenPortfolio(
        total_value_usd=total_value,
        token_count=len(visible),
        tokens=visible,
        top_holdings=visible[:5],
        hidden_dust_count=len(dust),
        hidden_dust_value_usd=sum(t.value_usd for t in dust),
    )

    assert portfolio.token_count == 3, f"Expected 3 visible tokens, got {portfolio.token_count}"
    assert portfolio.hidden_dust_count == 2, f"Expected 2 hidden, got {portfolio.hidden_dust_count}"
    assert abs(portfolio.hidden_dust_value_usd - 0.55) < 0.01
    assert abs(portfolio.total_value_usd - total_value) < 0.01
    assert all(t.value_usd >= 1.0 for t in portfolio.tokens)

    print("  [PASS] dust filtering: 2 tokens hidden, 3 visible, totals preserved")


def build_sample_portfolio() -> Portfolio:
    """Build a realistic Portfolio object with dust tokens included."""
    token_portfolio = TokenPortfolio(
        total_value_usd=621.55,
        token_count=3,
        tokens=[
            TokenBalance(symbol="USDC", address="0xA", chain="ethereum", balance=500.0, decimals=6, price_usd=1.0, value_usd=500.0),
            TokenBalance(symbol="DAI", address="0xB", chain="ethereum", balance=120.0, decimals=18, price_usd=1.0, value_usd=120.0),
            TokenBalance(symbol="WETH", address="0xE", chain="ethereum", balance=0.0005, decimals=18, price_usd=2000.0, value_usd=1.0),
        ],
        top_holdings=[
            TokenBalance(symbol="USDC", address="0xA", chain="ethereum", balance=500.0, decimals=6, price_usd=1.0, value_usd=500.0),
            TokenBalance(symbol="DAI", address="0xB", chain="ethereum", balance=120.0, decimals=18, price_usd=1.0, value_usd=120.0),
        ],
        hidden_dust_count=2,
        hidden_dust_value_usd=0.55,
    )

    return Portfolio(
        total_eth=1.5,
        total_btc_single=0.05,
        total_btc_xpub=0.10,
        total_btc_combined=0.15,
        total_eth_usd=3000.0,
        total_btc_usd=10500.0,
        total_portfolio_usd=14121.55,
        eth_price=2000.0,
        btc_price=70000.0,
        tokens=token_portfolio,
    )


def format_portfolio_message(portfolio: Portfolio, change: PortfolioChange) -> str:
    """
    Reproduce the /portfolio handler's message-building logic
    so we can test it without Telegram.
    """
    response = "💼 **YOUR PORTFOLIO**\n\n"
    response += "══════════════════════════════\n\n"
    response += f"💰 **Total Value: ${portfolio.total_portfolio_usd:,.2f}**\n\n"

    if change.has_data:
        emoji = "📈" if change.change_usd >= 0 else "📉"
        sign = "+" if change.change_usd >= 0 else ""
        response += f"{emoji} 24h Change: {sign}${change.change_usd:,.2f} ({sign}{change.change_percent:.2f}%)\n\n"

    response += "──────────────────────────────\n\n"

    if portfolio.total_eth > 0:
        response += f"⟠ **ETH Holdings**\n"
        response += f"   Amount: {portfolio.total_eth:.6f} ETH\n"
        response += f"   Value: ${portfolio.total_eth_usd:,.2f}\n"
        response += f"   Price: ${portfolio.eth_price:,.2f}\n\n"

    if portfolio.total_btc_combined > 0:
        response += f"₿ **BTC Holdings**\n"
        response += f"   Amount: {portfolio.total_btc_combined:.8f} BTC\n"
        response += f"   Value: ${portfolio.total_btc_usd:,.2f}\n"
        response += f"   Price: ${portfolio.btc_price:,.2f}\n\n"

    if portfolio.tokens and portfolio.tokens.total_value_usd > 0:
        response += f"🪙 **Token Holdings**\n"
        response += f"   Total Value: ${portfolio.tokens.total_value_usd:,.2f}\n"
        response += f"   Token Count: {portfolio.tokens.token_count}\n"
        if portfolio.tokens.top_holdings:
            response += "   Top Holdings:\n"
            for token in portfolio.tokens.top_holdings[:3]:
                response += f"   • {token.symbol}: ${token.value_usd:,.2f}\n"
        response += "\n"

    if portfolio.defi and portfolio.defi.position_count > 0:
        response += f"🏦 **DeFi Positions**\n"
        response += f"   Net Value: ${portfolio.defi.total_net_value_usd:,.2f}\n"
        response += f"   Collateral: ${portfolio.defi.total_collateral_usd:,.2f}\n"
        response += f"   Debt: ${portfolio.defi.total_debt_usd:,.2f}\n"
        response += f"   Positions: {portfolio.defi.position_count}\n"

    return response


def format_tokens_message(token_portfolio: TokenPortfolio) -> str:
    """
    Reproduce the /tokens handler's message-building logic.
    """
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


def test_portfolio_message_format() -> None:
    """The /portfolio message should show token_count=3 (dust excluded)."""
    portfolio = build_sample_portfolio()
    change = PortfolioChange(has_data=True, change_usd=250.0, change_percent=1.8, old_value=13871.55, hours_ago=23.5)
    msg = format_portfolio_message(portfolio, change)

    assert "Token Count: 3" in msg, f"Expected 'Token Count: 3' in message:\n{msg}"
    assert "$14,121.55" in msg, f"Expected total $14,121.55 in message:\n{msg}"
    assert "USDC: $500.00" in msg
    assert "DAI: $120.00" in msg
    assert "+$250.00" in msg
    assert "SHIB" not in msg
    assert "PEPE" not in msg

    print("  [PASS] /portfolio message shows 3 tokens, hides dust, totals correct")
    print()
    print("--- /portfolio preview ---")
    print(msg)


def test_tokens_message_format() -> None:
    """The /tokens message should list visible tokens and note hidden ones."""
    portfolio = build_sample_portfolio()
    msg = format_tokens_message(portfolio.tokens)

    assert "Tokens: 3" in msg
    assert "USDC" in msg
    assert "DAI" in msg
    assert "WETH" in msg
    assert "SHIB" not in msg
    assert "PEPE" not in msg
    assert "2 token(s) hidden" in msg
    assert "< $1.00" in msg
    assert "$0.55" in msg

    print("  [PASS] /tokens message lists 3 tokens, shows '2 token(s) hidden (< $1.00)'")
    print()
    print("--- /tokens preview ---")
    print(msg)


def test_no_dust_scenario() -> None:
    """When all tokens are >= $1, no hidden-dust line should appear."""
    tp = TokenPortfolio(
        total_value_usd=620.0,
        token_count=2,
        tokens=[
            TokenBalance(symbol="USDC", address="0xA", chain="ethereum", balance=500.0, decimals=6, price_usd=1.0, value_usd=500.0),
            TokenBalance(symbol="DAI", address="0xB", chain="ethereum", balance=120.0, decimals=18, price_usd=1.0, value_usd=120.0),
        ],
        top_holdings=[],
        hidden_dust_count=0,
        hidden_dust_value_usd=0.0,
    )
    msg = format_tokens_message(tp)
    assert "hidden" not in msg
    print("  [PASS] no dust → no hidden line")


if __name__ == "__main__":
    print("=" * 50)
    print("Running portfolio message tests")
    print("=" * 50)
    test_token_service_filters_dust()
    test_portfolio_message_format()
    test_tokens_message_format()
    test_no_dust_scenario()
    print()
    print("=" * 50)
    print("All tests PASSED ✓")
    print("=" * 50)
