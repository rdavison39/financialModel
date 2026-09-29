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


# Davison Financial Model — Project State

**Reviewed:** September 29, 2026  
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


# 22. AUTHORITATIVE CURRENT STATE — September 29, 2026

This section supersedes older test-count and Sprint 4 status statements in this historical document.

## Test baseline

Latest full Windows result reported by the user:

```text
137 passed
```

## Sprint 4

```text
4.1  COMPLETE
4.2  COMPLETE
4.3  COMPLETE
4.4  COMPLETE
4.5  COMPLETE
4.6  COMPLETE
4.7  COMPLETE
4.8  PREPARED; Pi not yet deployed
4.9A COMPLETE; Windows/WireGuard validation
4.9B NEXT; actual Pi + WireGuard end-to-end testing
```

## Deployment artifacts

```text
Sprint_4.8_Raspberry_Pi_Deployment.zip
Sprint_4.9A_Windows_WireGuard_Validation.zip
```

## Pi storage decision

The planned Pi storage is:

```text
Raspberry Pi 5
  -> official Raspberry Pi M.2 HAT+
  -> 2242 NVMe SSD
```

The intended installation places Raspberry Pi OS, the Financial Model, SQLite, and backups on the NVMe.

## Next action

Do not invent another development sprint before completing the Pi deployment. When the Pi is available, inspect the actual project, install the NVMe, copy the tested project/database, run `deploy/install_pi.sh`, verify the systemd service and `/api/health`, test the web application over LAN, then configure and test WireGuard.

Do not expose FastAPI port 8000 directly to the public Internet. Do not blindly run Alembic migrations. Do not put SQLite on a network share.
