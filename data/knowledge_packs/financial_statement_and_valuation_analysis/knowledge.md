# Financial Statement & Valuation Analysis
## Three statements & how they link
- **Income statement** (accrual): revenue − COGS = gross profit; − opex = operating income (EBIT); EBIT − interest − tax = net income. Net income ≠ cash. Watch revenue-recognition timing (ASC 606: recognize as performance obligations are satisfied).
- **Balance sheet**: Assets = Liabilities + Equity. Snapshot. Retained earnings roll forward by net income − dividends.
- **Cash flow** ties them: `CFO = net income + D&A ± other non-cash − ΔNWC`; `FCF = CFO − capex`; **FCFF** = EBIT(1−t) + D&A − capex − ΔNWC. Net income flows to equity; cash flows to the BS cash line.
## Key ratios
- Margins: gross = GP/rev; operating = EBIT/rev; net = NI/rev; **EBITDA margin** = EBITDA/rev (proxy, ignores capex & WC).
- Returns: **ROE** = NI/equity; **ROA** = NI/assets; **ROIC** = NOPAT/invested capital, NOPAT = EBIT(1−t). Value created when **ROIC > WACC**.
- Leverage/coverage: net debt/EBITDA (>4–5× stressed); interest coverage = EBIT/interest; current ratio = CA/CL; quick ratio excludes inventory.
- Working-capital cycle: **DSO** = AR/rev×365; **DIO** = inv/COGS×365; **DPO** = AP/COGS×365; **CCC** = DSO + DIO − DPO. Rising DSO = collection/quality risk.
## DuPont
- 3-step: `ROE = net margin × asset turnover × equity multiplier` (NI/rev × rev/assets × assets/equity). Decompose to see if ROE is margin, efficiency, or *leverage*-driven (leverage-inflated ROE is fragile).
## Earnings quality / accruals red flags
- **Accruals ratio** high (NI ≫ CFO) → earnings not cash-backed. Sloan accrual anomaly: high accruals predict weak forward returns.
- AR or inventory growing faster than revenue; capitalizing costs that should be expensed; falling tax rate flattering EPS; heavy non-GAAP add-backs; frequent "one-time" charges; cut D&A/lengthened useful lives; big Q4 true-ups.
## DCF
- Project **FCFF** over explicit horizon (5–10y), discount at **WACC**, add terminal value, sum to enterprise value; EV − net debt = equity value; ÷ diluted shares = per share.
- **WACC** = (E/V)·Re + (D/V)·Rd·(1−t); Re via CAPM = Rf + β·ERP.
- **Terminal value**: Gordon growth `TV = FCF_n(1+g)/(WACC−g)` with g ≤ long-run GDP (~2–3%, must be < WACC); or **exit multiple** (EV/EBITDA). Cross-check the two; TV often 60–80% of value → sensitize.
## Comps / multiples
- **EV/EBITDA** (capital-structure neutral), **EV/Sales** (pre-profit), **P/E** (equity, post-leverage), PEG, P/B (financials), FCF yield. Use EV multiples with EV-level numerators (EBIT/EBITDA/sales); P/E with equity earnings — don't mix.
- **EV** = market cap + total debt + preferred + minority interest − cash & equivalents. Add pension deficits/operating leases where material.
- Trailing vs forward; adjust for one-offs, leases, SBC, minority interest. Peer set must match margins/growth/risk. A justified multiple ties to fundamentals: P/E ≈ payout×(1+g)/(r−g); higher ROIC and growth, lower risk ⇒ higher fair multiple.
## Solvency, liquidity & footnotes
- Liquidity: current & quick ratios, CFO/current liabilities; can they fund the next 12m? Solvency: debt/equity, net debt/EBITDA, and the **maturity wall** (when does debt come due, at what rate on refi?).
- Off-balance-sheet & hidden claims: operating leases (now capitalized under ASC 842/IFRS 16), pension/OPEB deficits, purchase commitments, contingent liabilities, VIEs, factoring/receivables sales flattering DSO.
- Dilution: options, RSUs, convertibles, warrants — use **fully diluted** and treasury-stock method; watch convertible overhang.
## Owner earnings & cross-checks
- **Owner earnings** ≈ NI + D&A − maintenance capex ± ΔNWC (Buffett): the cash a passive owner could extract. Compare to reported earnings for quality.
- Cross-check valuations: DCF vs comps vs asset/sum-of-parts should triangulate; large gaps mean a wrong assumption somewhere. Reverse-DCF: back out the growth the current price implies, then judge if it's plausible.
- Reinvestment math: sustainable growth `g = ROIC × reinvestment rate`. Growth funded above ROIC destroys value.
## Sector adjustments
- **Banks/insurers**: EV/EBITDA meaningless (debt is raw material). Use P/B, P/TBV, ROE vs cost of equity, and dividend-discount / residual-income models; watch net interest margin, loan-loss provisions, capital ratios.
- **Real estate/REITs**: value on **FFO/AFFO** and cap rates, not EPS (D&A is huge and non-economic here).
- **Early-stage/high-growth**: negative FCF — use EV/Sales, rule-of-40 (growth% + FCF margin% ≥ 40), unit economics (LTV/CAC, payback, cohort retention, contribution margin), and dilution trajectory.
- **Cyclicals**: normalize earnings across the cycle (mid-cycle margins) — trailing P/E looks lowest at peak earnings (value trap) and highest at trough.
## Scenario discipline
- Value a range, not a point: bear/base/bull with explicit driver assumptions (growth, margin, WACC, exit multiple). Probability-weight; the spread *is* the risk.
- Anchor to fundamentals, not narrative — prefer cash flow evidence over the story. State the assumptions that would break the thesis.
## Gotchas -> Fix
- **EPS up but cash down**: accruals/receivables ballooning — check ΔNWC, DSO trend, CFO vs NI.
- **Buybacks masking dilution**: SBC issues shares while cash buys them back — track diluted count over time, treat SBC as a real cost, not an add-back.
- **EV/EBITDA looks cheap**: EBITDA ignores capex — high-capex firm isn't cheap; use EV/(EBITDA−capex) or FCF.
- **DCF says anything you want**: TV + WACC dominate. Small g/WACC changes swing value wildly — run a sensitivity grid, don't quote a point estimate.
- **ROE high on leverage**: DuPont-decompose; equity multiplier doing the work = fragile, rate-sensitive.
- **Non-GAAP "adjusted" everything**: recurring costs (SBC, restructuring every year) added back inflate earnings — reconcile to GAAP and CFO.
- **Growth capex vs maintenance**: lumping them understates true owner FCF; separate to value the going concern.
- **Negative working capital as free funding**: great until growth stalls or terms tighten — model the reversal.
- **Comparing P/E across different leverage**: leverage shifts P/E — use EV/EBIT to neutralize capital structure.
