# Davison Financial Model

## Project Overview

The Davison Financial Model is a private Python application for
managing investment portfolio information.

The initial objective is to reliably import brokerage Excel snapshots,
retain the historical information, and calculate current and historical
portfolio values.

---

# Current Scope

The application currently supports two brokerage providers:

* BMO
* Nesbitt Burns

Both provide Excel portfolio exports.

The application imports those exports into a SQLite database.

---

# Core Workflow

```text
Brokerage Excel Export
        |
        v
ExcelReader
        |
        v
Brokerage Importer
        |
        v
ImportService
        |
        v
SQLite Database
        |
        v
Portfolio Services
        |
        v
Portfolio Valuation