# Davison Financial Model

# AI_CONTEXT.md

**Purpose**

This document is the onboarding guide for any AI assistant working on the Davison Financial Model project.

Reading this document should provide enough context to immediately begin productive development.

The detailed project specification is contained in the remaining documentation within the `docs` directory.

---

# Project Overview

The Davison Financial Model is a professional-quality financial planning application written in Python.

The application is designed specifically for the Davison family.

It is intended to become the family's permanent financial management system.

The project combines:

* Portfolio Management
* Investment Analysis
* Dividend Forecasting
* Retirement Planning
* Tax Planning
* Estate Planning
* Trust Planning
* Financial Reporting

The application is expected to evolve over many years.

---

# Primary Objective

Create software that becomes the single source of truth for the family's financial information.

The application should answer questions that currently require:

* Brokerage websites
* Spreadsheets
* Retirement calculators
* Tax software
* Estate planning documents

---

# Current Development Status

Current Phase

Phase 2

Current Milestone

Implement the ImportService.

Current Status

The foundational architecture is complete.

Completed

• SQLAlchemy model layer
• Repository layer
• Import infrastructure
• DTO layer
• CashBalanceSnapshot support
• BMO InvestorLine importer
• Comprehensive automated test suite

Current Build Status

107 pytest tests

107 passing

0 failures

0 warnings

---

# Source of Truth

The project documentation is authoritative.

If documentation and implementation disagree:

**Documentation wins.**

---

# Required Reading

Before modifying code, review the following documents in order.

1. PROJECT_STATE.md
2. ARCHITECTURE.md
3. DATA_MODEL.md
4. DATABASE_SCHEMA.md
5. DECISIONS.md

Only consult other documentation as required.

---

# Project Philosophy

The application stores facts.

The application calculates everything else.

Historical information is never deleted.

Every brokerage import becomes a permanent historical snapshot.

Business logic belongs in services.

Importers import.

Repositories access databases.

Reports generate output.

Responsibilities should never overlap.

---

# Current Architecture

```text
BMO Excel

↓

Importer

↓

DTO Objects

↓

Validation

↓

Import Service

↓

SQLite Database

↓

Business Services

↓

Reporting
```

---

# Current Technology Stack

Language

Python 3.13

Database

SQLite

ORM

SQLAlchemy

Migrations

Alembic

Excel

openpyxl

Testing

pytest

Formatting

ruff

Version Control

Git

---

# Project Structure

```
FinancialModel/

docs/

src/

tests/

reports/

logs/

data/
```

The `docs` directory contains the project specification.

The `src` directory contains implementation.

The `tests` directory mirrors the `src` directory.

---

# Development Rules

These rules are mandatory.

1. Produce complete files.

Never produce snippets unless explicitly requested.

2. One class per file.

3. One responsibility per class.

4. Every public class has unit tests.

5. Use complete type hints.

6. Use complete docstrings.

7. Never use floating point numbers for financial calculations.

Always use Decimal.

8. Use SQLAlchemy for persistence.

9. Use Alembic for schema changes.

10. Historical data is immutable.

11. Business logic belongs in services.

12. SQLAlchemy models contain no business logic.

13. Importers never access the database.

14. Reports never modify the database.

15. No hard-coded paths.

16. No duplicated code.

17. Keep functions reasonably small and focused.

18. Every feature should compile before moving to the next feature.

---

# Current Naming Conventions

Examples

```
Account

Company

HoldingSnapshot

Import

MarketPrice
```

DTOs

```
ImportedAccount

ImportedPosition
```

Repositories

```
AccountRepository

CompanyRepository

HoldingSnapshotRepository
```

Services

```
PortfolioService

RetirementService

TaxService

EstateService
```

---

# Current Roadmap

Sprint 1

Import foundation

Sprint 2

Portfolio analytics

Sprint 3

Retirement engine

Sprint 4

Tax engine

Sprint 5

Estate engine

Sprint 6

Reporting

---

# Current Coding Workflow

Every feature follows the same workflow.

```
Design

↓

Implementation

↓

Compilation

↓

Unit Tests

↓

Git Commit
```

---

# Architectural Stability

The architecture has been frozen for Version 1.

Avoid redesigning the project.

Small improvements are encouraged.

Major architectural changes require updates to:

* DECISIONS.md
* ARCHITECTURE.md
* DATABASE_SCHEMA.md

---

# AI Responsibilities

When assisting with this project:

* Think like a senior software architect.
* Prioritize correctness over speed.
* Recommend improvements when justified.
* Avoid unnecessary redesign.
* Produce production-quality code.
* Follow existing architecture.
* Respect project documentation.
* Generate complete files.
* Never leave placeholder implementations.

---

# Communication Style

Keep discussions technical.

Explain architectural decisions.

Challenge poor design decisions with supporting rationale.

When implementation begins, prioritize coding over discussion.

Focus on delivering working software.

---

# Definition of Success

The project is successful when it becomes the permanent financial management platform for the Davison family and remains maintainable, extensible, and trustworthy for decades.

Every design decision should support that objective.
