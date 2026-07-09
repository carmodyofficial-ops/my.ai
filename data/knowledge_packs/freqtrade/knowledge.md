# Freqtrade — Strategy Framework

## What it is
Open-source Python crypto trading bot (GPL-3.0). Backtest, hyperopt, dry-run (paper), and live from one strategy class. Vectorized pandas OHLCV per pair; conditions are boolean masks over DataFrame columns.

## Setup & layout
```bash
pip install freqtrade                 # or docker: freqtradeorg/freqtrade
freqtrade create-userdir --userdir user_data
freqtrade new-config --config user_data/config.json
freqtrade new-strategy --strategy MyStrat   # -> user_data/strategies/MyStrat.py
```
`user_data/{strategies,data,backtest_results,hyperopts}/` + `config.json`. **Strategy file name must match the class name.**

## Strategy class (subclass `IStrategy`)
```python
from freqtrade.strategy import IStrategy, IntParameter
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib

class MyStrat(IStrategy):
    timeframe = '5m'
    stoploss = -0.10                          # hard stop, -10%
    minimal_roi = {"0": 0.10, "30": 0.04, "60": 0}  # minutes -> target
    trailing_stop = False
    startup_candle_count = 30                 # indicator warmup (CRITICAL)
    can_short = False
    process_only_new_candles = True

    buy_rsi = IntParameter(20, 40, default=30, space="buy")  # hyperoptable

    def populate_indicators(self, dataframe, metadata):
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['ema20'] = ta.EMA(dataframe, timeperiod=20)
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        return dataframe

    def populate_entry_trend(self, dataframe, metadata):
        dataframe.loc[
            (dataframe['rsi'] < self.buy_rsi.value)
            & (dataframe['close'] > dataframe['ema20'])
            & (dataframe['volume'] > 0), 'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe, metadata):
        dataframe.loc[(dataframe['rsi'] > 70), 'exit_long'] = 1
        return dataframe
```
- **`populate_indicators`**: compute all columns once per pair. No trade logic here.
- **`populate_entry_trend`**: set `enter_long` (and `enter_short` if `can_short=True`).
- **`populate_exit_trend`**: set `exit_long`/`exit_short`. Exits also come from ROI/stoploss/trailing.
- Always require `volume > 0` (skips halted/zero-volume candles).
- Callbacks for finer control: `custom_stoploss`, `custom_entry_price`, `confirm_trade_entry`, `adjust_trade_position` (DCA/partial exits).

## Exit priority — ROI, stoploss, trailing
- **`minimal_roi`**: time-decaying take-profit. `{"0":0.10,"30":0.04,"60":0}` = 10% immediately, 4% after 30min, break-even (any profit) after 60min. `"0"` key is mandatory.
- **`stoploss`**: fixed fractional hard stop (negative). Always set.
- **Trailing stop**:
```python
trailing_stop = True
trailing_stop_positive = 0.02          # trail 2% below peak once...
trailing_stop_positive_offset = 0.03   # ...profit reaches 3%
trailing_only_offset_is_reached = True # don't trail until offset hit
```
Offset must be > positive, else it errors. Exit precedence at a candle: stoploss/trailing, then ROI, then signal.

## config.json
```json
{ "dry_run": true, "dry_run_wallet": 1000,
  "stake_currency": "USDT", "stake_amount": "unlimited",
  "max_open_trades": 5, "tradable_balance_ratio": 0.99,
  "timeframe": "5m", "fee": 0.001,
  "exchange": { "name": "binance", "key": "", "secret": "",
    "pair_whitelist": ["BTC/USDT","ETH/USDT"], "pair_blacklist": ["*/BNB"] },
  "pairlists": [{"method": "StaticPairList"}],
  "order_types": {"entry":"limit","exit":"limit","stoploss":"market"} }
```
- `stake_amount`: fixed number or `"unlimited"` (splits balance across `max_open_trades`).
- `fee`: model the true taker/maker fee; idealized fills inflate results.
- Strategy attributes can be overridden in config (config wins).

