# Davison Financial Model

# Data Model

**Version:** 2.0

---

# Purpose

This document describes the persistent data model used by the Davison
Financial Model.

The model is intentionally simple and represents the information
required to import brokerage snapshots and calculate portfolio values.

---

# Core Principles

## Historical Imports Are Immutable

Brokerage imports represent historical snapshots.

Once imported, the holding and cash records are not modified.

A later brokerage import creates a new snapshot.

---

## Quantities Come From Brokerage Imports

Security quantities are changed only by importing a new brokerage
snapshot.

Portfolio valuation does not change quantities.

---

## Calculated Values

Portfolio valuation is calculated from:

* Latest imported holdings
* Latest imported cash
* Current market prices
* Current currency conversion

Daily calculated portfolio values are stored as `PortfolioSnapshot`
records.

---

# Entities

The current database contains seven entities.

```text
Brokerage
Account
Company
ImportRecord
HoldingSnapshot
CashSnapshot
PortfolioSnapshot