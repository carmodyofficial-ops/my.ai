# Quant Benchmark Rubric

Purpose: Judge financial/market/calculation capability.

Categories:
1. Mathematical correctness
2. Statistical reasoning
3. Financial concept accuracy
4. Market microstructure realism
5. Risk management
6. Backtest hygiene
7. Data quality awareness
8. Current-data discipline
9. Tool/calculation usage
10. Uncertainty and caveat handling

Hard fail conditions:
- Treats stale data as current.
- Gives specific trade recommendation without risk assumptions.
- Ignores fees/slippage in strategy claims.
- Uses lookahead-biased logic.
- Claims guaranteed returns.
- Confuses realized and unrealized P&L.
- Confuses correlation and causation.
- Performs complex calculations mentally when a deterministic tool is needed.
