# CURRENT HANDOFF — September 29, 2026

> **This section is the current source-of-truth status for the project.** Older sections in this document preserve historical design information. If an older statement conflicts with this section, inspect the current code/tests before changing anything.

## Current development status

The Financial Model is a working Windows desktop application with a new FastAPI/Jinja2 web implementation developed through Sprint 4. The Windows Tkinter application remains intact.

**Latest full test result reported by the user: 137 tests passed.** Treat 137 passed as the current project baseline unless a later test run changes it. Do not claim a different result without actually running the tests.

### Sprint 4 status

| Stage | Status | Notes |
|---|---|---|
| 4.1 API Foundation | COMPLETE | FastAPI + `/api/health` |
| 4.2 Read-only Financial API | COMPLETE | Service-backed API endpoints |
| 4.3 Web Application Shell | COMPLETE | Responsive Jinja2 web shell |
| 4.4 Web Portfolio | COMPLETE | Portfolio dashboard and refresh |
| 4.5 Web History | COMPLETE | Portfolio/Account/Holdings History views |
| 4.6 Web Account Management | COMPLETE | Rename, type, Include/Exclude, account display |
| 4.7 Web Import | COMPLETE | BMO/Nesbitt Excel upload through existing importer services |
| 4.8 Raspberry Pi Deployment | PREPARED | Deployment artifacts created; actual Pi deployment not yet performed |
| 4.9A Windows/WireGuard Validation | COMPLETE | Windows-side validation/configuration only |
| 4.9B Raspberry Pi + WireGuard | NEXT | Wait until Pi environment is available |

## Current Sprint 4 artifacts

### Sprint 4.8

Deployment ZIP:

```text
Sprint_4.8_Raspberry_Pi_Deployment.zip
```

Contains only the deployment files added for 4.8:

```text
deploy/README.md
deploy/financial-model.service.template
deploy/install_pi.sh
tests/test_pi_deployment.py
```

The deployment script:

- installs Python/venv dependencies on Raspberry Pi OS,
- expects the tested project and existing SQLite database to already be copied to the Pi,
- creates/uses a Python virtual environment,
- installs `requirements.txt` and `requirements-web.txt`,
- creates the `financial-model.service` systemd service,
- starts FastAPI with Uvicorn on port 8000,
- checks `/api/health` when `curl` is available,
- does **not** run Alembic migrations.

### Sprint 4.9A

Validation ZIP:

```text
Sprint_4.9A_Windows_WireGuard_Validation.zip
```

This was deliberately developed without requiring the Pi. It contains Windows-side validation/configuration material and tests. It does **not** prove an actual WireGuard tunnel to the Pi.

## Planned Pi storage

The user has decided to use NVMe storage rather than relying on microSD for the long-term Pi installation.

Planned hardware:

```text
Raspberry Pi 5
    |
    +-- Official Raspberry Pi M.2 HAT+
            |
            +-- 2242 NVMe SSD
```

The selected HAT is the genuine Raspberry Pi M.2 HAT+ from CanaKit. The user plans to purchase it with a suitable 2242 NVMe SSD.

When the Pi is deployed, the intended arrangement is to put the Pi OS/application/database on the NVMe rather than moving only the SQLite database to USB.

## Next development/deployment step

Do **not** invent another application sprint yet. The existing Sprint 4 plan ends with remote/WAN access through WireGuard. The next practical step is:

**Sprint 4.9B — actual Raspberry Pi deployment and WireGuard end-to-end testing.**

This requires the Pi environment.

When the Pi is available, follow the deployment sequence documented in the Sprint 4 handoff document in `Sprint 4 - web based` and in `deploy/README.md` from the 4.8 ZIP.


# Davison Financial Model — Architecture

**Reviewed:** September 29, 2026

This document describes the implementation architecture of the current Financial Model application and is intended to provide enough context for future development without requiring the original conversation history.

---

# 1. Architectural Goals

The application deliberately favors:

