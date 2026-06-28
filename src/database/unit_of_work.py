"""
unit_of_work.py

Defines the UnitOfWork used by the Davison Financial Model.

The UnitOfWork owns a SQLAlchemy session and provides access to all
repositories using that session.

Business services interact with repositories through the UnitOfWork
rather than constructing repositories directly.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.repositories.account_repository import AccountRepository
from src.repositories.brokerage_repository import BrokerageRepository
from src.repositories.company_repository import CompanyRepository
from src.repositories.holding_snapshot_repository import (
    HoldingSnapshotRepository,
)
from src.repositories.import_repository import ImportRepository
from src.repositories.market_price_repository import (
    MarketPriceRepository,
)


class UnitOfWork:
    """
    Coordinates repository access using a shared SQLAlchemy session.
    """

    def __init__(
        self,
        session: Session,
    ) -> None:
        """
        Initialize the UnitOfWork.

        Args:
            session:
                SQLAlchemy session shared by every repository.
        """

        self._session = session

        #
        # Repository instances
        #

        self.brokerages = BrokerageRepository(session)

        self.accounts = AccountRepository(session)

        self.companies = CompanyRepository(session)

        self.imports = ImportRepository(session)

        self.holdings = HoldingSnapshotRepository(session)

        self.market_prices = MarketPriceRepository(session)

    @property
    def session(self) -> Session:
        """
        Return the SQLAlchemy session.
        """

        return self._session

    #
    # Transaction Management
    #

    def commit(self) -> None:
        """
        Commit the current transaction.
        """

        self.session.commit()

    def rollback(self) -> None:
        """
        Roll back the current transaction.
        """

        self.session.rollback()

    def flush(self) -> None:
        """
        Flush pending changes.
        """

        self.session.flush()

    def refresh(
        self,
        entity: object,
    ) -> None:
        """
        Refresh an entity from the database.
        """

        self.session.refresh(entity)