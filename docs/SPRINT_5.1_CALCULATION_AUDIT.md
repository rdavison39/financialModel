# Sprint 5.1 — Financial Calculation Path Audit

**Project:** Davison Financial Model  
**Sprint:** 5.1  
**Purpose:** Establish exactly where historical/benchmark calculations are performed before changing code.  
**Status:** Audit complete — **no production code changed**.

## 1. Sprint 5 architectural objective

Sprint 5 exists to eliminate duplicate financial calculations between the Windows Tkinter client and the FastAPI/web client.

The target rule is:

> Financial calculations have one authoritative implementation in the service layer. Desktop and web clients consume the same calculated results and are responsible only for presentation/UI behavior.

This audit is intentionally descriptive. It does not move code or change behavior.

---

## 2. Audited components

The current implementation was reviewed across these areas:

- `src/services/portfolio_history_service.py`
- `src/services/account_comparison_history_service.py`
- `src/gui/graphs_tab.py`
- `src/api/main.py`
- Portfolio History web template/chart data path
- Portfolio History tests
- Existing project architecture documentation

The review also considered the later incremental changes that added:

- four Portfolio History views
- TSX benchmark handling
- trading-day filtering
- BMO/NB combined brokerage lines
- web chart date alignment

### Source-control note

The available full-project ZIP predates some of the later Sprint 4 incremental changes. The audit therefore uses the full project as the base and overlays the later Portfolio History/web incremental source files that are available in the project workspace. This is important because Sprint 5 must ultimately be performed against the user's latest Windows project, which remains the source of truth.

---

# 3. Current calculation ownership

| Calculation / behavior | Current desktop | Current web | Service layer | Finding |
|---|---|---|---|---|
| Raw portfolio history retrieval | `PortfolioHistoryService` | `PortfolioHistoryService` | Yes | Shared retrieval |
| Selected-account aggregation | `PortfolioHistoryService.get_aggregated_history()` | Same service | Yes | Shared raw aggregation |
| Portfolio Value display | GUI formatting | API/web formatting | No separate calculation required | Acceptable |
| `% Growth Since Start` | `GraphsTab._transform_history()` | `_portfolio_history_series()` | No | **Duplicated calculation** |
| `Day's Gain/Loss` | `GraphsTab._transform_history()` | `_portfolio_history_series()` | No authoritative shared calculation | **Duplicated calculation** |
| `% Day's Gain/Loss` | `GraphsTab._transform_history()` / snapshot fields | `_portfolio_history_series()` | No | **Duplicated calculation** |
| TSX benchmark raw history | `PortfolioHistoryService.get_benchmark_history()` | Same service | Yes | Shared retrieval |
| TSX `% Growth Since Start` | Desktop GUI benchmark normalization | `_benchmark_series()` | No | **Duplicated calculation** |
| TSX `% Day's Gain/Loss` | Desktop GUI previous-close logic | `_benchmark_series()` | No | **Duplicated calculation** |
| Effective benchmark start date | Desktop GUI uses first portfolio history date | Web has separate logic | No | **Duplicated policy** |
| Trading-day filtering | Desktop GUI | Web `_trading_dates()` + filtering | No | **Duplicated policy** |
| BMO combined history | Desktop GUI | Web `_brokerage_history_series()` | Raw aggregation only | **Duplicated transformation/policy** |
| NB combined history | Desktop GUI | Web `_brokerage_history_series()` | Raw aggregation only | **Duplicated transformation/policy** |
| Account `% Growth Since Start` | Desktop account/history logic | Web `_account_history_series()` | No | **Duplicated calculation** |
| Benchmark date-to-portfolio-date alignment | Desktop graph logic | Web `plot_dates` logic | No | **Duplicated policy** |

---

# 4. Existing service layer

## `PortfolioHistoryService`

The service currently provides two important categories of functionality.

### Raw portfolio history

- `get_value_on_or_before()`
- `get_history()`
- `get_aggregated_history()`

`get_aggregated_history()` is already an important shared foundation. It aggregates selected accounts using the latest known snapshot on or before each valuation date and uses the union of actual valuation dates.

### Raw benchmark history

- `get_benchmark_history()`

This retrieves daily benchmark closes from Yahoo Finance and returns `BenchmarkHistoryPoint` objects.

### What the service does NOT currently own

The service does not currently own the interpretation of those raw points into:

- growth percentages
- daily percentage changes
- effective performance start dates
- trading-day filtering
- benchmark normalization
- brokerage comparison performance

Those policies are currently implemented above the service layer.

---

# 5. Desktop calculation path

The current desktop Portfolio History path is approximately:

```text
Tkinter GraphsTab
        |
        +--> PortfolioHistoryService.get_aggregated_history()
        |
        +--> PortfolioHistoryService.get_benchmark_history()
        |
        +--> GraphsTab performs transformations
                |
                +--> Portfolio Value
                +--> % Growth Since Start
                +--> Day's Gain/Loss
                +--> % Day's Gain/Loss
                +--> TSX growth normalization
                +--> TSX previous-close daily percentage
                +--> trading-day filtering
                +--> BMO/NB grouping and comparison
        |
        +--> Canvas presentation
```

The desktop therefore already uses the service for data retrieval, but the GUI still owns significant financial interpretation.

### Important desktop behavior identified

The desktop benchmark refresh logic deliberately limits benchmark retrieval to the effective portfolio-history range. In particular, when the requested period is longer than the available portfolio history, the benchmark starts at the first actual portfolio valuation rather than the beginning of the requested period.

For `% Day's Gain/Loss`, the desktop also retrieves additional benchmark history before the first plotted date so that the first plotted day's return can be calculated against the actual preceding trading-day close.