- Simple Python modules.
- Tkinter/ttk GUI.
- SQLAlchemy ORM.
- SQLite persistence.
- Service classes for business logic.
- Brokerage-specific importers.
- Historical brokerage snapshots.
- Separate calculated valuation snapshots.
- Decimal-based financial calculations.
- Testable services.

The project does not currently use a repository pattern, dependency-injection framework, web API, or generic brokerage-plugin framework.

Do not introduce those abstractions unless the application's complexity actually requires them.

---

# 2. Layered Architecture

```text
                  Tkinter GUI
                       |
          +------------+-------------+
          |            |             |
          v            v             v
      Importers     Services      UI Settings
          |            |
          |            v
          |        SQLAlchemy
          |            |
          +------------+
                       |
                       v
                    SQLite
```

Market data is an external dependency:

```text
PortfolioValuationService
          |
          v
MarketPriceService
          |
          v
       yfinance
          |
          v
     Yahoo Finance
```

---

# 3. GUI Layer

Location:

```text
src/gui/
```

## `app.py`

Main Tk application.

Responsibilities:

- Create the root window.
- Configure styles.
- Build navigation.
- Instantiate each screen.
- Switch between screens.
- Start on Portfolio.

Screens are instantiated once and hidden/shown using `grid_remove()` / `grid()`.

Navigation:

```text
Portfolio
Portfolio History
Account Management
Account History
Holdings History
Import
```

---

## `portfolio_tab.py`

Current portfolio screen.

Responsibilities:

- Start portfolio valuation.
- Display consolidated values.
- Display brokerage summaries.
- Show progress.
- Run valuation work in a background worker.
- Communicate worker completion back to the Tk main thread.
- Generate `<<PortfolioUpdated>>` after successful updates.

Important threading rule:

**Worker threads must not directly manipulate Tkinter widgets.**

The worker communicates through a queue and the GUI thread consumes the results.

---

## `graphs_tab.py`

Portfolio History.

Responsibilities:

- Account selection.
- Historical portfolio value retrieval.
- Period selection.
- Benchmark selection.
- Graph/table display.
- Growth/change calculations.
- UI preference persistence.

Service dependencies:

```text
PortfolioHistoryService
UISettingsService
```

---

## `account_comparison_tab.py`

Account History.

Responsibilities:

- Account selection.
- Account historical values.
- Account comparison display.
- View/period/benchmark selection.
- UI preference persistence.

Service dependencies:

```text
AccountComparisonHistoryService
PortfolioHistoryService
UISettingsService
```

---

## `comparison_tab.py`

Holdings History.

Responsibilities:

- Account selection.
- From/To date comparison.
- Security-level position comparison.
- Consolidated value comparison.
- Quantity/value/gain changes.
- UI preference persistence.

Service dependency:

```text
PortfolioComparisonService
```

Special implementation detail:

Account checkboxes are dynamically destroyed/recreated when accounts are loaded. Therefore the current selection must be captured/restored using stable account keys.

Stable key:

```text
Brokerage|AccountNumber|AccountName
```

---

## `accounts_tab.py`

Account Management.

Responsibilities:

- Display accounts.
- Account sorting.
- Account selection.
- Account renaming.
- Account classification.
- Include/exclude account from portfolio.
- Account exports.
- Snapshot comparison.
- Holdings window.
- Current-value display.
- UI settings.

Service dependencies include:

```text
AccountService
AccountExportService
PortfolioService
PortfolioValuationService
UISettingsService
```

---

## `import_tab.py`

Import screen.

Responsibilities:

- Choose BMO directory.
- Choose Nesbitt Burns directory.
- Bulk import.
- Force re-import.
- Display import results.
- Persist import UI preferences.

Service:

```text
BulkImportService
```

---

## `account_holdings_window.py`

Separate account holdings display window.

It is opened from Account Management.

---

## `treeview_sort.py`

Shared Treeview sorting helpers.

Provides:

