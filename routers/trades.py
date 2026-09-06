from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from repositories import TradesRepository
from schema import PaginatedTrades
from models import Users
from auth import get_current_user
from database import get_db

router = APIRouter()

@router.get("/", response_model=PaginatedTrades)
async def trades(
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=50),
    symbol: str | None = Query(default=None)
):
    trades_repo = TradesRepository(db)
    offset = (page - 1) * page_size
    trades_result, total = await trades_repo.get_trades_by_user(current_user.id, offset, page_size, symbol)

    if not trades_result:
        raise HTTPException(status_code=404, detail={"msg": "Usuario sin trades existentes"})

    return PaginatedTrades(
        data=trades_result,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=-(-total // page_size)
    )