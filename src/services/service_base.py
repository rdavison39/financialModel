"""
service_base.py

Defines the abstract base class for all services in the
Davison Financial Model.

Services coordinate business logic and orchestrate repositories
through a UnitOfWork.

Business logic belongs in services.

Persistence belongs in repositories.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from src.database.unit_of_work import UnitOfWork


class ServiceBase:
    """
    Base class for all business services.
    """

    def __init__(
        self,
        uow: UnitOfWork,
    ) -> None:
        """
        Initialize the service.

        Args:
            uow:
                UnitOfWork used to access repositories and manage
                transactions.
        """

        self._uow = uow

    @property
    def uow(self) -> UnitOfWork:
        """
        Return the UnitOfWork.
        """

        return self._uow

    #
    # Transaction Helpers
    #

    def commit(self) -> None:
        """
        Commit the current transaction.
        """

        self.uow.commit()

    def rollback(self) -> None:
        """
        Roll back the current transaction.
        """

        self.uow.rollback()

    def flush(self) -> None:
        """
        Flush pending changes.
        """

        self.uow.flush()