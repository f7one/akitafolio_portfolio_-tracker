from unittest.mock import AsyncMock

import pytest

from akitafolio.config import settings
from akitafolio.handlers.commands import format_portfolio_message, format_tokens_message
from akitafolio.models import Portfolio, PortfolioChange, TokenBalance, TokenPortfolio
from akitafolio.services.tokens import TokenService


def make_token(symbol: str, balance: float, value_usd: float) -> TokenBalance:
    return TokenBalance(
        symbol=symbol,
        address=f"0x{symbol.lower()}",
        chain="ethereum",
        balance=balance,
        decimals=18,
        price_usd=1.0,
        value_usd=value_usd,
    )


@pytest.mark.asyncio
async def test_token_service_aggregates_balances_and_hides_dust(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        type(settings),
        "get_default_tokens",
        lambda _settings: {
            "ethereum": [
                {"symbol": "USDC", "address": "0xusdc", "decimals": 6, "coingecko_id": "usd-coin"},
                {"symbol": "DUST", "address": "0xdust", "decimals": 18, "coingecko_id": "dust"},
            ]
        },
    )
    mocked_balances = AsyncMock(
        side_effect=[
            make_token("USDC", 500.0, 500.0),
            make_token("DUST", 10.0, 0.30),
            make_token("USDC", 120.0, 120.0),
            make_token("DUST", 5.0, 0.25),
        ]
    )
    monkeypatch.setattr(TokenService, "get_token_balance", mocked_balances)

    portfolio = await TokenService.get_all_token_balances(["first", "second"])

    assert mocked_balances.await_count == 4
    assert portfolio.total_value_usd == pytest.approx(620.55)
    assert portfolio.token_count == 1
    assert portfolio.tokens[0].symbol == "USDC"
    assert portfolio.tokens[0].balance == pytest.approx(620.0)
    assert portfolio.hidden_dust_count == 1
    assert portfolio.hidden_dust_value_usd == pytest.approx(0.55)


def test_portfolio_formatter_uses_production_token_count_rule() -> None:
    portfolio = Portfolio(
        total_portfolio_usd=1.0,
        tokens=TokenPortfolio(total_value_usd=1.0, token_count=0),
    )

    message = format_portfolio_message(portfolio, PortfolioChange())

    assert "Token Holdings" not in message


def test_portfolio_formatter_renders_visible_holdings_and_change() -> None:
    portfolio = Portfolio(
        total_eth=1.5,
        total_eth_usd=3000.0,
        eth_price=2000.0,
        total_btc_combined=0.15,
        total_btc_usd=10500.0,
        btc_price=70000.0,
        total_portfolio_usd=14121.55,
        tokens=TokenPortfolio(
            total_value_usd=621.55,
            token_count=3,
            top_holdings=[make_token("USDC", 500.0, 500.0), make_token("DAI", 120.0, 120.0)],
        ),
    )

    message = format_portfolio_message(
        portfolio,
        PortfolioChange(has_data=True, change_usd=250.0, change_percent=1.8),
    )

    assert "Token Count: 3" in message
    assert "$14,121.55" in message
    assert "USDC: $500.00" in message
    assert "DAI: $120.00" in message
    assert "+$250.00" in message


def test_tokens_formatter_shows_hidden_dust_summary() -> None:
    token_portfolio = TokenPortfolio(
        total_value_usd=621.55,
        token_count=2,
        tokens=[make_token("USDC", 500.0, 500.0), make_token("DAI", 120.0, 120.0)],
        hidden_dust_count=2,
        hidden_dust_value_usd=0.55,
    )

    message = format_tokens_message(token_portfolio)

    assert "USDC" in message
    assert "DAI" in message
    assert "2 token(s) hidden" in message
    assert "$0.55" in message
