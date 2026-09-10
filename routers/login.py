from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from auth import verify_password, create_token
from database import get_db
from repositories import UsersRepository
from schema import UserLogin

router = APIRouter()

LOGIN_LIMIT_IP = {}


@router.post("/")
async def login(
    request: Request,
    income_user: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    ip_cliente = request.client.host
    limit_existente = LOGIN_LIMIT_IP.get(ip_cliente, {})

    if limit_existente.get("blocked_until") and datetime.now(timezone.utc) < limit_existente["blocked_until"]:
        raise HTTPException(status_code=429, detail={"msg": "Demasiados intentos fallidos. Intente más tarde."})

    user_repo = UsersRepository(db)
    usuario = await user_repo.get_user(income_user)

    if not usuario or not verify_password(income_user, usuario):
        intentos = limit_existente.get("attempts", 0) + 1
        nuevo_registro = {"attempts": intentos, "blocked_until": None}

        if intentos >= 5:
            nuevo_registro["blocked_until"] = datetime.now(timezone.utc) + timedelta(minutes=10)

        LOGIN_LIMIT_IP[ip_cliente] = nuevo_registro
        raise HTTPException(status_code=403, detail={"msg": "Credenciales incorrectas"})

    LOGIN_LIMIT_IP.pop(ip_cliente, None)

    await user_repo.update_last_login(usuario)
    access_token = create_token({"sub": income_user.username})

    return JSONResponse(
        content={"access_token": access_token, "token_type": "bearer"},
        status_code=200
    )