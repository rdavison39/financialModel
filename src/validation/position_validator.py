"""
account_validator.py

Defines the validator for ImportedAccount DTOs.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from src.dto.imported_account import ImportedAccount
from src.validation.validator import Validator


class AccountValidator(Validator):
    """
    Validates ImportedAccount DTOs.
    """

    def validate(
        self,
        dto: ImportedAccount,
    ) -> None:
        """
        Validate an ImportedAccount.

        Raises:
            ValueError:
                If the DTO contains invalid data.
        """

        #
        # Brokerage
        #

        if not dto.brokerage_name.strip():
            raise ValueError(
                "Brokerage name cannot be empty."
            )

        #
        # Account Number
        #

        if not dto.account_number.strip():
            raise ValueError(
                "Account number cannot be empty."
            )

        #
        # Account Name
        #

        if not dto.account_name.strip():
            raise ValueError(
                "Account name cannot be empty."
            )

        #
        # Owner
        #

        if not dto.owner.strip():
            raise ValueError(
                "Account owner cannot be empty."
            )

        #
        # Account Type
        #

        if not dto.account_type.strip():
            raise ValueError(
                "Account type cannot be empty."
            )

        #
        # Currency
        #

        if not dto.currency.strip():
            raise ValueError(
                "Currency cannot be empty."
            )

        if len(dto.currency) != 3:
            raise ValueError(
                "Currency must be a three-character ISO code."
            )