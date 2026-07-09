# Portfolio Risk and Position Sizing

Educational quant reference — concepts and math, not financial advice.

## Risk per trade & R-multiples (start here)
- **R** = dollars risked on a trade = `entry - stop` (per unit) × units. Everything is measured in R.
- **R-multiple** of an outcome = `PnL / initial_risk`. A +2R win made twice the risk; a −1R loss hit the stop.
- **Expectancy (per-trade EV, in R)** = `winrate·avgWinR − lossrate·avgLossR`. Must be >0 after costs or no edge.
- Size from risk, not conviction: **`units = (equity · risk%) / (entry − stop)`**. Fix risk%, let the stop distance set the share count.
- Typical bound: **risk 0.25–2% of equity per trade**. Smaller when signals correlate.

## Fixed-fractional sizing
- Risk a constant fraction `f` of current equity each trade → position scales with the account (geometric growth, auto-deleverage in drawdown).
- Contrast **fixed-dollar** (constant $ risk, no compounding) and **units-per-fixed-amount** (e.g. 1 contract per $10k).
- Fixed-fractional never fully ruins on a single loss but suffers **compounding drag**: after a −x% then +x%, net = `(1−x)(1+x)−1 = −x²`.

## Kelly & fractional Kelly
- Kelly fraction maximizes long-run log-growth. Binary bet, net odds `b`, win prob `p`: **`f* = p − (1−p)/b = (p·b − (1−p))/b`**.
- Continuous/returns form: **`f* ≈ μ/σ²`** (mean excess return over variance); multi-asset: `f* = Σ⁻¹·μ`.
- **Full Kelly is too aggressive**: maximizes growth but expected drawdown ≈ 50%, and it assumes `p, b` known exactly. Estimation error → overbetting → ruin.
- Use **fractional Kelly (½ or ¼)**: half-Kelly keeps ~75% of the growth rate at ~1/4 the variance. Standard practice.
- Overbetting past `f*` **lowers** growth and eventually goes negative at `2·f*` — the growth curve is a downward parabola in `f`.

## Volatility targeting
- Scale exposure so realized portfolio vol hits a target: **`leverage = target_vol / realized_vol`** (e.g. 10% target ÷ 20% realized → 0.5×).
- Per-instrument: **`units = (equity · target_vol) / (σ_instrument · price)`**; ATR proxy → `units = equity·risk% / (k·ATR)`.
- Lowers exposure when vol spikes, raises it in calm — stabilizes Sharpe, tames tail drawdowns. Estimate σ with EWMA/GARCH; cap max leverage.

## Risk parity
- Allocate so each asset contributes **equal risk**, not equal dollars. Marginal risk contribution of `i`: `MRC_i = (Σw)_i / σ_p`; total `RC_i = w_i·MRC_i`; set all `RC_i` equal.
- Naïve (ignore correlation): `w_i ∝ 1/σ_i`. Full version solves for equal `RC` using the covariance matrix; usually levered up to a vol target.
- Diversifies risk sources vs cap-weighting (which is dominated by equities' vol).

## Correlated bets & diversification math
- **Sharpe of a book** rises with diversification: N *uncorrelated* equal-Sharpe bets → portfolio Sharpe ≈ `s·√N`. Add correlation ρ and the multiplier collapses toward `s·√(N/(1+(N−1)ρ))`.
- **Sizing correlated signals:** when two entries share risk (ρ high), treat them as one position for the per-trade risk budget, or size each down by `1/√(1+(N−1)ρ)`.
- Correlations are **regime-dependent and rise in stress** — assets that looked independent go to ρ≈1 in a crash, exactly when the diversification was supposed to protect you.

## Portfolio-level risk
- **Portfolio variance** `σ_p² = wᵀΣw`; two assets: `σ_p² = w₁²σ₁² + w₂²σ₂² + 2w₁w₂ρσ₁σ₂`. **Correlation ρ is the dominant term.**
- Correlated positions ≈ one big position: N bets at pairwise ρ have effective independent bets `≈ N/(1+(N−1)ρ)`. At ρ=1 you hold 1 fat trade.
- **Gross exposure** = Σ|position| / equity; **net** = Σ(longs−shorts)/equity. Gross measures leverage/liquidity risk; net measures directional/market risk.
- **Beta** to a benchmark: `β = cov(r,r_m)/var(r_m)`; portfolio `β = Σ w_i β_i`. Beta-neutral ⇒ Σ w_i β_i = 0.
- **Concentration:** cap single-name weight; watch effective N (`1/Σw_i²`, inverse Herfindahl) and factor/sector exposure.

## Drawdown, ruin, leverage math
- **Max drawdown** = worst peak-to-trough; recovery from −D needs `+D/(1−D)` (−50% needs +100%). Track duration, not just depth.
- **Risk of ruin** (fixed fraction, ruin = fractional threshold): rises sharply as edge→0 and bet size→up. Simple Bernoulli approx with no edge: `RoR = (q/p)^(units_of_capital)`; Monte-Carlo the real path distribution.
- **Kelly ↔ drawdown:** expected max DD ≈ Kelly fraction used (full Kelly ~50%, half ~25%) — a practical reason to bet fractional.
- **Leverage:** `L = assets/equity`. Liquidation when equity hits maintenance margin: adverse move `≈ (1 − mm·L)/L`. At 5× with 20% maint, a ~16% move wipes you. Model margin calls and funding cost.

## Stop placement
- **Volatility stops** (`k·ATR`) adapt to noise — avoid fixed % that gets shaken out in high vol or set too wide in calm.
- Place stops at **structural** levels (swing high/low, support) then size to the resulting risk — don't tighten the stop just to trade bigger.
- Wider stop → smaller size for constant R. Never move a stop against the position ("hoping"). Slippage/gaps mean realized loss can exceed 1R.

## Rebalancing
- Restores target weights as prices drift. **Calendar** (monthly/quarterly) vs **threshold/band** (rebalance when a weight drifts >X%).
- Trade-off: tighter bands/frequent = better tracking but more cost & tax; wider = cheaper but more drift.
- Mechanically **sells winners, buys losers** (contrarian) — a small "rebalancing bonus" for mean-reverting, uncorrelated assets.

## Pitfalls → Fix
- **Over-leverage / full Kelly** → use fractional Kelly or vol targeting; cap gross leverage; size for the tail, not the mean.
- **Correlated bets counted as diversified** → size on the covariance matrix; apply a correlation/cluster limit; measure effective N.
- **Sizing from conviction** → size from stop distance and fixed risk%, mechanically.
- **Ignoring compounding drag / recovery math** → remember −x then +x = −x²; a deep DD needs an outsized gain to recover.
- **Static % stops in changing vol** → use ATR/vol-scaled stops; re-estimate σ (EWMA).
- **Point-estimate σ, ρ** → they're noisy and rise in crises (ρ→1 exactly when you need diversification); stress with shocked correlations.
- **Position size set before stop** → set stop from structure first, then derive size.
- **Leverage without liquidation model** → compute the adverse move to maintenance margin; account for funding/borrow.
- **Optimizing weights on in-sample covariance** → shrink Σ (Ledoit-Wolf); risk parity/vol-target are more robust than mean-variance to estimation error.
- **Chasing after a loss (Martingale)** → doubling into losers maximizes ruin probability; keep risk% constant.
- **Confusing risk levels** → always state whether a number is per-trade, daily, portfolio, or account-level.
