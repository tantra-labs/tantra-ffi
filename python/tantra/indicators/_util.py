# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Shared validation."""
# mirror: kernel-verbatim port (gap 0006)


def check(period: int) -> int:
    if period < 1:
        raise ValueError(f"period must be >= 1, got {period}")
    return period
