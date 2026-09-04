from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from auth import verify_password, crear_token
from database import get_db
from repositories import UsersRepository

from schema import UserLogin

login_router = APIRouter()

@login_router.post("/")
async def login(
    income_user : UserLogin,
    db : AsyncSession = Depends(get_db)
):
    user_repo = UsersRepository(db)
    usuario = await user_repo.get_user(income_user)
    if not usuario:
        raise HTTPException(status_code=403, detail={"msg":"Credenciales incorrectas"})
    if not verify_password(income_user, usuario):
        raise HTTPException(status_code=403, detail={"msg":"Credenciales incorrectas"})

    await user_repo.update_last_login(usuario)

    access_token = crear_token(
        {"sub":income_user.username}
    )

    return JSONResponse(
        content={
            "access_token": access_token,
            "token_type": "bearer"
        },
        status_code=200
    )
    
    
