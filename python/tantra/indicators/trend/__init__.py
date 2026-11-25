# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Trend indicators: MACD, Ichimoku, ADX, Aroon, Parabolic SAR, SuperTrend, Vortex, Chande Kroll, linear regression."""
# mirror: kernel-verbatim port (gap 0006)

from tantra.indicators.trend.adx import Adx, AdxValue
from tantra.indicators.trend.aroon import Aroon, AroonValue
from tantra.indicators.trend.chande_kroll_stop import (
    ChandeKrollStop,
    ChandeKrollStopValue,
)
from tantra.indicators.trend.ichimoku import Ichimoku
from tantra.indicators.trend.linear_regression import (
    LinearRegression,
    LinearRegressionValue,
)
from tantra.indicators.trend.macd import Macd, MacdValue
from tantra.indicators.trend.parabolic_sar import ParabolicSar
from tantra.indicators.trend.supertrend import Supertrend, SupertrendValue
from tantra.indicators.trend.vortex import Vortex, VortexValue

__all__ = [
    "Adx",
    "AdxValue",
    "Aroon",
    "AroonValue",
    "ChandeKrollStop",
    "ChandeKrollStopValue",
    "Ichimoku",
    "LinearRegression",
    "LinearRegressionValue",
    "Macd",
    "MacdValue",
    "ParabolicSar",
    "Supertrend",
    "SupertrendValue",
    "Vortex",
    "VortexValue",
]
