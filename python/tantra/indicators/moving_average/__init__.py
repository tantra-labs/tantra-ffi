# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Moving averages: SMA, EMA, Wilder's RMA, WMA, HMA, VWMA, DEMA, TEMA, KAMA, McGinley, ALMA, LSMA."""
# ruff: noqa: E501
# mirror: kernel-verbatim port (gap 0006)

from tantra.indicators.moving_average.alma import Alma
from tantra.indicators.moving_average.averages import (
    Ema,
    Rma,
    Sma,
    Wma,
    make_ma,
)
from tantra.indicators.moving_average.dema import Dema
from tantra.indicators.moving_average.hma import Hma
from tantra.indicators.moving_average.kama import Kama
from tantra.indicators.moving_average.lsma import Lsma, linreg_fit
from tantra.indicators.moving_average.mcginley_dynamic import McGinleyDynamic
from tantra.indicators.moving_average.tema import Tema
from tantra.indicators.moving_average.vwma import Vwma

__all__ = [
    "Alma",
    "Dema",
    "Ema",
    "Hma",
    "Kama",
    "Lsma",
    "McGinleyDynamic",
    "Rma",
    "Sma",
    "Tema",
    "Vwma",
    "Wma",
    "linreg_fit",
    "make_ma",
]
