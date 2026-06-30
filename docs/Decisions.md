# Davison Financial Model

## Architectural Decisions

This document records important design decisions for the project.

## Decision 1: Store Facts, Calculate Derived Values

The database stores factual financial records only.

Stored facts include accounts, companies, imports, holding snapshots,
cash balance snapshots, and market prices.

Calculated values such as portfolio value, unrealized gain, allocation,
retirement projections, tax projections, and estate projections are
computed on demand.

Rationale:

* Prevent stale calculated data.
* Keep the database auditable.
* Preserve the ability to improve calculations later.

## Decision 2: Preserve Historical Imports

Every brokerage import creates new immutable snapshot records.

HoldingSnapshot and CashBalanceSnapshot records are not updated to
represent later imports. Later imports create later snapshots.

Rationale:

* Preserve historical accuracy.
* Support point-in-time portfolio views.
* Make import history auditable.

## Decision 3: Keep Importers Independent from Persistence

Importers read brokerage files and produce DTO objects.

Importers do not import SQLAlchemy, open sessions, call repositories, or
write to the database.

Rationale:

* Keep brokerage parsing testable.
* Allow the same importer output to be validated before persistence.
* Make future brokerages easier to add.

## Decision 4: Use Repositories for Database Access

Database access is performed through repository classes.

Services coordinate repositories through UnitOfWork rather than writing
SQLAlchemy queries directly.

Rationale:

* Keep persistence concerns isolated.
* Keep services focused on orchestration and business rules.
* Make transaction boundaries explicit.

## Decision 5: Use ImportService as the Persistence Bridge

ImportService consumes imported DTOs and persists them through the
UnitOfWork.

It is responsible for validation, transaction management, finding or
creating master data, and creating immutable snapshot records.

Rationale:

* Keeps importers simple.
* Keeps repositories free of business workflow.
* Provides one clear place for import rules.

## Decision 6: Use Decimal for Financial Values

Financial values use Decimal in Python and NUMERIC columns in the
database.

Floating point values are not used for money, shares, prices, yields, or
financial calculations.

Rationale:

* Avoid binary floating point rounding errors.
* Preserve financial precision.

## Decision 7: Start with BMO InvestorLine

BMO InvestorLine is the first supported brokerage import format.

The architecture should allow future importer classes for other
brokerages without changing the persistence model.

Rationale:

* Deliver value with one real brokerage first.
* Avoid premature generalization.
* Keep the importer contract stable.

## Decision 8: Use SQLite First

SQLite is the initial database engine.

Rationale:

* Simple local deployment.
* Appropriate for a private personal finance application.
* Compatible with SQLAlchemy and future migration paths.

## Decision 9: Use Tests as the Change Gate

New public behavior should have pytest coverage.

The test suite should remain green after each meaningful change.

Rationale:

* Protect financial correctness.
* Keep long-term maintenance safe.
* Make refactoring practical.
