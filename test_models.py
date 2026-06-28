from src.database.base import Base

# Import every model

from src.models.brokerage import Brokerage
from src.models.account import Account
from src.models.company import Company
from src.models.import_record import Import
from src.models.holding_snapshot import HoldingSnapshot
from src.models.market_price import MarketPrice

print("All models imported successfully.")
print(f"Tables found: {len(Base.metadata.tables)}")

for table in Base.metadata.tables:
    print(table)