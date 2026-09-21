# Davison Financial Model

## Project Overview and Development Handoff

**Reviewed:** September 20, 2026  
**Project:** Private personal financial/portfolio management application  
**Language:** Python 3.13+  
**GUI:** Tkinter / ttk  
**ORM:** SQLAlchemy 2.x  
**Database:** SQLite  
**Market data:** Yahoo Finance through `yfinance`  
**Spreadsheet input:** Excel files through `openpyxl`

This document is intended to be a durable handoff document. If development resumes after a long break, feed this document together with the other files in `docs/` to ChatGPT before making changes.

---

# 1. Purpose

The Financial Model is a desktop application for maintaining historical investment-account information and calculating current and historical portfolio values.

The application is designed around a simple principle:

> Brokerage imports are historical facts. Portfolio valuation is calculated separately and must not rewrite those imported facts.

The application currently imports brokerage Excel exports from:

- BMO InvestorLine
- Nesbitt Burns

It stores account, holding, cash, import, company/security, and calculated portfolio history in SQLite.

---

# 2. Current Application Screens

The main application is `src/gui/app.py`.

The navigation order is:

1. **Portfolio**
2. **Portfolio History**
3. **Account Management**
4. **Account History**
5. **Holdings History**
6. **Import**

The application starts on **Portfolio**.

## Portfolio

Implemented by:

`src/gui/portfolio_tab.py`

Purpose:

- Show consolidated current portfolio value.
- Show daily change.
- Show TSX daily change.
- Show last update time.
- Show brokerage-level current values.
- Run the portfolio valuation/update process.
- Retrieve current market prices and USD/CAD conversion.
- Save calculated portfolio snapshots.

The portfolio update runs its valuation work in a background worker so that the GUI remains responsive.

After a successful portfolio update it generates the Tk event:

`<<PortfolioUpdated>>`

Other screens use this event to refresh their displayed data.

---

## Portfolio History

Implemented by:

`src/gui/graphs_tab.py`

Purpose:

- Display historical consolidated portfolio values.
- Select which accounts contribute to the history.
- Select a view:
  - Dollar Value
  - Gain/Loss
  - % Growth
  - Daily Change
- Select a period:
  - 1 Month
  - 3 Months
  - 6 Months
  - YTD
  - 1 Year
  - 3 Years
  - 5 Years
  - All Time
  - Custom
- Select a benchmark:
  - None
  - S&P 500
  - TSX Composite
  - Custom
- Specify custom start/end dates.
- Refresh the history.

Account checkbox selections and non-date view settings are persisted outside the database.

Dates are intended to be transient: they should be recalculated rather than persisted between application launches.

---

## Account Management

Implemented by:

`src/gui/accounts_tab.py`

Purpose:

- Display all investment accounts.
- Show brokerage.
- Show account number.
- Show account name.
- Show account type.
- Control whether the account is included in the portfolio.
- Show current value.
- Show gain/loss.
- Show ROI.
- Show cash.
- Show holdings count.
- Show last import.
- Show today's change.
- Rename accounts.
- View account holdings.
- Export included accounts.
- Compare snapshots for a selected account.

Account classification currently supports the values defined by `AccountService.ACCOUNT_TYPES`, plus an unclassified state.

The **Include** setting is important: it determines whether the account participates in consolidated portfolio calculations/export behavior.

The screen title is **Account Management**.

### Important current-state note

The current source contains older account-snapshot-date behavior in `_account_selected()`: selecting an account can populate the From/To fields from that account's latest import snapshots.

The intended UI rule established during development is different:

- **To = today**
- **From = one year before today**
- These dates should not be persisted.

If this behavior is still present when development resumes, treat it as a known item to correct rather than reintroducing persisted dates.

---

## Account History

Implemented by:

`src/gui/account_comparison_tab.py`

Purpose:

- Select one or more accounts.
- Display historical account values.
- Compare account histories over a selected period.
- Select the same general views/period/benchmark concepts used by Portfolio History.
- Show latest account values.

Account selections and non-date display settings are persisted outside the database.

---

## Holdings History

Implemented by:

`src/gui/comparison_tab.py`

Purpose:

- Select accounts using checkboxes.
- Compare holdings between two dates.
- Show:
  - Symbol
  - Company
  - Quantity at From date
  - Quantity at To date
  - Quantity change
  - Average cost
  - Market value
  - Unrealized gain
  - Status
