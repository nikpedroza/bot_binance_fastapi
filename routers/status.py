from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from schema import UserResponse
from models import Users
from auth import get_current_user

router = APIRouter()

@router.get("/", response_model=UserResponse)
async def me(current_user: Users = Depends(get_current_user)):
    return JSONResponse(
        status_code=200,
        content={"msg":"OK"}
    )