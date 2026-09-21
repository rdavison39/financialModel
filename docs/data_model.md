# Davison Financial Model — Data Model

**Reviewed:** September 20, 2026

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
