# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Momentum oscillators: RSI, KDJ, Stochastic, StochRSI, Williams %R, CCI, ROC, Momentum, TSI, AO, UO, Fisher, KST, Coppock, CMO, Connors RSI, RVGI."""
# mirror: kernel-verbatim port (gap 0006)

from tantra.indicators.momentum.awesome_oscillator import AwesomeOscillator
from tantra.indicators.momentum.cci import Cci
from tantra.indicators.momentum.chande_momentum import ChandeMomentum
from tantra.indicators.momentum.connors_rsi import ConnorsRsi
from tantra.indicators.momentum.coppock_curve import CoppockCurve
from tantra.indicators.momentum.fisher_transform import (
    FisherTransform,
    FisherValue,
)
from tantra.indicators.momentum.kdj import Kdj
from tantra.indicators.momentum.kst import Kst, KstValue
from tantra.indicators.momentum.momentum_ind import Momentum
from tantra.indicators.momentum.relative_vigor_index import (
    RelativeVigorIndex,
    RvgiValue,
)
from tantra.indicators.momentum.roc import Roc
from tantra.indicators.momentum.rsi import Rsi
from tantra.indicators.momentum.stoch_rsi import StochRsi, StochRsiValue
from tantra.indicators.momentum.stochastic import Stochastic, StochasticValue
from tantra.indicators.momentum.tsi import Tsi, TsiValue
from tantra.indicators.momentum.ultimate_oscillator import UltimateOscillator
from tantra.indicators.momentum.williams_r import WilliamsR

__all__ = [
    "AwesomeOscillator",
    "Cci",
    "ChandeMomentum",
    "ConnorsRsi",
    "CoppockCurve",
    "FisherTransform",
    "FisherValue",
    "Kdj",
    "Kst",
    "KstValue",
    "Momentum",
    "RelativeVigorIndex",
    "Roc",
    "Rsi",
    "RvgiValue",
    "StochRsi",
    "StochRsiValue",
    "Stochastic",
    "StochasticValue",
    "Tsi",
    "TsiValue",
    "UltimateOscillator",
    "WilliamsR",
]
