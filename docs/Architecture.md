# Davison Financial Model

# System Architecture

**Version:** 2.0

---

# Purpose

This document describes the current software architecture of the
Davison Financial Model.

It is the authoritative description of how the application is organized
and how its components interact.

The architecture is intentionally simple. The application currently
supports BMO InvestorLine and Nesbitt Burns brokerage Excel exports.

---

# Architectural Principles

## Simple Design

The application is deliberately kept simple.

There is no generic brokerage framework, repository layer, or unnecessary
abstraction.

Components should have clear responsibilities and should be easy to
understand and test.

---

## Store Historical Facts

Brokerage imports are historical facts and are retained.

Holding quantities and cash balances come from brokerage snapshots and
are never changed by portfolio valuation.

Calculated portfolio values are stored separately as daily valuation
snapshots.

---

## Decimal for Financial Values

`Decimal` is used for quantities and monetary values where appropriate.

Floating-point arithmetic should not be used for financial calculations.

---

## One Class Per File

Each major class is contained in its own Python file.

Classes should have one clear responsibility.

---

# High-Level Architecture

```text
                    Brokerage Excel File
                           |
                           v
                     ExcelReader
                           |
                           v
              +-------------------------+
              |      Brokerage          |
              |       Importer          |
              +-------------------------+
                    /            \
                   /              \
                  v                v
          ImportedAccount     ImportedHolding
                  |                |
                  |                |
                  +-------+--------+
                          |
                          v
                    ImportService
                          |
                          v
                   SQLAlchemy Models
                          |
                          v
                       SQLite
                          |
             +------------+-------------+
             |            |             |
             v            v             v
      PortfolioService  History   Comparison
             |
             v
      PortfolioValuationService
             |
             v
      MarketPriceService
             |
             v
      PortfolioSnapshot