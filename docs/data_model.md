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


# Davison Financial Model — Data Model

**Reviewed:** September 29, 2026

This document describes the persistent data model used by the Financial Model application.

---

# 1. Database

Database engine:

```text
SQLite
```

Database file:

```text
database/financial_model.db
```

ORM:

```text
SQLAlchemy 2.x
```

Base class:

```text
src/models/base.py
```

---

# 2. Entity Overview

The current database model contains seven application entities:

```text
Brokerage
    |
    +---- Account
             |
             +---- ImportRecord
             |
             +---- HoldingSnapshot ---- Company
             |
             +---- CashSnapshot
             |
             +---- PortfolioSnapshot
```

`PortfolioSnapshot.account_id` may be NULL for a consolidated portfolio snapshot.

---

# 3. Brokerage

Model:

```text
src/models/brokerage.py
```

Table:

```text
brokerages
```

Fields:

| Field | Type | Meaning |
|---|---|---|
| id | integer | Primary key |
| name | string | Brokerage name; unique |

Examples currently represented by the application:

- BMO
- Nesbitt Burns / NB

---

# 4. Account

Model:

```text
src/models/account.py
```

Table:

```text
accounts
```

Fields:

| Field | Type | Meaning |
|---|---|---|
| id | integer | Primary key |
| brokerage_id | FK | Parent brokerage |
| account_number | string | Brokerage account number |
| name | string | User-facing account name |
| account_type | string/null | Classification such as RRSP/TFSA/etc. |
| include_in_portfolio | boolean | Whether included in consolidated portfolio calculations |

Unique constraint:

```text
brokerage_id + account_number
```

This is the stable database identity of an account.

---

# 5. Company

Model:

```text
src/models/company.py
```

Table:

```text
companies
```

Fields:

| Field | Type | Meaning |
|---|---|---|
| id | integer | Primary key |
| symbol | string | Security symbol |
| name | string | Security/company name |

`symbol` is unique.

The Company table represents securities rather than only operating companies; options and other instruments may also be represented by symbols.

---

# 6. ImportRecord

Model:

```text
src/models/import_record.py
```

Table:

```text
import_records
```

Fields:

| Field | Type | Meaning |
|---|---|---|
| id | integer | Primary key |
| brokerage_id | FK | Source brokerage |
| account_id | FK | Source account |
| snapshot_date | datetime | Exact source timestamp |
| snapshot_day | date | Calendar day used for import uniqueness |
| file_name | string | Source Excel file |

Unique constraint:

```text
brokerage_id + account_id + snapshot_day
```

This enforces the application's rule of one authoritative import snapshot per brokerage/account/calendar day.

`ImportRecord.__init__()` derives `snapshot_day` from `snapshot_date` when necessary.

---

# 7. HoldingSnapshot

Model:

```text
src/models/holding_snapshot.py
```

Table:

```text
holding_snapshots
```

Fields:

| Field | Meaning |
|---|---|
| id | Primary key |
| account_id | Owning account |
| company_id | Security |
| snapshot_date | Brokerage snapshot timestamp |
| quantity | Imported quantity |
| price | Imported/security price |
| average_cost | Brokerage average cost |
| market_value | Imported market value |
| unrealized_gain | Imported unrealized gain |
| unrealized_gain_percent | Imported unrealized gain percentage |
| daily_change | Imported daily change |
| daily_change_percent | Imported daily change percentage |
| previous_close | Previous close |
| current_price | Current/live price when available |
| current_market_value | Current/live market value |
| current_previous_close | Current valuation previous close |
| current_daily_change | Current valuation daily change |
| current_daily_change_percent | Current valuation daily percentage change |
| currency | Security currency |

Financial numeric fields use SQLAlchemy `Numeric` types.

---

# 8. CashSnapshot

Model:

```text
src/models/cash_snapshot.py
```

Table:

```text
cash_snapshots
```

Fields:

| Field | Meaning |
|---|---|
| id | Primary key |
| account_id | Owning account |
| snapshot_date | Brokerage snapshot timestamp |
| currency | CAD/USD/etc. |
| amount | Cash amount |

Cash is historical brokerage data.

---

