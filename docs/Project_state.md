# Davison Financial Model

# PROJECT_STATE.md

**Version:** 0.2.0 (End of Phase 1)

**Last Updated:** June 28, 2026

---

# Current Status

## Current Phase

**Phase 2**

## Current Milestone

Implement the **ImportService**.

The importer infrastructure is complete and fully tested.

The next objective is to persist imported brokerage data into the database while maintaining the project's layered architecture.

---

# Build Status

## Python

3.13

## Test Status

```
107 tests passed
0 failures
0 warnings
```

The project builds cleanly.

---

# Completed Components

## Database Layer

Completed.

Models:

* Brokerage
* Account
* Company
* Import
* HoldingSnapshot
* CashBalanceSnapshot
* MarketPrice

---

## Repository Layer

Completed.

Repositories:

* BrokerageRepository
* AccountRepository
* CompanyRepository
* ImportRepository
* HoldingSnapshotRepository
* CashBalanceSnapshotRepository
* MarketPriceRepository

Repository responsibilities are limited to persistence.

Business logic is intentionally excluded.

---

## Import Infrastructure

Completed.

Components:

* ExcelReader
* WorksheetHelper
* BMOLayout
* BMOInvestorLineImporter

The importer successfully reads a BMO InvestorLine holdings export and produces DTO objects.

The importer has no dependency on SQLAlchemy or the database.

---

## DTO Layer

Completed.

DTOs:

* ImportedAccount
* ImportedCash
* ImportedPosition

DTOs provide the contract between the importer layer and the service layer.

---

## Test Infrastructure

Completed.

Current testing includes:

* Repository tests
* Importer tests
* Model tests
* DTO tests
* Helper class tests

All tests are currently passing.

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

ImportedAccount DTO

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

# Current Architectural Principles

The following architectural rules are now considered established.

* Importers never communicate directly with SQLAlchemy.
* Importers return DTO objects only.
* DTOs are independent of persistence.
* Repositories encapsulate all database access.
* Business logic belongs in services.
* SQLAlchemy models contain no business logic.
* Historical data is immutable.
* The database stores facts only.
* Calculated values are never persisted.

---

# Current Development Rules

The following development rules apply throughout the project.

1. Always provide complete files unless a smaller edit is clearly preferable.
2. Work on one file at a time.
3. Never remove existing functionality without discussion.
4. Maintain production-quality code.
5. Use complete type hints.
6. Use complete docstrings.
7. Every feature should include unit tests.
8. Keep responsibilities clearly separated.
9. Prefer readability over cleverness.
10. Keep the test suite green after every change.

---

# Immediate Next Task

Implement:

```
src/services/import_service.py
```

Responsibilities:

* Accept ImportedAccount DTOs.
* Validate imported data.
* Create an Import record.
* Find or create Brokerage.
* Find or create Account.
* Find or create Company.
* Create HoldingSnapshot records.
* Create CashBalanceSnapshot records.
* Commit the transaction.
* Roll back the transaction on failure.

The ImportService becomes the bridge between the importer layer and the persistence layer.

---

# Upcoming Work

## Phase 2

ImportService

* ImportService
* ImportResult
* Transaction management
* Validation
* Persistence

---

## Phase 3

Folder Import

* Import every workbook within a folder.
* Support multiple accounts.
* Support multiple brokerage files.

---

## Phase 4

Portfolio Services

* Portfolio calculations
* Asset allocation
* Historical portfolio views
* Performance calculations

---

## Phase 5

Market Data

* Market price downloads
* Company updates
* Historical pricing
* Dividend history

---

## Phase 6

Planning Engines

* Retirement planning
* Tax planning
* Estate planning
* Trust planning

---

## Phase 7

Reporting

* Portfolio reports
* Retirement reports
* Tax reports
* Estate reports

---

# Session Summary

Completed during this development session:

* Added CashBalanceSnapshot support.
* Completed repository implementation.
* Completed importer infrastructure.
* Improved WorksheetHelper.
* Updated ExcelReader to return WorksheetHelper objects.
* Reorganized pytest fixtures.
* Eliminated Python 3.13 deprecation warnings.
* Restored a clean test suite.
* Achieved:

```
107 tests passed
0 failures
0 warnings
```

This represents the completion of the project's foundation.

The next development session will begin implementing the ImportService.
