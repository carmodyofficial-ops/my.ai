# Backtesting and Market Data Quality Guard

Updated: 2026-06-22T01:00:24.487450+00:00

## Required backtest critique checklist

Every serious strategy/backtest review should consider:

- Slippage.
- Fees and commissions.
- Bid/ask spread.
- Market impact.
- Timestamp alignment.
- Lookahead bias.
- Survivorship bias.
- Corporate actions, where relevant.
- Data cleaning rules.
- Missing candles/ticks.
- Exchange outages.
- Walk-forward validation.
- Train/test leakage.
- Multiple-testing and overfitting.
- Parameter stability.
- Capacity constraints.
- Regime dependence.

## Intraday strategy warning

Intraday strategies are especially sensitive to:

- Spread assumptions.
- Queue position.
- Partial fills.
- Latency.
- Session boundaries.
- Timezone handling.
- Event/news windows.

## Crypto strategy warning

Crypto backtests must account for:

- Exchange-specific liquidity.
- Funding rates for perpetuals.
- Maker/taker fees.
- Liquidation mechanics.
- Cross-exchange price differences.
- Weekend/24-7 sessions.
- API outage survivorship.

## Response discipline

Do not present backtest results as live edge without caveats.

Do not give personalized financial advice.

Always state assumptions and limitations.

When calculations are required, show formulas and deterministic arithmetic.