- Show consolidated From/To portfolio values and change.

The screen is also called the Holdings History screen in the UI.

Account selections are intended to persist across application restarts.

The stable account selection key is:

`Brokerage|AccountNumber|AccountName`

The implementation also stores account IDs as a fallback.

Dates are intentionally transient and should be recalculated rather than saved.

---

## Import

Implemented by:

`src/gui/import_tab.py`

Supports:

- BMO directory selection
- Nesbitt Burns directory selection
- Bulk import
- Force re-import of existing snapshots
- Display of import results

The selected import directories and force-reimport setting are persisted outside the database.

---

# 3. Normal Application Startup

The preferred command is:

```text
python -m src.gui.app
```

The supplied Windows launcher is:

```text
run_financical_model.bat
```

It activates the project's `.venv` and starts:

```text
python -m src.gui.app
```

The application expects to be run from the project root.

---

# 4. Persistent GUI Settings

GUI preferences are deliberately kept separate from the SQLite database.

Service:

```text
src/services/ui_settings_service.py
```

On Windows the default location is:

```text
%APPDATA%\FinancialModel\ui_settings.json
```

The service:

- Loads JSON settings.
- Reloads the file before reads/writes so separate screen instances do not overwrite each other.
- Writes atomically using a temporary file followed by `os.replace()`.
- Treats preferences as optional; a settings-file failure must not prevent the application from starting.
- Removes legacy date fields.

Dates that should never be persisted include:

- `start_date`
- `end_date`
- `from_date`
- `to_date`

The important design distinction is:

**Persist user preferences; calculate dates from today's date.**

---

# 5. Brokerage Import Workflow

The high-level flow is:

```text
BMO/Nesbitt Excel file
        |
        v
Brokerage importer
        |
        v
Imported account/holding/cash structures
        |
        v
ImportService
        |
        v
SQLAlchemy models
        |
        v
SQLite
```

For directories:

```text
BulkImportService
        |
        +--> BMOImporter
        |
        +--> NesbittImporter
        |
        v
ImportService
```

Duplicate/re-import rules are important:

- The exact source timestamp is retained.
- `snapshot_day` represents the calendar day.
- The application enforces one authoritative brokerage/account snapshot per calendar day.
- A newer same-day source can replace an older same-day snapshot.
- Duplicate imports are rejected/skipped according to the import rules.
- Force re-import can replace an existing snapshot.

Imported holdings and cash represent brokerage facts and should not be altered by portfolio valuation.

---

# 6. Portfolio Valuation Workflow

Current portfolio valuation uses:

```text
PortfolioService
       |
       v
latest imported holdings/cash
       |
       v
MarketPriceService
       |
       v
PortfolioValuationService
       |
       v
PortfolioSnapshot
```

Market data comes from Yahoo Finance through `yfinance`.

The valuation service handles:

- Current security prices.
- Previous closes.
- USD/CAD conversion.
- CAD and USD holdings.
- Current market value.
- Daily change.
- Daily change percentage.
- Options using a 100-share contract multiplier.
- Canadian preferred-share Yahoo symbol conversion.
- Fallback to brokerage-imported values when Yahoo data is unavailable.

Calculated values are stored separately from the imported brokerage snapshots.

---

# 7. Current Brokerage Support

## BMO

Importer:

```text
src/importers/bmo_importer.py
```

## Nesbitt Burns

Importer:

```text
src/importers/nesbitt_importer.py
```

The application currently recognizes Nesbitt Burns internally as `NB` in several account-selection/display contexts.

---

# 8. Current Project Structure

The important project structure is:

```text
financialModel/
│
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── data/
│   └── uploads/
│
├── database/
│   └── financial_model.db
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DATA_MODEL.md
│   ├── PROJECT_OVERVIEW.md
│   ├── PROJECT_STATE.md
│   └── README
│
├── src/
│   ├── config/
│   ├── gui/
│   ├── importers/
│   ├── models/
│   └── services/
│
├── tests/
│
├── alembic.ini
├── pyproject.toml
├── requirements.txt
├── financial_model_icon.ico
└── run_financical_model.bat
```

The project also contains local-development material such as `.venv`, Git metadata, and maintenance scripts. Those are not part of the application architecture.

---

# 9. Development Rules

When modifying this application:

