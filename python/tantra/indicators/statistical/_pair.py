# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Shared helpers for paired-series statistics."""
# mirror: kernel-verbatim port (gap 0006)

from __future__ import annotations

from decimal import Decimal

from tantra.types import to_decimal


def simple_return(prev: Decimal, cur: Decimal) -> Decimal:
    """cur/prev - 1; 0.0 when prev <= 0 (undefined)."""
    prev, cur = to_decimal(prev), to_decimal(cur)
    return cur / prev - Decimal(1) if prev > 0 else Decimal(0)


def cov_var(
    xs: list[Decimal], ys: list[Decimal], ddof: int
) -> tuple[Decimal, Decimal, Decimal]:  # mirror accommodation (gap 0006)
    """(cov, var_x, var_y) with divisor n - ddof."""
    xs = [to_decimal(x) for x in xs]
    ys = [to_decimal(y) for y in ys]
    n = len(xs)
    mx, my = sum(xs, Decimal(0)) / n, sum(ys, Decimal(0)) / n
    d = n - ddof
    cxy = sum(((x - mx) * (y - my) for x, y in zip(xs, ys)), Decimal(0)) / d
    vx = sum(((x - mx) ** 2 for x in xs), Decimal(0)) / d
    vy = sum(((y - my) ** 2 for y in ys), Decimal(0)) / d
    return cxy, vx, vy
