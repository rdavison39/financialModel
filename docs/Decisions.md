# Davison Financial Model

# DATABASE_SCHEMA.md

**Version:** 1.0

---

# Purpose

This document defines the physical database schema for the Davison Financial Model.

It is the authoritative specification for:

* Database tables
* Columns
* Data types
* Primary keys
* Foreign keys
* Relationships
* Indexes
* Constraints

SQLAlchemy models shall implement this schema.

---

# Database Philosophy

The database stores facts.

It does **not** store calculations.

Examples of stored values:

* Shares
* Average Cost
* Book Cost
* Historical Market Price
* Historical Dividend

Examples of calculated values:

* Portfolio Value
* Asset Allocation
* Unrealized Gain
* Retirement Projection
* Estate Value

---

# Database Engine

SQLite

ORM

SQLAlchemy 2.x

Schema Management

Alembic

---

# Table Overview

```text
Brokerages

Accounts

Companies

Imports

HoldingSnapshots

MarketPrices
```

Future tables

```text
Transactions

Dividends

ExchangeRates

Trusts

Beneficiaries

Properties

Liabilities
```

---

# Table

## Brokerages

Stores supported brokerages.

Columns

| Column   | Type       | Description           |
| -------- | ---------- | --------------------- |
| id       | INTEGER PK | Primary Key           |
| name     | TEXT       | Brokerage Name        |
| importer | TEXT       | Python Importer Class |
| website  | TEXT       | Website               |
| active   | BOOLEAN    | Enabled               |

Indexes

* name (unique)

---

# Table

## Accounts

Represents investment accounts.

Columns

| Column         | Type       |
| -------------- | ---------- |
| id             | INTEGER PK |
| brokerage_id   | FK         |
| account_number | TEXT       |
| account_name   | TEXT       |
| owner          | TEXT       |
| account_type   | TEXT       |
| currency       | TEXT       |
| active         | BOOLEAN    |

Indexes

* account_number
* owner

Unique

(brokerage_id, account_number)

---

# Table

## Companies

Represents securities.

Columns

| Column       | Type       |
| ------------ | ---------- |
| id           | INTEGER PK |
| ticker       | TEXT       |
| company_name | TEXT       |
| exchange     | TEXT       |
| currency     | TEXT       |
| asset_class  | TEXT       |
| sector       | TEXT       |
| industry     | TEXT       |
| country      | TEXT       |
| active       | BOOLEAN    |

Indexes

* ticker
* sector
* asset_class

Unique

ticker

---

# Table

## Imports

Represents one brokerage import.

Columns

| Column            | Type       |
| ----------------- | ---------- |
| id                | INTEGER PK |
| brokerage_id      | FK         |
| import_timestamp  | DATETIME   |
| source_folder     | TEXT       |
| file_count        | INTEGER    |
| account_count     | INTEGER    |
| holding_count     | INTEGER    |
| validation_status | TEXT       |
| notes             | TEXT       |

Indexes

* import_timestamp

---

# Table

## HoldingSnapshots

Represents one holding imported during one Import.

Every brokerage import creates new HoldingSnapshot records.

Existing records are never modified.

Columns

| Column                   | Type          |
| ------------------------ | ------------- |
| id                       | INTEGER PK    |
| import_id                | FK            |
| account_id               | FK            |
| company_id               | FK            |
| shares                   | NUMERIC(20,6) |
| average_cost             | NUMERIC(20,6) |
| total_cost               | NUMERIC(20,2) |
| imported_price           | NUMERIC(20,6) |
| imported_market_value    | NUMERIC(20,2) |
| imported_unrealized_gain | NUMERIC(20,2) |
| imported_dividend        | NUMERIC(20,6) |
| imported_yield           | NUMERIC(10,6) |

Indexes

* account_id
* company_id
* import_id

Composite Index

(import_id, account_id)

---

# Table

## MarketPrices

Historical market prices.

Columns

| Column     | Type          |
| ---------- | ------------- |
| id         | INTEGER PK    |
| company_id | FK            |
| price_date | DATE          |
| open       | NUMERIC(20,6) |
| high       | NUMERIC(20,6) |
| low        | NUMERIC(20,6) |
| close      | NUMERIC(20,6) |
| volume     | INTEGER       |
| dividend   | NUMERIC(20,6) |

Indexes

(company_id, price_date)

Unique

(company_id, price_date)

---

# Relationships

```text
Brokerage

    │

    └────────────── Accounts

                         │

                         ▼

HoldingSnapshots

     ▲

     │

Imports

     │

     ▼

Companies

     │

     ▼

MarketPrices
```

---

# Referential Integrity

Deleting Brokerages

Not allowed.

Deleting Accounts

Not allowed if HoldingSnapshots exist.

Deleting Companies

Not allowed if HoldingSnapshots exist.

Deleting Imports

Never permitted.

HoldingSnapshots are immutable.

---

# Audit Strategy

Every import creates new HoldingSnapshot records.

Historical data is preserved forever.

No UPDATE statements should normally occur against HoldingSnapshots.

Historical accuracy takes precedence over storage requirements.

---

# Index Strategy

Indexes should optimize

* Company lookups
* Account lookups
* Import history
* Historical price lookups
* Portfolio calculations

Premature optimization should be avoided.

Indexes should be added only when justified by profiling.

---

# Numeric Precision

Financial values must never use floating point types.

Money

NUMERIC(20,2)

Prices

NUMERIC(20,6)

Shares

NUMERIC(20,6)

Dividend Yield

NUMERIC(10,6)

Python shall use

Decimal

for all financial calculations.

---

# Future Tables

Version 2+

Transactions

Trade history.

Dividends

Actual dividend payments.

ExchangeRates

Daily FX rates.

Version 3+

Properties

Florida home.

Ontario home.

Cottage.

Version 4+

Liabilities

Loans

Mortgages

Credit Lines

Version 5+

Estate

Beneficiaries

Trusts

Executors

Power of Attorney

Estate Scenarios

---

# Migration Strategy

Database schema changes shall be managed exclusively through Alembic.

Manual database modifications are prohibited.

Every schema change must include

* Alembic migration
* Updated SQLAlchemy models
* Updated documentation

---

# Design Rules

1. Facts only.
2. Historical data is immutable.
3. Every import is permanent.
4. Every holding belongs to one import.
5. Every company exists once.
6. Every account exists once.
7. Money uses Decimal.
8. SQLAlchemy models mirror this schema exactly.
9. Business logic never exists in SQLAlchemy models.
10. Database changes require documentation updates.
