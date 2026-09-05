from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from models import BinanceKeys

class BinanceKeysRepository():
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_key_by_userid(self, user_id: UUID) -> BinanceKeys:
        query = select(BinanceKeys).where(BinanceKeys.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()