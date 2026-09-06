from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from repositories import BinanceKeysRepository
from bnc import BinanceAdmin
from schema import Status
from models import Users
from auth import get_current_user, decode_key
from database import get_db

router = APIRouter()

@router.get("/", response_model=Status)
async def status(
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    binance_keys = BinanceKeysRepository(db)
    binance_result = await binance_keys.get_key_by_userid(current_user.id)
    if not binance_result:
        raise HTTPException(status_code=404, detail={"msg":"Claves API inexistente"})

    public_key = decode_key(binance_result.api_key)
    private_key = decode_key(binance_result.api_secret)

    bnc = BinanceAdmin(current_user.username, public_key, private_key)
    balance = bnc.get_balance_futuros()
    posiciones = bnc.get_posiciones_activas()
    return Status(
        username = current_user.username,
        balance = balance,
        posiciones = posiciones
    )