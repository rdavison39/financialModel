"""
imported_account.py

Defines the ImportedAccount DTO.

ImportedAccount is an immutable data transfer object produced by
brokerage importers.

It contains only factual data read from a brokerage export.

Importers create these objects.

ImportService consumes them.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ImportedAccount:
    """
    Immutable account imported from a brokerage export.
    """

    brokerage_name: str

    account_number: str

    account_name: str

    owner: str

    account_type: str

    currency: str