1. Do not remove existing functionality unless explicitly requested.
2. Prefer small, targeted changes.
3. Keep imported brokerage facts immutable.
4. Keep calculated valuation data separate.
5. Use `Decimal` for financial calculations.
6. Use SQLAlchemy models/services rather than embedding database logic in GUI code.
7. Keep one major class per source file.
8. Preserve the existing GUI navigation and screen responsibilities.
9. Preserve account-selection functionality.
10. Do not persist transient dates in `ui_settings.json`.
11. Run the relevant tests after changes.
12. For larger changes, run the full test suite.
13. When changing database structure, add/update an Alembic migration rather than silently changing the database.
14. Do not delete old maintenance scripts or migrations merely because they are not imported by the GUI without first determining whether they are still needed for historical data maintenance.

---

# 10. Important Known State/Issues

The following items are deliberately recorded so future development does not repeat earlier investigation:

### GUI settings

The settings system is shared by all screens but each screen owns its own `UISettingsService` instance. The service reloads the JSON file before every read/write to avoid one tab overwriting settings written by another.

### Holdings History selections

Holdings History has required special handling because its account checkboxes are dynamically rebuilt when accounts are loaded/refreshed.

The intended behavior is:

```text
user changes checkbox
        |
        v
save immediately
        |
        v
screen/account list can be rebuilt
        |
        v
selection is restored from stable account keys
```

The stable key is:

```text
Brokerage|AccountNumber|AccountName
```

### Dates

Dates are transient.

Do not add date persistence back into `UISettingsService`.

### Account Management dates

The intended default is:

```text
To   = today
From = today - 1 year
```

Selecting an account should not replace these defaults with historical import dates unless that behavior is explicitly requested.

### Database migrations

The database contained in the reviewed project ZIP reported Alembic revision:

```text
7c1d4e8a2b6f
```

while migration files newer than that revision are present in the repository.

The database schema itself already contains several of the later columns.

This is an important inconsistency. Before performing future database migration work, inspect:

```text
alembic current
alembic heads
```

against the actual database before making assumptions about migration state.

Do not blindly run migrations against the production database without first backing it up.

---

# 11. Current Database Snapshot

The database included in the reviewed project ZIP contained:

```text
brokerages             2
accounts              22
companies            313
import_records        25
cash_snapshots        41
holding_snapshots    457
portfolio_snapshots   69
```

These are a snapshot of the uploaded project database, not a permanent specification. They will change as new imports and valuations are performed.

---

# 12. Testing

The repository currently contains **65 collected test cases/functions** before collection errors in the review environment.

Test areas include:

- Models
- BMO importer
- Nesbitt importer
- Import service
- Bulk import service
- Duplicate/re-import rules
- Market price service
- Portfolio valuation
- Daily change calculations
- Portfolio history
- Account history
- Account export
- Account settings
- Treeview sorting
- Portfolio update background worker

The test suite uses:

```text
pytest
```

with:

```text
tests/
```

as the configured test directory.

### Review environment note

A test run during this documentation update collected 65 tests but stopped during collection because the temporary environment used for the review did not have `yfinance` installed.

The project itself declares:

```text
yfinance>=1.4
```

in `pyproject.toml`.

Therefore, the documentation update does **not** claim that the current 65-test suite passes. Before relying on test results, run the suite in the project's normal `.venv`.

---

# 13. Dependencies

Declared project dependencies currently include:

```text
sqlalchemy>=2.0
openpyxl>=3.1
yfinance>=1.4
```

Python requirement:

```text
Python >= 3.13
```

Development configuration is in:

```text
pyproject.toml
```

Pytest is configured there as well.

---

# 14. How to Resume Development

When returning to this project after a long break:

1. Read all five files in `docs/`.
2. Inspect the actual project tree under `src/`.
3. Inspect `pyproject.toml`.
4. Inspect the current Alembic revision before database changes.
5. Run:

```text
python -m pytest
```

6. Confirm the application starts with:

```text
python -m src.gui.app
```

7. Do not assume the historical docs or sprint names are authoritative. These rewritten documents describe the implementation that was reviewed on September 20, 2026.
8. If code and documentation disagree, inspect the code and database first, then update the documentation after the intended behavior is confirmed.

---

# 15. Source of Truth

For future development, use this priority order:

1. Current source code
2. Current database schema/data
3. Alembic migration history
4. Tests
5. These documentation files

These documents are designed to preserve architectural intent and development history, but they must not override the actual current code.
