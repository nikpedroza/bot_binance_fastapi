from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from repositories import BinanceKeysRepository
from bnc import BinanceAdmin
#from schema import UserResponse
from models import Users
from auth import get_current_user, decode_key
from database import get_db

router = APIRouter()

@router.get("/")
async def status(
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    binance_keys = BinanceKeysRepository(db)
    result = await binance_keys.get_key_by_userid(current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail={"msg":"Claves API inexistente"})

    public_key = decode_key(result.api_key)
    private_key = decode_key(result.api_secret)

    bnc = BinanceAdmin(current_user.username, public_key, private_key)
    balance = bnc.get_balance_futuros()
    #TEST
    return {
        "username": current_user.username,
        "balance": balance,
    }