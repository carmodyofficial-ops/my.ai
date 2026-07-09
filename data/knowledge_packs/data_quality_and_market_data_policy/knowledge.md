# Data Quality and Market Data Policy

Purpose: Prevent bad finance conclusions from bad data.

Rules:
- Current market analysis requires current data.
- If data may have changed, fetch or ask for data.
- Never use stale prices as current.
- Always state data timestamp.
- Verify ticker, venue, currency, and split/adjustment basis.
- For backtests, preserve raw and adjusted data distinction.
- Handle missing data explicitly.
- Do not silently forward-fill prices unless appropriate.
- Beware survivorship bias in equity universes.

Data checks:
- source
- timestamp
- timezone
- frequency
- corporate action adjustment
- missing values
- outliers
- duplicate rows
- lookahead fields