- text parsing
- numeric parsing
- numeric sort keys
- sortable Treeview headings

Financial numeric sorting uses `Decimal` rather than float.

---

# 4. Importer Layer

Location:

```text
src/importers/
```

## `bmo_importer.py`

Reads BMO Excel exports.

Produces intermediate imported structures:

```text
ImportedAccount
ImportedHolding
ImportedCash
```

It is responsible for understanding the BMO spreadsheet layout, not for writing database rows.

---

## `nesbitt_importer.py`

Reads Nesbitt Burns Excel exports.

Produces the same conceptual intermediate structures.

Cash rows are not treated as security holdings.

---

# 5. Service Layer

Location:

```text
src/services/
```

## `import_service.py`

Converts importer output into persistent database records.

Responsibilities:

- Create/find brokerage.
- Create/find account.
- Create/find company.
- Store ImportRecord.
- Store HoldingSnapshot.
- Store CashSnapshot.
- Enforce duplicate/re-import rules.
- Replace authoritative same-day snapshot when appropriate.

---

## `bulk_import_service.py`

Directory-level orchestration.

Responsibilities:

- Iterate files.
- Invoke the appropriate importer.
- Call ImportService.
- Continue after a bad file.
- Track imported/skipped/failed results.
- Support force re-import.

---

## `account_service.py`

Account business logic.

Responsibilities:

- Get/create accounts.
- Rename accounts.
- Update account type.
- Update `include_in_portfolio`.
- Return account summaries.
- Get all accounts.

The account unique identity is:

```text
brokerage + account_number
```

---

## `portfolio_service.py`

Reads the latest imported account portfolio.

Produces structures such as:

```text
PortfolioHolding
PortfolioCash
AccountPortfolio
```

It represents imported facts and does not perform live market valuation itself.

---

## `market_price_service.py`

External market-data integration.

Uses:

```text
yfinance
```

Responsibilities:

- Current prices.
- Previous closes.
- Historical daily prices.
- USD/CAD.
- Canadian symbol conversion.
- Canadian preferred-share conversion.
- Yahoo candidate symbols.
- Handling unavailable securities.

The static Yahoo symbol mapping is:

```text
src/config/yahoo_symbol_map.py
```

---

## `portfolio_valuation_service.py`

Calculates portfolio values from imported portfolio facts plus live market data.

Responsibilities:

- Current market value.
- CAD conversion.
- Daily change.
- Daily change percentage.
- Options contract multiplier.
- Account valuation.
- Consolidated valuation.
- Cached valuation retrieval.
- Save PortfolioSnapshot records.

For options, the current contract multiplier is 100.

---

## `portfolio_history_service.py`

Reads historical portfolio snapshots.

Responsibilities:

- Get value on/before a date.
- Get account history.
- Get aggregated selected-account history.
- Get benchmark history.

---

## `account_comparison_history_service.py`

Reads historical values for selected accounts.

Responsibilities:

- Return account metadata.
- Return historical points.
- Respect selected account IDs.
- Deduplicate account IDs.
- Respect date ranges.
- Exclude consolidated snapshots when account history is requested.

---

## `portfolio_comparison_service.py`

Provides security-level holdings comparisons between dates.

Responsibilities:

- Resolve selected accounts.
- Find snapshots applicable to From/To dates.
- Merge positions.
- Compare quantities.
- Compare market values.
- Compare average cost.
- Compare unrealized gains.
- Determine position status.
- Calculate portfolio-level comparison values.

---

## `account_export_service.py`

Exports included accounts.

The Account Management **Include** flag controls which accounts participate in exports.

The service produces CSV output with stable headers and UTF-8 handling.

---

## `ui_settings_service.py`

Persists GUI preferences outside the database.

Windows location:

```text
%APPDATA%\FinancialModel\ui_settings.json
```

Important behavior:

- Each screen may have its own service instance.
- Reads reload the JSON first.
- Writes reload the JSON first.
- Updates are atomic.
- Date settings are stripped.
- Settings errors do not stop the application.

