# Davison Financial Model — Project State

**Reviewed:** September 20, 2026  
**Project version in `pyproject.toml`:** 0.1.0  
**Python requirement:** >= 3.13

This file is the current-state handoff document.

The previous Project State document was substantially outdated and should not be used as the source of truth.

---

# 1. Overall Status

The application is a working desktop financial-model application with:

- BMO import.
- Nesbitt Burns import.
- Historical account/holding/cash snapshots.
- Current market valuation.
- Historical portfolio valuation.
- Account history.
- Holdings history.
- Account management.
- Account exports.
- Persistent GUI preferences.
- SQLite persistence.
- Alembic migration infrastructure.
- Automated tests.

The GUI is currently organized into six screens.

---

# 2. Current Navigation

```text
Portfolio
Portfolio History
Account Management
Account History
Holdings History
Import
```

Startup screen:

```text
Portfolio
```

Main entry point:

```text
src.gui.app
```

---

# 3. Current Source Tree

```text
src/
├── config/
│   └── yahoo_symbol_map.py
│
├── gui/
│   ├── account_comparison_tab.py
│   ├── account_holdings_window.py
│   ├── accounts_tab.py
│   ├── app.py
│   ├── comparison_tab.py
│   ├── graphs_tab.py
│   ├── import_tab.py
│   ├── portfolio_tab.py
│   └── treeview_sort.py
│
├── importers/
│   ├── bmo_importer.py
│   └── nesbitt_importer.py
│
├── models/
│   ├── account.py
│   ├── base.py
│   ├── brokerage.py
│   ├── cash_snapshot.py
│   ├── company.py
│   ├── holding_snapshot.py
│   ├── import_record.py
│   └── portfolio_snapshot.py
│
├── services/
│   ├── account_comparison_history_service.py
│   ├── account_export_service.py
│   ├── account_service.py
│   ├── bulk_import_service.py
│   ├── import_service.py
│   ├── market_price_service.py
│   ├── portfolio_comparison_service.py
│   ├── portfolio_history_service.py
│   ├── portfolio_service.py
│   ├── portfolio_valuation_service.py
│   └── ui_settings_service.py
│
├── database.py
├── database_init.py
└── __init__.py
```

---

# 4. Current Tests

Test files currently include:

```text
test_account_comparison_history_service.py
test_account_export_service.py
test_bmo_importer.py
test_bulk_import_service.py
test_daily_change_calculation.py
test_import_reimport_rules.py
test_import_service.py
test_market_price_service.py
test_models.py
test_nesbitt_importer.py
test_portfolio_history_service.py
test_portfolio_update_async.py
test_sprint_301.py
test_sprint_31_account_settings.py
test_treeview_sort.py
```

The reviewed project collected 65 test functions before test collection was blocked by a missing `yfinance` package in the temporary review environment.

The normal project `.venv` should be used for authoritative test results.

---

# 5. Current Database

Database:

```text
database/financial_model.db
```

At review time:

```text
22 accounts
2 brokerages
313 companies
25 import records
41 cash snapshots
457 holding snapshots
69 portfolio snapshots
```

---

# 6. Current Database Migration State

Database reports:

```text
alembic_version = 7c1d4e8a2b6f
```

Repository contains later migrations.

This must be treated as a known technical issue.

Do not assume:

```text
alembic_version == latest migration
```

Do not run a destructive migration without first backing up the database and inspecting the actual schema.

---

# 7. Current GUI Settings

Settings file:

```text
%APPDATA%\FinancialModel\ui_settings.json
```

Settings currently used by screens include concepts such as:

- selected accounts
- view
- period
- benchmark
- custom benchmark
- import directories
- force re-import
- selected Account Management account

Dates are intentionally transient and are stripped from persisted settings.

---

# 8. Current Account-Selection Design

There are three different concepts that must not be confused.

## Account Management Include flag

Database field:

```text
Account.include_in_portfolio
```

This controls whether the account contributes to the consolidated portfolio.

## Portfolio History selection

Temporary analysis selection persisted in UI settings.

## Account History selection

Temporary analysis selection persisted in UI settings.

## Holdings History selection

Temporary analysis selection persisted in UI settings.

Stable account reference:

```text
Brokerage|AccountNumber|AccountName
```

---

# 9. Holdings History

File:

```text
src/gui/comparison_tab.py
```

Current purpose:

Compare selected holdings between From and To dates.

The screen shows:

- symbol
- company
- quantities
- quantity change
- average cost
- market value
- unrealized gain
- status

The account selector is dynamically rebuilt when accounts are loaded.

This is why the selection persistence code is more complicated than the other history screens.

The intended lifecycle is:

