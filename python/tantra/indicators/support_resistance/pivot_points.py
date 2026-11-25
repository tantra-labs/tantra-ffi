# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Session pivot points (support_resistance family)."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from tantra.indicators._base import Indicator, indicator
from tantra.indicators._india import ist_session_day
from tantra.types import to_decimal

MODES = ("standard", "fibonacci", "camarilla", "woodie")


@dataclass(frozen=True, slots=True)
class PivotPointsValue:
    pp: Decimal
    r1: Decimal
    r2: Decimal
    r3: Decimal
    s1: Decimal
    s2: Decimal
    s3: Decimal


@indicator(
    "pivot_points",
    "support_resistance",
    inputs=("high", "low", "close", "ts"),
    outputs=("pp", "r1", "r2", "r3", "s1", "s2", "s3"),
    warmup=None,
)
class PivotPoints(Indicator):
    """Pivot levels for the current IST session from the previous IST session's H/L/C.

    Sessions are detected with ``ist_session_day(ts)`` (daily bars: each bar is a session).
    First value is on the first bar of the second session; levels stay fixed all session.
    With P = previous (H+L+C)/3 and R = H-L:
    standard: R1=2P-L, S1=2P-H, R2/S2=P+/-R, R3=H+2(P-L), S3=L-2(H-P).
    fibonacci: R1..R3 = P + 0.382/0.618/1.0*R, S1..S3 = P - same.
    camarilla: R1..R3 = C + 1.1*R/12, /6, /4; S1..S3 = C - same (pp = P).
    woodie: P=(H+L+2C)/4 (no next-open available), other levels as standard.
    """

    def __init__(self, mode: str = "standard") -> None:
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
        self.mode = mode
        self._day: int | None = None
        self._h = self._l = self._c = Decimal(0)
        self._levels: PivotPointsValue | None = None

    @property
    def warmup(self) -> None:
        return None  # session-dependent: first value on the first bar of the second session

    def _compute(self, h: Decimal, l: Decimal, c: Decimal) -> PivotPointsValue:
        r = h - l
        if self.mode == "woodie":
            p = (h + l + 2 * c) / 4
        else:
            p = (h + l + c) / 3
        if self.mode in ("standard", "woodie"):
            return PivotPointsValue(
                p, 2 * p - l, p + r, h + 2 * (p - l), 2 * p - h, p - r, l - 2 * (h - p)
            )
        if self.mode == "fibonacci":
            return PivotPointsValue(
                p,
                p + Decimal("0.382") * r,
                p + Decimal("0.618") * r,
                p + r,
                p - Decimal("0.382") * r,
                p - Decimal("0.618") * r,
                p - r,
            )
        k = Decimal("1.1") * r
        return PivotPointsValue(
            p, c + k / 12, c + k / 6, c + k / 4, c - k / 12, c - k / 6, c - k / 4
        )

    def update(
        self, high: Decimal, low: Decimal, close: Decimal, ts: int
    ) -> PivotPointsValue | None:
        high, low, close = to_decimal(high), to_decimal(low), to_decimal(close)
        day = ist_session_day(int(ts))
        if self._day is None:
            self._day, self._h, self._l = day, high, low
        elif day != self._day:
            self._levels = self._compute(self._h, self._l, self._c)
            self._day, self._h, self._l = day, high, low
        else:
            self._h, self._l = max(self._h, high), min(self._l, low)
        self._c = close
        return self._levels
