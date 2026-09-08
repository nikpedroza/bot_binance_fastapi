from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from models import Trades
from schema import NewTradeRequest

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
    
    async def get_all_trades_by_users(self, user_id: UUID) -> Trades:
        query = select(Trades).where(Trades.user_id == user_id)
        result = await self.db.execute(
            query
            .order_by(Trades.tiempo_entrada.asc())
            )
        return result.scalars().all()
    
    async def insert_trades(self,user_id: UUID, new_trade: NewTradeRequest):
        insert_trade = Trades(
            user_id=user_id,
            symbol=new_trade.symbol,
            entrada=new_trade.entrada,
            salida=new_trade.salida,
            tipo=new_trade.tipo,
            razon_salida=new_trade.razon_salida,
            pnl_neto=new_trade.pnl_neto,
            comision=new_trade.comision,
            funding_total=new_trade.funding_total,
            tiempo_entrada=new_trade.tiempo_entrada,
            tiempo_salida=new_trade.tiempo_salida,
            balance_acumulado=new_trade.balance_acumulado,
            strategy=new_trade.strategy,
            order_id_market=new_trade.order_id_market,
            order_id_sl=new_trade.order_id_sl,
            order_id_tp=new_trade.order_id_tp,
        )
        self.db.add(insert_trade)
        await self.db.commit()