# Contributing to the Davison Financial Model

## Purpose

This document defines the development workflow and coding standards for the Davison Financial Model.

Although this project is currently maintained by a single developer, these guidelines ensure consistency over the lifetime of the project and make it easy for future contributors—or even your future self—to understand how the project is developed.

---

# Project Philosophy

The objective is **not** to write code quickly.

The objective is to build software that remains understandable, maintainable, and correct for decades.

When choosing between:

* shorter code vs. clearer code
* clever code vs. readable code
* fast implementation vs. maintainability

Always choose the maintainable solution.

---

# Development Workflow

Every feature follows the same workflow.

```
Idea

↓

Architecture Review

↓

Documentation (if required)

↓

Implementation

↓

Unit Tests

↓

Manual Testing

↓

Git Commit
```

Large architectural changes must be documented before implementation.

---

# Coding Standards

## General

* One class per file.
* One responsibility per class.
* Prefer composition over inheritance.
* Avoid global state.
* Avoid duplicated code.
* Use meaningful names.
* Write self-documenting code.

---

## Type Hints

Every public function must include complete type hints.

Example

```python
def load_account(filename: Path) -> ImportedAccount:
    ...
```

---

## Docstrings

Every public class and public function must have a docstring.

Use clear English.

Explain **why**, not just **what**.

---

## Financial Calculations

Floating point values must never be used for financial calculations.

Always use:

```python
Decimal
```

Database numeric fields must use SQL NUMERIC types.

---

## Imports

Use standard library imports first.

Third-party imports second.

Project imports last.

Example

```python
from pathlib import Path

from openpyxl import load_workbook

from src.dto.imported_account import ImportedAccount
```

---

## Logging

Every subsystem should log meaningful events.

Examples

* Import started
* Import completed
* Validation failure
* Database update
* Report generated

Never log confidential financial information.

---

# Error Handling

Never silently ignore exceptions.

Avoid:

```python
except:
    pass
```

Catch only exceptions that can be handled.

Unexpected exceptions should be logged and re-raised.

---

# Repository Structure

```
src/
    config/
    database/
    dto/
    importers/
    market/
    models/
    repositories/
    reporting/
    services/
    utils/

tests/

docs/

data/

reports/

logs/
```

Each directory has a single purpose.

---

# Unit Testing

Every new class should have a corresponding test.

Example

```
src/importers/bmo_investorline_importer.py

↓

tests/importers/test_bmo_investorline_importer.py
```

Tests should be:

* repeatable
* isolated
* deterministic

---

# Git Workflow

Keep commits focused.

Good examples

```
Add BMO InvestorLine importer

Add PortfolioService

Implement HoldingSnapshot model
```

Avoid commits such as

```
Stuff

Changes

Fixes
```

---

# Branch Strategy

Current strategy

```
main
```

Future (if required)

```
main

feature/portfolio-engine

feature/tax-engine

bugfix/import-validation
```

---

# Documentation

Documentation is part of the source code.

Whenever architecture changes:

Update:

* ARCHITECTURE.md
* DATA_MODEL.md
* DATABASE_SCHEMA.md
* DECISIONS.md
* PROJECT_STATE.md

Documentation should never become outdated.

---

# Code Reviews

Before committing, ask the following questions:

* Is this code easy to understand?
* Is it properly documented?
* Is it tested?
* Does it follow the architecture?
* Is there duplicated logic?
* Is there a simpler design?

If the answer to any question is "No", improve the implementation before committing.

---

# Pull Requests

If this project ever expands beyond a single developer:

Every pull request should include:

* Description
* Motivation
* Testing performed
* Documentation updates
* Breaking changes (if any)

---

# AI-Assisted Development

AI is considered a development partner, not the source of truth.

AI-generated code must always be:

* reviewed
* understood
* tested

Architectural decisions should remain consistent with the project documentation.

---

# Long-Term Vision

The goal is to create software that can be maintained confidently ten or twenty years from now.

Future developers should be able to understand the project by reading the documentation before reading the code.

Consistency is more important than speed.

Correctness is more important than convenience.

Maintainability is more important than cleverness.

When in doubt, choose the simpler design.