# 9. PortfolioSnapshot

Model:

```text
src/models/portfolio_snapshot.py
```

Table:

```text
portfolio_snapshots
```

Fields:

| Field | Meaning |
|---|---|
| id | Primary key |
| account_id | Account being valued; NULL for consolidated |
| snapshot_date | Valuation date |
| total_value | Calculated CAD portfolio value |
| daily_change | Calculated daily change |
| daily_change_percent | Calculated daily percentage change |
| tsx_daily_change_percent | TSX daily comparison |
| usd_to_cad | USD/CAD rate used |
| valuation_updated_at | Valuation timestamp |
| valuation_data | JSON text containing calculated valuation details |

A NULL `account_id` represents the consolidated portfolio.

This is deliberate and must not be confused with an account-level snapshot.

---

# 10. Imported Facts vs Calculated Values

This distinction is central to the application.

## Imported facts

Stored in:

```text
ImportRecord
HoldingSnapshot
CashSnapshot
```

These represent what the brokerage reported.

They should remain historically stable.

## Calculated valuation

Stored in:

```text
PortfolioSnapshot
```

and current valuation fields associated with holdings.

These depend on current market data and valuation logic.

---

# 11. Account Inclusion

`Account.include_in_portfolio` determines whether an account participates in consolidated portfolio calculations.

This setting is controlled from Account Management.

It is not the same as the temporary account-selection checkboxes in:

- Portfolio History
- Account History
- Holdings History

Those checkboxes are UI preferences stored in the separate JSON settings file.

---

# 12. Account Selection Persistence

History-screen checkbox selections are not database data.

They are UI preferences.

The stable UI account reference is:

```text
Brokerage|AccountNumber|AccountName
```

This allows selections to survive changes in database-generated integer IDs more safely than relying only on `Account.id`.

The current Holdings History implementation stores:

- selected account references
- selected account keys
- selected account IDs

as compatibility/fallback information.

---

# 13. Database Snapshot at Documentation Review

The uploaded database contained:

```text
brokerages             2
accounts              22
companies            313
import_records        25
cash_snapshots        41
holding_snapshots    457
portfolio_snapshots   69
```

Again, these are the contents of the reviewed database at that point in time.

---

# 14. Current Migration-State Warning

The database's `alembic_version` was:

```text
7c1d4e8a2b6f
```

The repository contains later migration files, including:

```text
77d48232bd35
9b3e1d2f
a3f7c2d1e8b4
4b7f3a2c91d1
```

The actual database schema already contains columns associated with later migrations.

Therefore, the migration history and actual schema are not perfectly synchronized.

Before future schema changes:

1. Back up `database/financial_model.db`.
2. Run `alembic current`.
3. Run `alembic heads`.
4. Inspect the actual schema.
5. Determine whether the existing database needs its Alembic revision corrected or migrations applied.
6. Do not blindly downgrade or upgrade.

---

# 15. Data Integrity Rules

Future changes must preserve:

- Brokerage/account uniqueness.
- Import snapshot-day uniqueness.
- Historical imported quantities.
- Historical cash.
- Historical security values.
- Decimal precision.
- Consolidated snapshots having NULL account IDs.
- Account inclusion semantics.

Do not solve a valuation problem by rewriting historical import records.

---

# 16. Typical Relationships

Conceptually:

```text
Brokerage
    1
    |
    +----< Account
              |
              +----< ImportRecord
              |
              +----< HoldingSnapshot >---- Company
              |
              +----< CashSnapshot
              |
              +----< PortfolioSnapshot
```

`PortfolioSnapshot` can also represent:

```text
AccountSnapshot
```

or:

```text
ConsolidatedPortfolioSnapshot
```

depending on whether `account_id` is populated.


# CURRENT STORAGE / DEPLOYMENT NOTE — September 29, 2026

SQLite remains the application database. No schema change is required for Pi deployment. The user plans to use the official Raspberry Pi M.2 HAT+ with a 2242 NVMe SSD. The intended long-term Pi installation places the OS, application, database, and backups on NVMe.

The database must remain local to the Pi. Do not place the SQLite database on a network share.

The latest full Windows test result reported by the user is **137 passed**.
