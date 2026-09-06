from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from repositories import TradesRepository
from schema import PaginatedTrades, TradesAnalysis
from models import Users
from auth import get_current_user
from database import get_db
from analysis import analyze_bot

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

@router.get("/analysis", response_model=TradesAnalysis)
async def analysis(
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
    ):
    trades_repo = TradesRepository(db)
    trades = await trades_repo.get_all_trades_by_users(current_user.id)

    if not trades:
        raise HTTPException(status_code=404, detail={"msg": "Usuario sin trades existentes"})
    
    resultado = analyze_bot(trades)
    if resultado is None:
        raise HTTPException(status_code=500, detail={"msg": "No se pudo generar el análisis"})
    
    return resultado