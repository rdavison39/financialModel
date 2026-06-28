# Davison Financial Model

**Version:** 0.1.0 (Pre-Alpha)

---

# Overview

The Davison Financial Model is a Python-based personal wealth management platform designed specifically for the Davison family.

Unlike commercial portfolio software, this application is designed to integrate investment management, retirement planning, tax planning, estate planning, trust management, and financial reporting into a single application.

The project is intended to become the single source of truth for the family's financial information.

---

# Primary Objectives

The application will:

* Import portfolio holdings from brokerage exports
* Maintain a complete historical record of portfolio snapshots
* Download and maintain historical market prices
* Track portfolio performance
* Forecast dividend income
* Model retirement cash flow
* Optimize RRSP, TFSA and taxable account withdrawals
* Estimate income taxes
* Estimate estate values
* Model inheritance scenarios
* Produce professional Excel reports

---

# Design Philosophy

The application is designed around several core principles.

## Facts vs Calculations

The database stores **facts**.

Examples:

* Accounts
* Companies
* Shares owned
* Book cost
* Average cost
* Imported brokerage data
* Historical market prices

The database does **not** permanently store calculated values such as:

* Portfolio value
* Unrealized gains
* Asset allocation
* Retirement projections
* Estate values

These values are always calculated from the stored facts.

---

## Historical Accuracy

Nothing is ever overwritten.

Each brokerage export becomes a permanent portfolio snapshot.

Historical portfolio data is never lost.

This allows the application to answer questions such as:

* What did my portfolio look like one year ago?
* How has my allocation changed?
* What was my dividend income last quarter?
* What was my portfolio worth on a particular date?

---

## Single Responsibility

Every class has one responsibility.

Examples:

* Importers import.
* Database classes persist data.
* Portfolio services perform calculations.
* Report generators create reports.

Responsibilities are never mixed.

---

# Current Brokerage Support

Initial development targets:

* BMO InvestorLine

Future support:

* RBC Direct Investing
* Questrade
* Interactive Brokers
* Wealthsimple
* Fidelity

---

# Planned Features

## Portfolio Management

* Portfolio snapshots
* Historical performance
* Company allocation
* Sector allocation
* Currency exposure
* Dividend income
* Capital gains
* Risk analysis

---

## Market Data

* Historical prices
* Live prices
* Dividend history
* Corporate actions

---

## Retirement Planning

* RRSP withdrawal optimization
* TFSA optimization
* CPP planning
* OAS planning
* Cash-flow forecasting
* Monte Carlo simulations (future)

---

## Tax Planning

* Capital gains
* Dividend tax credits
* Ontario tax estimates
* Withdrawal sequencing
* Trust distributions

---

## Estate Planning

* Estate valuation
* Inheritance scenarios
* Trust planning
* Beneficiary modelling

---

# Project Structure

```
FinancialModel/

    data/
        raw/
        processed/
        cache/

    database/

    docs/

    reports/

    logs/

    src/

        config/

        database/

        dto/

        importers/

        market/

        models/

        repositories/

        services/

        reporting/

        utils/

    tests/
```

---

# Technology Stack

Language

* Python 3.13

Database

* SQLite
* SQLAlchemy
* Alembic

Excel

* openpyxl

Testing

* pytest

Utilities

* pathlib
* decimal
* logging

Future

* Yahoo Finance
* Plotly
* Dash (optional)

---

# Current Status

Current development phase:

**Sprint 1**

Current objective:

Import BMO InvestorLine portfolio exports into the application.

Current milestone:

Read one brokerage export and build an in-memory representation of the portfolio.

---

# Development Philosophy

This project follows professional software engineering practices.

Every feature should:

* Have a written specification.
* Have unit tests.
* Have logging.
* Be documented.
* Be committed to Git.
* Be independently testable.

---

# Documentation

Project documentation is located in the `docs` directory.

The documentation is considered the authoritative specification for the project.

Developers should consult the documentation before modifying code.

---

# License

Private software.

Developed exclusively for the Davison family.

Not intended for public distribution.

---

# Acknowledgements

This application is being developed collaboratively by Ron Davison and ChatGPT.

The objective is to build a long-term financial management platform capable of supporting the family's investment, retirement, tax, and estate planning needs for many years.
