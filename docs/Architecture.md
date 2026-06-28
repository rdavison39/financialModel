# Davison Financial Model

# System Architecture

**Version:** 1.0

---

# Purpose

This document defines the software architecture of the Davison Financial Model.

It is the authoritative technical specification describing how the application is organized, how components interact, and the responsibilities of each subsystem.

This document should be updated whenever the architecture changes.

---

# Architectural Philosophy

The application follows several fundamental design principles.

## Separation of Concerns

Each component has one responsibility.

Examples:

* Importers import data.
* Repositories store and retrieve data.
* Services perform business calculations.
* Reporting creates reports.
* Models define persistent entities.
* DTOs move data between components.

Responsibilities should never overlap.

---

## Store Facts — Calculate Everything Else

The database stores facts only.

Facts include:

* Accounts
* Companies
* Portfolio snapshots
* Historical market prices
* Import history

Derived information is never permanently stored.

Examples:

* Portfolio value
* Unrealized gains
* Asset allocation
* Dividend forecasts
* Retirement projections

These values are always calculated.

---

## Immutable History

Historical information is never overwritten.

Every brokerage import becomes a permanent portfolio snapshot.

Historical market prices are retained indefinitely.

This allows historical analysis without data loss.

---

## Modular Design

Every major feature exists as an independent subsystem.

Subsystems communicate through well-defined interfaces.

---

# High-Level Architecture

```text
                     +-----------------------+
                     |   BMO InvestorLine    |
                     |   Excel Exports       |
                     +-----------+-----------+
                                 |
                                 |
                                 v
                    +-------------------------+
                    |      Import Layer       |
                    +-----------+-------------+
                                |
                                v
                     ImportedAccount DTO
                     ImportedPosition DTO
                                |
                                v
                    +-------------------------+
                    |     Validation Layer    |
                    +-----------+-------------+
                                |
                                v
                    +-------------------------+
                    |     Import Service      |
                    +-----------+-------------+
                                |
                                v
                    +-------------------------+
                    |      Database Layer     |
                    +-----------+-------------+
                                |
                                v
                    +-------------------------+
                    |    Business Services    |
                    +-----------+-------------+
                                |
                +---------------+----------------+
                |               |                |
                v               v                v
        Portfolio         Retirement         Tax Engine
          Engine             Engine
                |
                +------------------------------+
                                               |
                                               v
                                      Estate Engine
                                               |
                                               v
                                        Reporting Layer
                                               |
                                               v
                                         Excel Reports
```

---

# Layered Architecture

The application consists of six logical layers.

## 1. Import Layer

Responsibilities:

* Read brokerage exports.
* Convert raw Excel data into DTOs.
* Perform basic validation.

Contains:

* BMO InvestorLine Importer
* Future brokerage importers

The import layer never communicates directly with the database.

---

## 2. Validation Layer

Responsibilities:

* Verify required columns.
* Detect duplicate records.
* Validate numeric values.
* Validate currencies.
* Produce validation reports.

Validation occurs before any database updates.

---

## 3. Persistence Layer

Responsibilities:

* Store and retrieve data.

Contains:

* SQLAlchemy models
* Repository classes
* Database services

Business logic does not exist in this layer.

---

## 4. Business Services

Responsibilities:

Perform financial calculations.

Examples:

* Portfolio valuation
* Asset allocation
* Dividend forecasting
* Currency exposure
* Retirement modelling
* Tax calculations
* Estate modelling

Business services should never contain SQL statements.

---

## 5. Reporting Layer

Responsibilities:

Generate output.

Examples:

* Excel reports
* Portfolio summaries
* Retirement reports
* Tax reports
* Estate reports

Reporting never modifies the database.

---

## 6. User Interface

Initially:

Command-line interface.

Future:

Desktop application.

Potential future:

Web dashboard.

---

# Project Directory Structure

```text
FinancialModel/

│
├── data/
│   ├── raw/
│   ├── processed/
│   └── cache/
│
├── database/
│
├── docs/
│
├── logs/
│
├── reports/
│
├── tests/
│
└── src/
    │
    ├── config/
    │
    ├── database/
    │
    ├── dto/
    │
    ├── importers/
    │
    ├── market/
    │
    ├── models/
    │
    ├── repositories/
    │
    ├── services/
    │
    ├── reporting/
    │
    └── utils/
```

---

# DTO Layer

DTOs (Data Transfer Objects) are temporary objects used to move data between layers.

Examples:

* ImportedAccount
* ImportedPosition

DTOs:

* do not know about SQLAlchemy
* do not know about SQLite
* contain no business logic

---

# Models

Models represent persistent entities.

Examples:

* Account
* Company
* PortfolioSnapshot
* Import
* MarketPrice

Models map directly to database tables.

---

# Repositories

Repositories provide all database access.

Examples:

* AccountRepository
* CompanyRepository
* PortfolioSnapshotRepository
* MarketPriceRepository

Repositories hide SQLAlchemy from the rest of the application.

---

# Services

Services contain business logic.

Examples:

PortfolioService

Responsibilities:

* Portfolio value
* Asset allocation
* Sector allocation
* Dividend calculations

RetirementService

Responsibilities:

* Withdrawal modelling
* CPP optimisation
* OAS optimisation
* Cash-flow projections

TaxService

Responsibilities:

* Tax estimates
* Capital gains
* Dividend tax credits

EstateService

Responsibilities:

* Estate valuation
* Beneficiary modelling
* Inheritance projections

---

# Logging

Every subsystem logs important events.

Examples:

* Imports
* Validation errors
* Database updates
* Report generation

Logging is centralized.

---

# Error Handling

Errors are never silently ignored.

Recoverable errors produce warnings.

Critical errors abort the current operation.

---

# Design Rules

The following rules apply throughout the project.

* One class per file.
* One responsibility per class.
* Complete type hints.
* Complete docstrings.
* No duplicated code.
* No magic numbers.
* No hard-coded paths.
* No global mutable state.
* Every feature must be testable.
* Every public class must have unit tests.

---

# Technology Stack

Language:

Python 3.13

Database:

SQLite

ORM:

SQLAlchemy

Schema Management:

Alembic

Excel:

openpyxl

Testing:

pytest

Formatting:

ruff

Version Control:

Git

---

# Architectural Goals

The architecture should remain stable as the application grows.

New features should be added by introducing new services rather than modifying existing ones.

Major architectural changes should be rare and documented in `DECISIONS.md`.

The application should remain understandable by a new developer after reading only the project documentation.