```text
load accounts
   |
read saved stable account keys
   |
create checkboxes
   |
user changes checkbox
   |
save immediately
   |
refresh/rebuild
   |
restore stable selection
```

---

# 10. Date Policy

The project requirement established during development is:

### Account Management / direct From-To screens

```text
To   = today
From = one year before today
```

### Named-period history screens

The date range is calculated from the selected period and today's date.

### Persistence

Dates must not be stored in `ui_settings.json`.

The settings service actively removes:

```text
start_date
end_date
from_date
to_date
```

from all saved screens.

---

# 11. Current Known Date Issue

The current `AccountsTab._account_selected()` implementation still loads the two most recent import snapshot dates when an account is selected.

That conflicts with the desired date policy above.

Future development should fix this so Account Management uses:

```text
From = today - 1 year
To   = today
```

and account selection does not replace those values with historical import dates.

This is intentionally recorded here because it is exactly the type of discrepancy that would otherwise be easy to rediscover after a long break.

---

# 12. Current Market Valuation

Current valuation is handled by:

```text
PortfolioValuationService
```

It uses:

```text
PortfolioService
MarketPriceService
```

and Yahoo Finance via `yfinance`.

Supported concepts include:

- CAD securities.
- USD securities.
- USD/CAD conversion.
- Current prices.
- Previous closes.
- Daily change.
- Daily change percentage.
- Options.
- Canadian preferred shares.
- Yahoo unavailable fallback behavior.

---

# 13. Current Import Rules

For each brokerage/account/calendar day, the database aims to have one authoritative snapshot.

Same-day rules include:

- duplicate timestamp is skipped.
- older same-day import is skipped.
- newer same-day import replaces the authoritative snapshot.
- different calendar day creates a new snapshot.
- force re-import can replace an existing snapshot.

This behavior is covered by tests.

---

# 14. Account Settings

Account types are managed by:

```text
AccountService.ACCOUNT_TYPES
```

A new account:

```text
include_in_portfolio = True
account_type = None
```

The Account Management screen allows the user to:

- classify the account.
- include/exclude it from portfolio calculations.
- rename it.

---

# 15. Account Export

Service:

```text
AccountExportService
```

Exports accounts marked:

```text
include_in_portfolio = True
```

The export includes account metadata and current holding/cash information.

---

# 16. External Inputs

Sample brokerage files currently present in the project include:

```text
data/uploads/Bmo-1.xlsx
data/uploads/Nesbit-1.xlsx
```

These are useful for testing/reproducing importer behavior.

Do not delete them until you're certain they are no longer needed as import fixtures/examples.

---

# 17. Development Entry Points

Start:

```text
python -m src.gui.app
```

Windows launcher:

```text
run_financical_model.bat
```

Tests:

```text
python -m pytest
```

---

# 18. Future Development Procedure

When starting a new development session:

### Step 1

Feed ChatGPT:

```text
docs/PROJECT_OVERVIEW.md
docs/PROJECT_STATE.md
docs/ARCHITECTURE.md
docs/DATA_MODEL.md
docs/README
```

### Step 2

Tell ChatGPT the requested change.

### Step 3

Have ChatGPT inspect the relevant source files before changing them.

### Step 4

Preserve existing functionality unless the change explicitly removes it.

### Step 5

Run relevant tests.

### Step 6

Run the full suite before considering a major sprint complete.

### Step 7

Update these documentation files whenever architecture, data model, screen structure, or important behavior changes.

---

# 19. Important Lessons From Previous Development

These are recorded to prevent repeated mistakes.

### Do not reconstruct the project from memory

The actual uploaded/current source should be inspected before making a change.

### Do not replace the entire project unnecessarily

For a small change, provide only the changed files unless a full replacement is specifically requested.

### Preserve GUI behavior

The account checkboxes, navigation, Include setting, sorting, exports, and existing screen behavior are all considered existing functionality.

### Do not persist dates

Dates should be calculated at runtime.

### Do not confuse UI selection with database inclusion

The history-screen checkboxes do not modify `Account.include_in_portfolio`.

### Do not change financial history during valuation

Imported brokerage facts are historical records.

---

# 20. Current Cleanup Status

The project contains some development/maintenance files that are not part of the runtime application:

```text
scripts/
Makefile
requirements-dev.txt
prune_financial_model.py
```

These can be removed if they are no longer needed.

The virtual environment:

```text
.venv/
```

is also disposable but should normally be retained while actively developing.

Do not delete:

```text
alembic/
tests/
database/
data/uploads/
src/
docs/
```

without a specific reason.

---

# 21. Documentation Authority

These documents describe the project as reviewed on September 20, 2026.

When the project changes:

- update the code first,
- update tests,
- then update these documents.

If documentation conflicts with the code, inspect the actual implementation rather than blindly following an old document.
