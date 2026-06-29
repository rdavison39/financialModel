# Financial Model Project

**Project Status:** Phase 2 Beginning
**Last Updated:** June 28, 2026

---

# Project Vision

Build a production-quality personal investment portfolio management application.

The application imports brokerage statements (beginning with BMO InvestorLine), stores historical portfolio snapshots, and later will provide reporting, performance analysis, dividend tracking, tax reporting, and portfolio analytics.

The design emphasizes:

* clean architecture
* separation of concerns
* comprehensive automated testing
* maintainability
* production-quality code

---

# Technology Stack

* Python 3.13
* SQLAlchemy ORM
* SQLite
* openpyxl
* pytest

---

# Development Rules

These rules apply throughout the project.

1. Always provide COMPLETE files unless a smaller edit is clearly better.
2. Work on only one file at a time.
3. Never remove functionality without discussing it first.
4. Keep business logic out of repositories.
5. Keep importers independent of SQLAlchemy.
6. Every feature should include unit tests.
7. Maintain consistent formatting, type hints and docstrings.
8. Prioritize clean architecture over shortcuts.

---

# Current Status

## Test Status

```
107 tests passed
0 failures
0 warnings
```

Python 3.13 deprecation warnings have been eliminated.

---

# Completed Components

## Database Models

Completed

* Brokerage
* Account
* Company
* Import
* HoldingSnapshot
* CashBalanceSnapshot
* MarketPrice

---

## Repository Layer

Completed

* BrokerageRepository
* AccountRepository
* CompanyRepository
* ImportRepository
* HoldingSnapshotRepository
* CashBalanceSnapshotRepository
* MarketPriceRepository

Repositories contain only persistence logic.

---

## Test Infrastructure

Completed

* in-memory SQLite testing
* entity factory
* importer fixtures
* repository fixtures

All tests passing.

---

## Import Infrastructure

Completed

### ExcelReader

Responsible for opening workbooks.

---

### WorksheetHelper

Provides generic worksheet utilities.

Responsibilities

* cell access
* row helpers
* text searching
* worksheet navigation

Contains no brokerage-specific logic.

---

### BMOLayout

Discovers worksheet structure.

Finds

* account information
* statement date
* cash section
* holdings section
* all required columns

The importer never searches worksheets directly.

---

### BMO InvestorLine Importer

Completed.

Produces DTO objects only.

Contains no SQLAlchemy or database code.

---

## DTOs

Completed

* ImportedAccount
* ImportedCash
* ImportedPosition

These form the contract between importers and the application layer.

---

# Current Architecture

```
Excel Workbook
        │
        ▼
ExcelReader
        │
        ▼
WorksheetHelper
        │
        ▼
BMOLayout
        │
        ▼
BMOInvestorLineImporter
        │
        ▼
ImportedAccount
        │
        ▼
ImportService
        │
        ▼
Repositories
        │
        ▼
SQLite Database
```

---

# Architectural Principles

Importers know nothing about SQLAlchemy.

Repositories know nothing about Excel.

Business rules belong in services.

DTOs isolate the importer layer from the persistence layer.

Repositories should never contain business logic.

---

# Immediate Next Task

Implement:

```
src/services/import_service.py
```

Responsibilities

* accept ImportedAccount
* validate imported data
* create Import record
* find or create Brokerage
* find or create Account
* find or create Company
* create HoldingSnapshot records
* create CashBalanceSnapshot records
* commit transaction
* rollback on failure

---

# Planned Near-Term Work

## Phase 2

Service Layer

* ImportService
* ImportResult
* Import validation
* transaction management

---

## Phase 3

Folder Import

Import every workbook in a folder.

Support multiple accounts.

Support multiple brokerages.

---

## Phase 4

Reporting

Portfolio reports

Historical portfolio views

Performance calculations

Asset allocation

Dividend reports

---

## Phase 5

Market Data

Download market prices

Update Company records

Calculate portfolio value

Performance metrics

---

## Phase 6

Analytics

Portfolio growth

Returns

Income tracking

Sector allocation

Country allocation

Asset allocation

---

## Phase 7

User Interface

CLI

Desktop UI (TBD)

Web UI (possible future)

---

# Future Brokerages

Planned

* BMO InvestorLine
* RBC Direct Investing
* TD Direct Investing
* Questrade
* Wealthsimple

Each brokerage should implement the same importer interface.

---

# Git Milestones

Recommended tags

```
v0.1
Database Layer Complete

v0.2
Importer Infrastructure Complete

v0.3
ImportService Complete

v0.4
Folder Import Complete

v0.5
Reporting Complete

v1.0
Production Release
```

---

# Notes

The project currently has a solid, fully tested foundation.

Future work should continue to emphasize:

* test-driven development
* clean separation of concerns
* production-quality code
* maintainability
* extensibility

Avoid introducing shortcuts that compromise the architecture.
