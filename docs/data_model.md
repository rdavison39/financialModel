# Davison Financial Model

# Data Model

**Version:** 1.0

---

# Purpose

This document defines the business entities used throughout the Davison Financial Model.

These entities represent real-world financial concepts rather than database tables.

The database schema, SQLAlchemy models, repositories, and business services are derived from this document.

---

# Design Philosophy

The data model represents financial reality.

It should not be influenced by:

* database design
* programming language
* reporting requirements
* user interface

The business model always comes first.

---

# Core Principles

The application stores only facts.

Facts include:

* ownership
* historical portfolio snapshots
* imported brokerage data
* market prices

Everything else is calculated.

---

# Business Entities

The application consists of the following primary entities.

---

# Account

Represents a single investment account.

Examples

* Ron RRSP
* Ron TFSA
* Ron Margin
* Sonya RRSP
* Sonya TFSA
* Family Trust
* Betty Non-Registered

---

## Attributes

* Account Number
* Account Name
* Owner
* Brokerage
* Account Type
* Currency
* Status

---

## Relationships

An Account contains many Portfolio Snapshots.

An Account belongs to one Brokerage.

---

# Brokerage

Represents a financial institution.

Examples

* BMO InvestorLine
* RBC Direct Investing
* Questrade
* Interactive Brokers

---

## Attributes

* Name
* Website
* Import Format
* Active

---

# Company

Represents a publicly traded security.

Examples

* TD Bank
* BCE
* Brookfield
* Apple
* Enbridge

---

## Attributes

* Ticker
* Name
* Exchange
* Currency
* Asset Class
* Sector
* Industry
* Country

---

## Relationships

One Company may appear in many Portfolio Snapshots.

One Company has many Market Prices.

---

# Import

Represents a single brokerage import operation.

One import may contain multiple brokerage accounts.

An Import is immutable.

---

## Attributes

* Import ID
* Import Date
* Source Folder
* Brokerage
* Number of Accounts
* Number of Holdings
* Validation Status
* Notes

---

# Portfolio Snapshot

Represents one security held in one account during one import.

This is the most important entity in the application.

A Portfolio Snapshot never changes.

Every import creates a new snapshot.

---

## Attributes

* Account
* Company
* Import
* Shares
* Average Cost
* Book Cost
* Imported Market Price
* Imported Market Value
* Imported Unrealized Gain
* Imported Dividend
* Imported Yield

---

## Relationships

Belongs to

* one Account
* one Company
* one Import

---

# Market Price

Represents the market price of a security on a specific day.

---

## Attributes

* Company
* Date
* Open
* High
* Low
* Close
* Volume
* Dividend

---

## Relationships

Belongs to one Company.

---

# Portfolio

The Portfolio is NOT a database table.

It is a calculated object.

The Portfolio is produced by combining:

Portfolio Snapshots

*

Market Prices

---

The Portfolio provides calculations such as

* Current Value
* Book Value
* Unrealized Gain
* Sector Allocation
* Company Allocation
* Dividend Income

---

# Retirement Projection

Not stored.

Calculated.

Inputs include

* Portfolio
* Spending
* CPP
* OAS
* Inflation
* Investment Returns
* Tax Rules

---

# Tax Projection

Not stored.

Calculated.

Uses

* Portfolio
* Retirement Projection
* Tax Rules

Produces

* Income Tax
* Capital Gains
* Dividend Tax Credits
* Net Cash Flow

---

# Estate Projection

Not stored.

Calculated.

Uses

* Portfolio
* Tax Projection
* Trust Information
* Beneficiaries

Produces

* Estate Value
* Estimated Taxes
* Distribution Scenarios

---

# Report

Reports are generated from calculated objects.

Reports are never considered the source of truth.

Examples

* Portfolio Summary
* Retirement Report
* Tax Report
* Estate Report

---

# Entity Relationships

```text
Brokerage
    │
    ├───────────────┐
    │               │
    ▼               ▼

Account          Import
    │               │
    │               │
    └──────┬────────┘
           │
           ▼

Portfolio Snapshot

     │

     ├────────────► Company

     │                 │

     │                 ▼

     │           Market Price

     │

     ▼

Portfolio

     │

     ├────────► Retirement Projection

     │

     ├────────► Tax Projection

     │

     └────────► Estate Projection

                    │

                    ▼

                 Reports
```

---

# Lifetime of Data

The lifetime of each entity is different.

Brokerage

Created once.

Rarely changes.

---

Company

Created once.

Occasionally updated.

---

Account

Created once.

Rarely changes.

---

Import

Created every import.

Never modified.

---

Portfolio Snapshot

Created every import.

Never modified.

---

Market Price

Created daily.

Never modified.

---

Portfolio

Calculated on demand.

Never stored.

---

Retirement Projection

Calculated on demand.

Never stored.

---

Estate Projection

Calculated on demand.

Never stored.

---

# Design Rules

The following rules apply throughout the application.

1. Business entities represent real financial concepts.

2. Calculated objects are never persisted.

3. Historical information is immutable.

4. Every Portfolio Snapshot belongs to one Import.

5. Every Company exists only once.

6. Every Account exists only once.

7. Every Import is permanent.

8. Reports never contain master data.

9. Reports are disposable.

10. The database stores facts only.

---

# Future Extensions

The data model has been designed to support future features including:

* Multiple brokerages
* Multiple currencies
* Options
* Bonds
* GICs
* Private investments
* Real estate
* Precious metals
* Cryptocurrency
* Corporate accounts
* Family partnerships
* Additional trusts

without requiring major architectural redesign.