## Workflow
```bash
freqtrade download-data --timerange 20230101-20231231 -t 5m
freqtrade backtesting --strategy MyStrat --timerange 20230101-20230630
freqtrade hyperopt --strategy MyStrat --hyperopt-loss SharpeHyperOptLoss \
    --spaces buy sell roi stoploss trailing --epochs 100
freqtrade plot-dataframe --strategy MyStrat -p BTC/USDT   # HTML chart
freqtrade trade --strategy MyStrat --dry-run              # paper; drop flag for live
```
- **Hyperopt** searches `*Parameter` values (`IntParameter/DecimalParameter/CategoricalParameter`) declared in the strategy, per `--spaces` (buy/sell/roi/stoploss/trailing/protection). Loss function defines "better" (`SharpeHyperOptLoss`, `SortinoHyperOptLoss`, `OnlyProfitHyperOptLoss`, custom).
- **`--timeframe-detail`** in backtest replays intra-candle order for more realistic fills.

## Informative (higher-timeframe) data
- Use a higher timeframe to gate a lower-timeframe entry (e.g. 1h trend filter on a 5m strategy) without lookahead.
```python
from freqtrade.strategy import informative
@informative('1h')
def populate_indicators_1h(self, dataframe, metadata):
    dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)
    return dataframe
# -> merged column 'ema50_1h' available in the base timeframe
```
- Manual path: declare `informative_pairs()`, fetch with `self.dp.get_pair_dataframe`, align with `merge_informative_pair` (forward-fills correctly, no future leak).

## Key callbacks
- `custom_stoploss(pair, trade, current_time, current_rate, current_profit, ...)` -> dynamic/ATR trailing stop.
- `confirm_trade_entry` / `confirm_trade_exit` -> last-moment veto (spread, slippage checks).
- `adjust_trade_position` -> position adjustment: DCA-in or partial scale-out (requires `position_adjustment_enable=True`).
- `custom_entry_price` / `custom_exit_price` -> override limit price. `leverage()` -> per-trade leverage on futures.

## PairLists & Protections
- **PairLists** (chained handlers): `StaticPairList` (fixed whitelist), `VolumePairList` (auto top-N by quote volume), then filters `AgeFilter`, `PriceFilter`, `SpreadFilter`, `RangeStabilityFilter`, `ShuffleFilter`.
- **Protections** (risk circuit breakers): `StoplossGuard` (pause after N stoplosses), `MaxDrawdown`, `CooldownPeriod`, `LowProfitPairs` — pause a pair/global after bad streaks.

## Dry-run vs live
- **Dry-run**: simulated wallet, real market data, no real orders. Same code path as live. Always validate here first.
- **Live**: real keys, real funds — flip `dry_run:false` + valid `key/secret`. Never do this before a passing dry-run soak.

## Gotchas -> Fix
- **Repainting / lookahead in `populate_*`** -> using future data to trade the current candle inflates backtests, fails live. Never `.shift(-1)` future values in; row N must not see N+1. Fix: run `freqtrade lookahead-analysis`; only use data available at candle close.
- **Repainting indicators** (some indicators recompute on new data, e.g. certain pivot/ZigZag/non-causal filters) -> backtest sees a value live won't. Fix: prefer causal indicators; verify with `freqtrade recursive-analysis`.
- **Insufficient warmup** -> `startup_candle_count` < longest indicator period leaves cold indicators; backtest ≠ live. Fix: set `startup_candle_count >= max(periods)`.
- **Timeframe mismatch** -> strategy `timeframe` vs downloaded data vs informative pairs disagree -> empty/NaN columns. Fix: download the exact `-t` timeframe; use `@informative` decorator / `informative_pairs()` for higher TFs, and `merge_informative_pair` to align (avoids lookahead).
- **Unrealistic costs** -> default fee/no slippage overstates returns. Fix: set true `fee`; use realistic order types and `--timeframe-detail`.
- **Hyperopt overfitting** -> best epoch is curve-fit to the window. Fix: validate the chosen params on a separate **out-of-sample** timerange before trusting; prefer robust loss (Sortino/profit+drawdown).
- **Sharpe-only hyperopt is gameable** by under-trading (few lucky trades). Fix: require a min trade count or a profit+drawdown objective; a high in-sample win-rate with huge avg trade duration = holding losers (check OOS).
- **ROI vs signal exit confusion** -> ROI/stoploss fire independent of `exit_long`; you may exit "early" unexpectedly. Fix: reason about exit precedence (stoploss/trailing > ROI > signal).
- **Committing API keys** -> secrets leak via git. Fix: keep `key/secret` in an env/`config-private.json` outside git; `.gitignore` it.
- **Skipping dry-run** -> untested logic on real money. Fix: dry-run soak first, always.
- **`process_only_new_candles=False`** -> recomputes every tick, slow and can differ from backtest. Fix: keep it `True`.