These are **financial rules**, not merely drawing behavior, and therefore belong in the shared calculation layer.

---

# 6. Web calculation path

The current web Portfolio History path is approximately:

```text
FastAPI /portfolio/history
        |
        +--> PortfolioHistoryService.get_aggregated_history()
        +--> PortfolioHistoryService.get_benchmark_history()
        |
        +--> src/api/main.py performs transformations
                |
                +--> _trading_dates()
                +--> _benchmark_series()
                +--> _portfolio_history_series()
                +--> _account_history_series()
                +--> _brokerage_history_series()
        |
        +--> JSON/chart data
        |
        +--> history.html / Chart.js
```

The web layer therefore contains substantial financial calculation logic of its own.

Examples include:

```python
(point.total_value - first) / first * Decimal("100")
```

for growth calculations, and benchmark daily percentage calculations based on previous benchmark values.

This is exactly the architecture problem Sprint 5 is intended to correct.

---

# 7. The TSX discrepancy identified during Sprint 4

The user-visible discrepancy was:

- Desktop TSX growth was approximately **-1.4%** for the displayed portfolio history beginning September 17, 2026.
- Web TSX growth was approximately **+21%** because its calculation used the requested date range beginning September 29, 2025 as the benchmark growth baseline.

The underlying issue was not Yahoo Finance data. It was **different effective-start-date rules in the two presentation layers**.

This is a direct example of why Sprint 5 is necessary.

The correct long-term design is not another web-specific patch. The effective benchmark start-date rule should be calculated once by the shared history service and consumed by both clients.

---

# 8. BMO/NB comparison calculation path

The BMO/NB comparison currently works conceptually as follows:

```text
Selected account IDs
        |
        +--> group by brokerage
                |
                +--> BMO account IDs
                +--> NB account IDs
        |
        +--> get_aggregated_history()
        |
        +--> calculate % Growth / % Daily Gain-Loss
```

The raw aggregation is shared through `PortfolioHistoryService`, but the transformation into performance percentages is independently implemented in the desktop and web layers.

Therefore BMO/NB comparison belongs in the Sprint 5 shared calculation design as well.

---

# 9. Account History

`AccountComparisonHistoryService` currently provides raw account histories:

- account identity
- snapshot dates
- total values

It does not own the performance transformations.

The web layer calculates account growth and daily metrics itself.

This should be addressed as part of the same shared calculation model rather than creating a separate web-only implementation.

---

# 10. What should move into the shared service layer

The audit identifies the following as candidates for authoritative service-level calculation methods.

### Portfolio performance

- effective valuation dates
- Portfolio Value series
- Gain/Loss series if still required by any client
- `% Growth Since Start`
- `Day's Gain/Loss`
- `% Day's Gain/Loss`

### Benchmark performance

- effective benchmark date range
- benchmark values aligned to portfolio valuation dates
- benchmark `% Growth Since Start`
- benchmark `% Day's Gain/Loss`
- preceding trading-day lookup for the first daily-return point

### Market/trading-day policy

- identification of actual benchmark trading dates
- filtering performance views to actual trading dates
- handling a requested start date that is a weekend/holiday

### Brokerage comparison

- grouping selected accounts by brokerage
- aggregated BMO history
- aggregated NB history
- BMO/NB `% Growth Since Start`
- BMO/NB `% Day's Gain/Loss`

The exact public method names should be chosen during Sprint 5.2 after reviewing all affected callers and tests.

---

# 11. What should remain outside the service layer

These are presentation concerns and should remain in the clients:

- Tkinter widgets
- Chart.js configuration
- HTML templates
- axis formatting
- colors
- line styles
- legends
- checkbox rendering
- browser/mobile layout
- desktop/mobile interaction
- HTTP request/response handling
- JSON serialization

The service should return structured calculated data; it should not know anything about Tkinter or HTML.

---

# 12. Proposed Sprint 5.2 boundary

Sprint 5.2 should **not** immediately rewrite both clients.

First create the shared calculation contract in `PortfolioHistoryService` (or a narrowly scoped supporting service if the existing service becomes too large).

Then add tests for the new shared calculations using deterministic data.

The first acceptance target should be:

```text
Existing raw history
        |
        v
Shared calculation service
        |
        +--> desktop can consume it
        +--> web can consume it
```

No UI redesign should occur in 5.2.

---

# 13. Controlled migration order

The recommended order remains:

```text
5.1  Audit                         COMPLETE
        |
        v
5.2  Shared calculation contract
        |
        v
5.3  Migrate desktop
        |
        v
5.4  Migrate web
        |
        v
5.5  Cross-client regression tests
        |
        v
5.6  Full Windows test suite
```

The desktop should be migrated before the web because the desktop behavior is the existing reference behavior that we are trying to preserve.

---

# 14. Sprint 5.1 acceptance criteria

- [x] Current calculation paths identified.
- [x] Service-layer responsibilities identified.
- [x] Desktop calculation responsibilities identified.
- [x] Web calculation responsibilities identified.
- [x] Duplicate financial calculations identified.
- [x] TSX discrepancy traced to duplicated effective-start-date logic.
- [x] BMO/NB duplicate transformation logic identified.
- [x] Account History duplicate transformation logic identified.
- [x] No production code changed.
- [x] Sprint 5.2 scope defined.

**Sprint 5.1 is complete.**

---

# 15. Important implementation rule for Sprint 5

Do not fix the identified discrepancies by adding more special cases to `src/api/main.py`.

The next code change should move the authoritative financial calculation into the shared service layer and then make both clients consume it.

That is the purpose of Sprint 5.
