# Davison Financial Model

# Architecture Decision Log

**Version:** 1.0

---

# Purpose

This document records significant architectural and design decisions made during the development of the Davison Financial Model.

The objective is to preserve the reasoning behind important decisions so they are not lost over time.

Every architectural change that affects the long-term design of the application should be recorded here.

---

# Decision Format

Each decision includes:

* Decision Number
* Date
* Status
* Decision
* Context
* Alternatives Considered
* Rationale
* Consequences

---

# Decision 001

## Title

Use brokerage exports instead of direct brokerage integration.

### Status

Accepted

### Date

2026-06

### Context

Two approaches were considered.

Option 1

Import exported Excel files from the brokerage.

Option 2

Log directly into the brokerage website and retrieve holdings.

### Alternatives Considered

* Website automation
* Screen scraping
* Brokerage APIs

### Decision

The application will use exported brokerage files.

Initially:

* BMO InvestorLine

Future brokerages may be added.

### Rationale

Advantages

* Reliable
* Repeatable
* No credentials stored
* No dependence on brokerage websites
* No multi-factor authentication issues
* Easy to test
* Historical exports can be archived

### Consequences

Users must periodically export holdings from their brokerage.

This manual step is considered acceptable.

---

# Decision 002

## Title

Maintain complete import history.

### Status

Accepted

### Context

Two approaches were considered.

Option A

Overwrite existing holdings.

Option B

Preserve every brokerage import.

### Decision

Every brokerage import becomes permanent.

Nothing is overwritten.

### Rationale

Historical information is valuable.

Examples

* Portfolio history
* Asset allocation changes
* Historical reporting
* Performance analysis

### Consequences

Database size increases over time.

This is considered acceptable.

Storage costs are negligible.

---

# Decision 003

## Title

Database stores facts only.

### Status

Accepted

### Decision

The database stores factual information only.

Examples

* Shares
* Book Cost
* Market Prices
* Import History

Calculated values are not persisted.

Examples

* Portfolio Value
* Asset Allocation
* Retirement Projections
* Estate Values

### Rationale

Avoid duplicated information.

Prevent stale calculations.

Improve consistency.

---

# Decision 004

## Title

Historical data is immutable.

### Status

Accepted

### Decision

Historical imports are never modified.

Updates create new records.

### Rationale

Provides a complete audit trail.

Allows historical reporting.

Improves confidence in calculations.

---

# Decision 005

## Title

Python Decimal used for financial calculations.

### Status

Accepted

### Decision

Floating point numbers will not be used for money.

Python Decimal and SQL NUMERIC fields will be used.

### Rationale

Financial calculations require deterministic precision.

Avoid floating point rounding errors.

---

# Decision 006

## Title

Use SQLAlchemy.

### Status

Accepted

### Decision

SQLAlchemy is the application's ORM.

### Alternatives

* Raw SQL
* Peewee
* Django ORM

### Rationale

SQLAlchemy is mature, well documented, flexible and widely used.

---

# Decision 007

## Title

Use Alembic.

### Status

Accepted

### Decision

Database schema changes will be managed through Alembic.

Manual schema changes are prohibited.

### Rationale

Supports controlled database evolution.

Provides repeatable deployments.

---

# Decision 008

## Title

Use openpyxl.

### Status

Accepted

### Decision

Excel import and report generation will use openpyxl.

### Alternatives

* pandas
* xlrd

### Rationale

The brokerage exports contain structured worksheets rather than pure tables.

openpyxl provides direct worksheet access and supports future report generation.

---

# Decision 009

## Title

Use HoldingSnapshot entity.

### Status

Accepted

### Context

Several names were considered.

* Position
* PortfolioSnapshot
* Holding
* HoldingSnapshot

### Decision

HoldingSnapshot was selected.

### Rationale

The imported data represents a single holding at one point in time.

The name accurately reflects the business concept.

---

# Decision 010

## Title

Importer returns DTOs.

### Status

Accepted

### Decision

Importers return DTO objects.

They never communicate directly with the database.

### Rationale

Separates importing from persistence.

Improves testing.

Supports future brokerages.

---

# Decision 011

## Title

Repository Pattern

### Status

Accepted

### Decision

Business services never communicate directly with SQLAlchemy.

Repositories provide all persistence.

### Rationale

Improves maintainability.

Simplifies testing.

Encapsulates database access.

---

# Decision 012

## Title

Professional Documentation

### Status

Accepted

### Decision

The project documentation is considered part of the source code.

Documentation shall be maintained alongside implementation.

### Rationale

Documentation becomes the permanent memory of the project.

Future development should rely on documentation rather than conversation history.

---

# Decision 013

## Title

Architecture Freeze

### Status

Accepted

### Decision

Once Version 1.0 architecture is complete, changes to the core architecture require an entry in this document.

### Rationale

Prevents unnecessary redesign.

Encourages stability.

Allows controlled evolution.

---

# Future Decisions

Future architectural decisions will be recorded here.

Examples

* Multi-currency support
* Transaction engine
* Dividend engine
* Trust engine
* Estate engine
* Cloud synchronization
* AI-assisted financial planning

---

# Review Process

Before implementing a major architectural change:

1. Review existing decisions.
2. Determine whether the change conflicts with previous decisions.
3. Record a new decision.
4. Update the relevant documentation.
5. Implement the change.

---

# Guiding Principle

Architecture should evolve deliberately.

Design decisions should be based on long-term maintainability rather than short-term convenience.

When in doubt, favour simplicity, transparency, and historical accuracy.
