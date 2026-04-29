# TP-017: Implement mocked market data, trending stocks/ETFs, and SignalR streaming — Status

**Current Step:** Not Started
**Status:** 🔵 Ready for Execution
**Last Updated:** 2026-04-29
**Review Level:** 2
**Review Counter:** 0
**Iteration:** 0
**Size:** L

> **Hydration:** Checkboxes represent meaningful outcomes, not individual code changes. Workers expand steps when runtime discoveries warrant it — aim for 2-5 outcome-level items per step, not exhaustive implementation scripts.

---

### Step 0: Preflight
**Status:** ⬜ Not Started

- [ ] Required files and paths exist
- [ ] Dependencies satisfied
- [ ] Current MarketData shell state confirmed
- [ ] No external provider/runtime requirement confirmed

---

### Step 1: Implement deterministic mocked market-data contracts and services
**Status:** ⬜ Not Started

- [ ] Add response types for symbols, OHLCV candles, timeframes, indicators, and trending scores
- [ ] Add deterministic stock/ETF symbol catalog
- [ ] Add stable candle generation for charting and tests
- [ ] Add simple moving-average, RSI, and MACD support
- [ ] Add explainable trending score with news-sentiment placeholder
- [ ] Targeted MarketData project build passes

---

### Step 2: Expose MarketData HTTP endpoints through the API
**Status:** ⬜ Not Started

- [ ] Add API reference to `ATrade.MarketData`
- [ ] Register MarketData services in API startup
- [ ] Map trending endpoint
- [ ] Map candle endpoint with validation
- [ ] Map or include indicator payloads with documented shape
- [ ] Preserve existing endpoints
- [ ] Targeted API smoke checks pass

---

### Step 3: Add SignalR real-time market-data streaming
**Status:** ⬜ Not Started

- [ ] Add market-data SignalR hub
- [ ] Add deterministic mocked update publisher
- [ ] Keep HTTP endpoints usable without streaming clients
- [ ] Preserve compatibility with future NATS/TimescaleDB/LEAN-backed updates
- [ ] Targeted hub/build checks pass

---

### Step 4: Add market-data feature verification
**Status:** ⬜ Not Started

- [ ] Create `tests/apphost/market-data-feature-tests.sh`
- [ ] Verify solution build and API reference
- [ ] Assert `/health` remains healthy
- [ ] Assert trending stocks/ETFs and score components
- [ ] Assert timeframe/indicator behavior and invalid validation
- [ ] Assert SignalR hub registration/startup without external services
- [ ] Targeted market-data feature test passes

---

### Step 5: Update docs for mocked data and future real signals
**Status:** ⬜ Not Started

- [ ] Update paper-trading workspace architecture doc
- [ ] Update module map current-state notes
- [ ] Update overview if runtime surface changed
- [ ] Update README if current status changed materially

---

### Step 6: Testing & Verification
**Status:** ⬜ Not Started

- [ ] FULL test suite passing
- [ ] Runtime infrastructure test passes or cleanly skips when no engine is available
- [ ] All failures fixed
- [ ] Solution build passes

---

### Step 7: Documentation & Delivery
**Status:** ⬜ Not Started

- [ ] "Must Update" docs modified
- [ ] "Check If Affected" docs reviewed
- [ ] Discoveries logged

---

## Reviews

| # | Type | Step | Verdict | File |
|---|------|------|---------|------|

---

## Discoveries

| Discovery | Disposition | Location |
|-----------|-------------|----------|

---

## Execution Log

| Timestamp | Action | Outcome |
|-----------|--------|---------|
| 2026-04-29 | Task staged | PROMPT.md and STATUS.md created |

---

## Blockers

*None*

---

## Notes

*Reserved for execution notes*
