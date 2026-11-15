# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Klinger volume oscillator."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._util import check as _check
from tantra.indicators.moving_average import Ema
from tantra.types import to_decimal


@dataclass(slots=True)
class KlingerValue:
    klinger: Decimal
    signal: Decimal


@indicator(
    "klinger_oscillator",
    "volume",
    inputs=("high", "low", "close", "volume"),
    outputs=("klinger", "signal"),
    warmup=lambda s: max(s.fast, s.slow) + s.signal,
)
class KlingerOscillator(Indicator):
    """Klinger oscillator (TradingView form): signed volume = +V if hlc3 >= previous hlc3 else -V;
    klinger = EMA(sv, fast) - EMA(sv, slow); signal = EMA(klinger, signal). EMAs are SMA-seeded;
    the first bar has no previous hlc3 so signed volume starts on bar 2."""

    def __init__(self, fast: int = 34, slow: int = 55, signal: int = 13) -> None:
        self.fast, self.slow, self.signal = _check(fast), _check(slow), _check(signal)
        self._f, self._s, self._sig = Ema(fast), Ema(slow), Ema(signal)
        self._prev: Decimal | None = None

    def update(self, high: Decimal, low: Decimal, close: Decimal, volume: Decimal) -> KlingerValue | None:
        high, low, close, volume = (
            to_decimal(high),
            to_decimal(low),
            to_decimal(close),
            to_decimal(volume),
        )
        tp = (high + low + close) / 3
        prev, self._prev = self._prev, tp
        if prev is None:
            return None
        sv = volume if tp >= prev else -volume
        f, s = self._f.update(sv), self._s.update(sv)
        if f is None or s is None:
            return None
        k = f - s
        sig = self._sig.update(k)
        return None if sig is None else KlingerValue(k, sig)
