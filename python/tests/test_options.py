"""Tests for the Decimal-canonical wheel `tantra.options` (T13 wheel port)."""

from datetime import date
from decimal import Decimal

import pytest
from tantra.instrument import InstrumentId
from tantra.options import (
    Greeks,
    OptionChain,
    OptionContract,
    OptionKind,
    OptionStyle,
    bs_greeks,
    bs_price,
    implied_volatility,
)


def test_bs_price_atm_call_approx() -> None:
    price = bs_price(
        kind=OptionKind.CALL,
        spot=Decimal(100),
        strike=Decimal(100),
        tau=Decimal(1),
        iv=Decimal("0.2"),
        r=Decimal("0.05"),
    )
    # Abramowitz & Stegun erf approximation is accurate to ~1.5e-7; use a
    # generous 0.05 tolerance around the textbook ATM price.
    assert abs(price - Decimal("10.45")) < Decimal("0.05")


def test_bs_price_put_positive() -> None:
    price = bs_price(
        kind=OptionKind.PUT,
        spot=Decimal(100),
        strike=Decimal(100),
        tau=Decimal(1),
        iv=Decimal("0.2"),
        r=Decimal("0.05"),
    )
    assert price > Decimal(0)


def test_bs_price_itm_call_lower_bound() -> None:
    price = bs_price(
        kind=OptionKind.CALL,
        spot=Decimal(110),
        strike=Decimal(100),
        tau=Decimal(1),
        iv=Decimal("0.2"),
        r=Decimal("0.05"),
    )
    assert price >= Decimal(10)  # >= intrinsic value 10


def test_bs_greeks_all_decimal_and_item_access() -> None:
    g = bs_greeks(
        kind=OptionKind.CALL,
        spot=Decimal(90),
        strike=Decimal(100),
        tau=Decimal(1),
        iv=Decimal("0.2"),
        r=Decimal("0.05"),
    )
    assert isinstance(g, Greeks)
    for name in ("price", "delta", "gamma", "theta", "vega", "rho"):
        assert isinstance(getattr(g, name), Decimal)
    # OTM call delta sits strictly between 0 and 1.
    assert Decimal(0) < g.delta < Decimal(1)
    assert g["delta"] == g.delta


def test_implied_volatility_round_trip() -> None:
    price = bs_price(
        kind=OptionKind.CALL,
        spot=Decimal(100),
        strike=Decimal(100),
        tau=Decimal(1),
        iv=Decimal("0.25"),
        r=Decimal("0.05"),
    )
    iv = implied_volatility(
        price,
        spot=Decimal(100),
        strike=Decimal(100),
        tau=Decimal(1),
        r=Decimal("0.05"),
        kind=OptionKind.CALL,
    )
    assert iv is not None
    assert abs(iv - Decimal("0.25")) < Decimal("0.01")


def test_option_contract_negative_strike_raises() -> None:
    with pytest.raises(ValueError):
        OptionContract(
            instrument_id=InstrumentId("RELIANCE", "NSE"),
            expiry=date(2026, 12, 31),
            strike=Decimal(-5),
            kind=OptionKind.CALL,
        )


def test_option_contract_negative_iv_raises() -> None:
    with pytest.raises(ValueError):
        OptionContract(
            instrument_id=InstrumentId("RELIANCE", "NSE"),
            expiry=date(2026, 12, 31),
            strike=Decimal(100),
            kind=OptionKind.CALL,
            iv=Decimal(-1),
        )


def test_option_contract_to_decimal_semantics() -> None:
    c = OptionContract(
        instrument_id=InstrumentId("RELIANCE", "NSE"),
        expiry=date(2026, 12, 31),
        strike="105.5",
        kind=OptionKind.CALL,
        bid="0.5",
    )
    assert isinstance(c.strike, Decimal)
    assert c.strike == Decimal("105.5")
    assert c.bid == Decimal("0.5")
    assert c.iv == Decimal(0)
    assert c.style is OptionStyle.EUROPEAN


def test_option_chain_negative_spot_raises() -> None:
    with pytest.raises(ValueError):
        OptionChain(
            underlying=InstrumentId("NIFTY", "NSE"),
            expiry=date(2026, 12, 31),
            spot=Decimal(-1),
            contracts=[],
        )


def test_option_chain_spot_is_decimal() -> None:
    chain = OptionChain(
        underlying=InstrumentId("NIFTY", "NSE"),
        expiry=date(2026, 12, 31),
        spot="99.5",
        contracts=[],
    )
    assert isinstance(chain.spot, Decimal)
    assert chain.spot == Decimal("99.5")