The database is for financial/application data; this JSON file is for GUI preferences.

---

# 6. Database Layer

Location:

```text
src/database.py
src/database_init.py
```

`database.py` owns:

- SQLAlchemy engine.
- Session creation.

`database_init.py` imports all models and creates missing tables.

Database file:

```text
database/financial_model.db
```

---

# 7. Database Models

Location:

```text
src/models/
```

Models:

```text
Brokerage
Account
Company
ImportRecord
HoldingSnapshot
CashSnapshot
PortfolioSnapshot
```

Base:

```text
src/models/base.py
```

---

# 8. Event Flow

A typical import/update flow is:

```text
Import screen
     |
     v
BulkImportService
     |
     v
BMOImporter / NesbittImporter
     |
     v
ImportService
     |
     v
SQLite
```

A portfolio update is:

```text
Portfolio screen
     |
     v
PortfolioValuationService
     |
     +--> PortfolioService
     |
     +--> MarketPriceService
     |
     v
PortfolioSnapshot
     |
     v
<<PortfolioUpdated>>
     |
     +--> Account Management refresh
     +--> Holdings History refresh
     +--> other interested screens
```

The event is a GUI refresh signal, not a database event.

---

# 9. Financial Calculation Rules

Use:

```text
Decimal
```

for quantities and money.

Do not replace financial calculations with binary floating point.

For USD positions:

```text
USD value × USD/CAD
```

For CAD positions:

```text
CAD value
```

For options:

```text
quantity × price × 100
```

Current live valuation uses Yahoo data where available.

If Yahoo cannot value a security, the application can fall back to brokerage-imported values.

---

# 10. Historical Data Principle

There are two distinct classes of data.

## Imported facts

Examples:

- Imported quantity.
- Imported price.
- Imported average cost.
- Imported market value.
- Imported cash.
- Imported daily change.

These belong to the historical brokerage snapshot.

## Calculated values

Examples:

- Current market value.
- Current price.
- Current daily change.
- Portfolio total.
- Consolidated portfolio total.

These are valuation results and are stored separately.

Never rewrite historical brokerage facts merely because current market prices changed.

---

# 11. Database Migrations

Migrations live in:

```text
alembic/versions/
```

The chain includes changes for:

- consolidated portfolio snapshots
- holding average cost/unrealized gain
- holding daily values
- account classification/include settings
- live Yahoo valuation fields
- one snapshot per account/day
- stored valuation data

Before future schema work, verify the real database's Alembic state.

The reviewed database reported:

```text
7c1d4e8a2b6f
```

while later migration files exist.

This discrepancy must be resolved carefully before relying on Alembic's current/upgrade state.

---

# 12. Architectural Rules for Future Changes

- Keep GUI thin.
- Put business logic in services.
- Keep spreadsheet parsing in importers.
- Keep persistence in models/services.
- Keep live market data isolated in MarketPriceService.
- Preserve historical facts.
- Use Decimal.
- Add tests for business rules.
- Do not create unnecessary generic abstractions.
- Do not remove working GUI functionality during refactoring.


# CURRENT DEPLOYMENT ARCHITECTURE — September 29, 2026

The web implementation now exists and has been developed through Sprint 4.9A. FastAPI/Jinja2 sits above the existing service layer. The Raspberry Pi is intended to become the single owner of the SQLite database.

The planned Pi deployment is:

```text
Browser / Windows client
        |
        | HTTP/HTTPS over LAN or WireGuard
        v
Raspberry Pi 5
        |
     FastAPI
        |
    Services
        |
   SQLAlchemy
        |
     SQLite
        |
    NVMe SSD
```

Sprint 4.8 deployment artifacts exist, but the Pi has not yet been deployed. Sprint 4.9A validates the Windows/WireGuard side without the Pi. The next practical step is 4.9B.

The latest full Windows test result reported by the user is **137 passed**.
