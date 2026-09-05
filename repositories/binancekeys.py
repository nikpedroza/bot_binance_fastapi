from sqlalchemy.ext.asyncio import AsyncSession

from models import BinanceKeys

class BinanceKeysRepository():
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_key_by_userid(self, userid) -> BinanceKeys:
        pass