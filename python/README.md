# व्यापार

Python SDK for the Tantra trading core (compiled via PyO3; see README).

## REST client

`tantra.client` is a stdlib-only client for the runtime's `/api/v2` contract. Numbers come
back as `Decimal`; money inputs must be `Decimal`, `int` or `str` (never `float`).

```python
from decimal import Decimal
from tantra.client import Client

with Client.http("http://127.0.0.1:8000", token="...") as c:   # or Client.from_config()
    run = c.run_backtest(strategy="sma_crossover", universe="RELIANCE.NSE",
                         start="2024-01-01", end="2024-06-01",
                         initial_capital=Decimal("1000000"))
    journal = c.backtest_journal(run.run_id)
```

`Client.from_config()` reads the `runtime` block (`url`, `token`; supports `{env:VAR}` and
`{file:path}`) of `tantra.jsonc` found by walking up from the cwd, merged over
`~/.config/tantra/tantra.jsonc`. Failures raise `ClientError(status, code, message, reason)`.
`Client.inproc` is not available yet. Regenerate typed models with
`python3 scripts/gen_client_models.py` (`--check` in CI).
