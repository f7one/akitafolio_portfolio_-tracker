import asyncio

import pytest

from akitafolio.config import settings
from akitafolio.http_client import HTTPClient
from akitafolio.limits import RpcExecutor, UserRequestLimiter
from akitafolio.models import AggregatedBalance, CryptoPrices, TokenBalance, UserAddresses
from akitafolio.services.bitcoin import HDWALLET_AVAILABLE, Bitcoin, HDWallet
from akitafolio.services.blockchain import BlockchainService
from akitafolio.services.portfolio import PortfolioService
from akitafolio.services.tokens import TokenService


@pytest.mark.asyncio
async def test_user_request_limiter_rejects_concurrent_and_exhausted_requests():
    limiter = UserRequestLimiter(requests_per_minute=1, burst_size=1)

    assert await limiter.try_acquire(1)
    assert not await limiter.try_acquire(1)
    await limiter.release(1)
    assert not await limiter.try_acquire(1)
    assert await limiter.try_acquire(2)


@pytest.mark.asyncio
async def test_rpc_executor_limits_blocking_work():
    executor = RpcExecutor(max_concurrency=2)
    active = 0
    peak = 0

    def blocking_work():
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        import time

        time.sleep(0.03)
        active -= 1
        return 1

    assert await asyncio.gather(*(executor.run(blocking_work) for _ in range(6))) == [1] * 6
    assert peak == 2


def test_http_retry_after_is_bounded_and_invalid_values_are_safe():
    assert HTTPClient._retry_after_seconds("999999") == HTTPClient.max_retry_after_seconds
    assert HTTPClient._retry_after_seconds("-1") == 0
    assert HTTPClient._retry_after_seconds("not-a-number") == 5


@pytest.mark.asyncio
async def test_http_response_body_has_a_hard_limit():
    class Content:
        async def read(self, _size):
            return b"x" * (HTTPClient.max_response_bytes + 1)

    class Response:
        content = Content()

    with pytest.raises(Exception, match="too large"):
        await HTTPClient._read_limited(Response())


def test_web3_providers_explicitly_disable_ccip_read():
    BlockchainService._web3_instances = None


def test_hdwallet_v3_constructor_is_compatible():
    assert HDWALLET_AVAILABLE
    assert HDWallet(cryptocurrency=Bitcoin)
    instances = BlockchainService.get_web3_instances()
    assert instances
    assert all(not instance.provider.global_ccip_read_enabled for instance in instances.values())
    BlockchainService._web3_instances = None


@pytest.mark.asyncio
async def test_custom_token_duplicate_does_not_create_extra_rpc_work(monkeypatch):
    default_tokens = settings.get_default_tokens()
    default_token = default_tokens["ethereum"][0]
    calls = []

    async def fake_balance(**kwargs):
        calls.append(kwargs)
        return TokenBalance(
            symbol=kwargs["symbol"],
            address=kwargs["token_address"],
            chain=kwargs["chain"],
            balance=1,
            decimals=kwargs["decimals"],
            price_usd=1,
            value_usd=1,
        )

    monkeypatch.setattr(TokenService, "get_token_balance", fake_balance)
    custom_duplicate = {
        **default_token,
        "chain": "ethereum",
        "address": default_token["address"].lower(),
    }
    await TokenService.get_all_token_balances(["0xabc"], [custom_duplicate])
    default_count = sum(len(tokens) for tokens in default_tokens.values())
    assert len(calls) == default_count


@pytest.mark.asyncio
async def test_custom_token_metadata_uses_contract_decimals(monkeypatch):
    class Call:
        def __init__(self, value):
            self.value = value

        def call(self):
            return self.value

    class Functions:
        def decimals(self):
            return Call(6)

        def symbol(self):
            return Call("USDC")

    class Eth:
        def contract(self, **_kwargs):
            return type("Contract", (), {"functions": Functions()})()

    class Web3Instance:
        eth = Eth()

    monkeypatch.setattr(
        BlockchainService, "get_web3_instances", lambda: {"ethereum": Web3Instance()}
    )
    decimals, symbol = await TokenService.get_token_metadata(
        "0x0000000000000000000000000000000000000001", "ethereum"
    )
    assert (decimals, symbol) == (6, "USDC")


@pytest.mark.asyncio
async def test_incomplete_upstream_portfolio_is_marked_not_safe_for_snapshot(monkeypatch):
    async def fake_prices():
        return CryptoPrices(eth=100, btc=100)

    async def failed_eth(_addresses):
        return [AggregatedBalance(address="0xabc", error="rpc failed")]

    monkeypatch.setattr("akitafolio.services.portfolio.PriceService.get_crypto_prices", fake_prices)
    monkeypatch.setattr(PortfolioService, "_get_eth_balances", failed_eth)

    portfolio = await PortfolioService.get_portfolio(
        UserAddresses(eth=["0xabc"]), include_tokens=False, include_defi=False
    )
    assert portfolio.total_eth == 0
    assert not portfolio.is_complete
    assert portfolio.errors
