# Davison Financial Model

## Project Overview

The Davison Financial Model is a private Python application for
managing the Davison family's long-term financial information.

The goal is to create one trustworthy source of truth for portfolio
holdings, cash balances, historical market data, retirement planning,
tax planning, estate planning, trust planning, and financial reporting.

The first production milestone is reliable brokerage import. The
application begins with BMO InvestorLine exports and is designed to
support additional brokerages later.

## Current Objective

The current development objective is to persist imported BMO
InvestorLine data into SQLite.

The import path is:

```text
BMO Excel workbook
-> ExcelReader
-> WorksheetHelper
-> BMOLayout
-> BMOInvestorLineImporter
-> ImportedAccount / ImportedPosition / ImportedCash DTOs
-> ImportService
-> Repositories
-> SQLite database
```

## Core Principles

The project follows these principles:

* Store facts only.
* Calculate derived values on demand.
* Preserve historical imports permanently.
* Keep importers independent from persistence.
* Keep database access inside repositories.
* Keep business orchestration inside services.
* Use Decimal for financial values.
* Keep features independently testable.

## Stored Facts

The database stores factual records such as:

* Brokerages
* Accounts
* Companies
* Import records
* Holding snapshots
* Cash balance snapshots
* Market prices

The database does not store calculated values such as:

* Portfolio value
* Unrealized gains
* Asset allocation
* Retirement projections
* Tax projections
* Estate projections

Those values are calculated from stored facts.

## Implementation Roadmap

### Phase 2: ImportService

Persist imported DTOs into the database.

Deliverables:

* Validate imported account data.
* Create one Import record per import operation.
* Find or create Brokerage, Account, and Company records.
* Create immutable HoldingSnapshot records.
* Create immutable CashBalanceSnapshot records.
* Commit successful imports.
* Roll back failed imports.
* Return an ImportResult summary.

### Phase 3: End-to-End Import

Make a full import usable from a script or command-line entry point.

Deliverables:

* Import one workbook.
* Provide a local web GUI to upload a workbook and display results.
* Import every workbook in a folder.
* Produce a clear import summary.
* Add duplicate-import safeguards where practical.

### Phase 4: Portfolio Services

Build read-only portfolio calculations from snapshots.

Deliverables:

* Current portfolio view.
* Account totals.
* Company totals.
* Cash totals.
* Book cost and market value summaries.

### Phase 5: Reporting

Generate reports from calculated portfolio views.

Deliverables:

* Excel portfolio summary.
* Account-level reports.
* Holdings reports.
* Cash balance reports.

### Phase 6: Market Data and Income

Add external market facts and dividend/income support.

Deliverables:

* Historical market prices.
* Current price updates.
* Dividend facts.
* Income summaries.

### Phase 7: Planning Engines

Build long-range planning features after portfolio facts are reliable.

Deliverables:

* Retirement cash-flow modelling.
* Tax estimates.
* Estate projections.
* Trust and inheritance scenarios.

## Technology Stack

* Python 3.13
* SQLite
* SQLAlchemy
* openpyxl
* pytest
* ruff

## Documentation

The `docs` directory is the project specification. If documentation and
implementation disagree, update the documentation or implementation
until they tell the same story.
