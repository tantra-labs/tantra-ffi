# wheel surface (ex 0006): Decimal-canonical indicators registry (mirrors tantra_examples/_kernel/indicators public API)
# stand-in closure for tantra-examples gap 0006

"""Statistical indicators: correlation, beta, covariance, z-score, Hurst exponent."""
# mirror: kernel-verbatim port (gap 0006)

from tantra.indicators.statistical.beta import Beta
from tantra.indicators.statistical.correlation import Correlation
from tantra.indicators.statistical.covariance import Covariance
from tantra.indicators.statistical.hurst_exponent import HurstExponent
from tantra.indicators.statistical.zscore import ZScore

__all__ = ["Beta", "Correlation", "Covariance", "HurstExponent", "ZScore"]
