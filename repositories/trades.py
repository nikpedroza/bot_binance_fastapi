from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from models import Trades

class TradesRepository():
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_trades_by_user(
        self,
        user_id: UUID,
        offset: int,
        page_size: int,
        symbol: str | None
    ) -> tuple[list[Trades], int]:
        query = select(Trades).where(Trades.user_id == user_id)
        count_query = select(func.count()).select_from(Trades).where(Trades.user_id == user_id)

        if symbol:
            query = query.where(Trades.symbol == symbol)
            count_query = count_query.where(Trades.symbol == symbol)

        result = await self.db.execute(
            query.order_by(Trades.tiempo_entrada.desc())
            .limit(page_size)
            .offset(offset)
        )
        trades = result.scalars().all()

        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        return trades, total