"""
validator.py

Defines the abstract base class for all validators used by the
Davison Financial Model.

Validators verify imported DTOs before they reach the service layer.

Validators do not modify DTOs.

Validators raise ValueError when invalid data is encountered.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod


class Validator(ABC):
    """
    Abstract base class for validators.
    """

    @abstractmethod
    def validate(self, dto: object) -> None:
        """
        Validate a DTO.

        Raises:
            ValueError:
                If the DTO is invalid.
        """

        raise NotImplementedError