# Derivatives, Options, and Volatility

Educational reference on options/vol. Not financial advice.

## Basics
- Call: right to BUY at strike K by expiry. Put: right to SELL at K. Buyer pays premium (long, limited loss); seller/writer receives it (short, obligation, potentially large loss).
- Payoff at expiry: call `max(S_T − K, 0)`; put `max(K − S_T, 0)`. P&L = payoff − premium (long) / premium − payoff (short).
- Value = intrinsic + extrinsic (time) value. Intrinsic: call `max(S−K,0)`, put `max(K−S,0)`. Extrinsic = premium − intrinsic; decays to 0 at expiry.
- Moneyness: ITM (intrinsic>0), ATM (S≈K), OTM (intrinsic=0). Forward moneyness uses forward price `F = S·e^{(r−q)T}`.
- Style: American (exercise anytime), European (expiry only). American calls on non-dividend stock ≈ never early-exercised; puts and dividend-payers can be.

## Put–call parity (European, same K, T)
- `C − P = S − K·e^{−rT}` (add PV of dividends: `C − P = S − D − K·e^{−rT}`).
- Uses: synthetic positions (synthetic long stock = long call + short put), arbitrage bound, implied dividend/rate. Violations → arbitrage (conversion/reversal).

## Black–Scholes intuition
- Assumes: GBM (lognormal S), constant σ and r, no arbitrage, continuous frictionless trading/hedging, European exercise. Real markets violate constant-σ (→ smile/skew) and continuity (jumps).
- `C = S·e^{−qT}·N(d1) − K·e^{−rT}·N(d2)`, `d1 = [ln(S/K)+(r−q+σ²/2)T]/(σ√T)`, `d2 = d1 − σ√T`. `N(d2)` ≈ risk-neutral prob of finishing ITM; `N(d1)` = call delta (×e^{−qT}).
- Price is monotonic in σ → invert market price to get implied volatility (no closed form; solve numerically).

## The Greeks (sensitivities)
- Delta (∂V/∂S): directional exposure. Call 0→1, put −1→0; ATM ≈ ±0.5. ≈ hedge ratio and ≈ risk-neutral P(ITM).
- Gamma (∂Δ/∂S = ∂²V/∂S²): convexity; peaks ATM near expiry. Long gamma = delta grows favorably (buy low/sell high when re-hedging); short gamma = the reverse (bleeds on moves).
- Theta (∂V/∂t): time decay, negative for long options; accelerates ATM into expiry; short options collect theta but are short gamma.
- Vega (∂V/∂σ): sensitivity to IV (per 1 vol point); highest ATM and for longer T. Long options = long vega.
- Rho (∂V/∂r): rate sensitivity; matters for long-dated. 2nd order: Vanna (∂Δ/∂σ), Volga/Vomma (∂Vega/∂σ), Charm (∂Δ/∂t = delta decay).
- Gamma–theta tradeoff: long gamma is paid for with theta; profitable if realized moves > implied (realized var > implied var).

## Implied vs realized vol
- Realized (historical) vol: `σ_RV = √(k·Σ r_t²)` (close-to-close) or Parkinson/Garman–Klass (range-based, more efficient). Backward-looking.
- Implied vol: forward-looking, market's expected σ backed out of price. IV usually > RV on average (variance risk premium — sellers earn compensation for tail/gap risk).
- Long option makes money if realized vol exceeds the IV paid (gamma scalping), before costs.

## Vol surface: skew, smile, term structure
- Smile/skew: IV varies by strike. Equity indices show negative skew (downside puts bid up — crash insurance + leverage effect). FX shows a smile. Measured via 25-delta risk reversal (put IV − call IV) and butterfly.
- Term structure: IV vs expiry; usually upward (contango) in calm markets, inverts (backwardation) in stress. Forward vol = implied vol between two future dates.
- Sticky-strike vs sticky-delta: how the smile moves as spot moves (affects realized delta/vanna P&L).

## Common strategies
- Vertical spread: long+short same-type different strikes (bull call / bear put) — capped payoff, cheaper, defined risk.
- Straddle (same K call+put) / strangle (OTM call+put): long = bet on large move / rising IV (long vega+gamma, short theta); short = bet on quiet/high IV.
- Covered call: long stock + short call — income, caps upside, no downside protection below premium.
- Protective put / collar: long put (insurance) / financed by short call. Calendar spread: same K different expiries — long term structure/vega, short front theta. Butterfly/condor: pinned-range, defined risk.

## Assignment, expiry, settlement
- Short options risk early assignment (American), especially ITM near dividends (calls) or deep-ITM puts. Assignment turns options into stock/cash + margin demands.
- Pin risk: S ≈ K at expiry → uncertain exercise; residual unhedged stock position Monday. Cash-settled (index) vs physically-settled (single-name) differ. Auto-exercise if ITM by threshold at expiry.

## Futures, forwards, basis & carry
- Forward/futures fair value: `F = S·e^{(r+u−q)T}` (r rate, u storage, q yield/dividend/convenience). Basis = F − S.
- Contango (F>S, upward curve) vs backwardation (F<S). Carry/roll: holding a position earns/pays as futures roll toward spot; roll yield can dominate returns in commodities.
- Cost-of-carry links options too via the forward in Black-76 (`F`-based pricing for futures options).

## Scenario grid (long ATM straddle, illustrative)
| S move | IV −5 | IV flat | IV +5 |
|--------|-------|---------|-------|
| −10%   | +     | ++      | +++   |
| flat   | −−    | −(theta)| +     |
| +10%   | +     | ++      | +++   |
- Long straddle: profits from large moves (gamma) or rising IV (vega); bleeds theta if quiet — build the real grid in P&L dollars before trading.

## Margin & risk of short options
- Short options require margin scaled to tail risk (e.g. SPAN/portfolio margin stresses S and σ jointly). Vol spikes → margin expansion → forced covering at the worst price. Size to the stressed scenario, not the premium collected.

## Pitfalls → Fix
- Analyzing without full spec → always fix S, K, T, r, q/dividends, and σ assumption before pricing/Greeks.
- Selling options as "free income" → short gamma + unlimited/large tail loss; size to worst-case, not to premium.
- Ignoring vega when trading direction → a right-direction move can lose if IV collapses (post-event vol crush); separate directional, vol, and carry exposure.
- Buying pre-earnings options → elevated IV crushes after the event; realized must beat inflated implied.
- Assuming BS constant vol → use the surface; account for skew, jumps, and stochastic vol.
- Delta-hedging discretely / ignoring costs → P&L = gamma scalping minus transaction costs and slippage; discrete rehedge adds path noise.
- Forgetting theta on long premium and assignment/pin risk on shorts → model decay; manage/close shorts before expiry and around dividends.
- Confusing IV with a forecast → IV is a risk-neutral price, not a physical probability; the variance risk premium biases it above RV.
- Scenario blindness → build a P&L grid across S × σ × time (and per-Greek) before entering.
