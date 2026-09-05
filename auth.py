from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from repositories import UsersRepository
from sqlalchemy.ext.asyncio import AsyncSession
from cryptography.fernet import Fernet

from database import get_db
from schema import UserLogin
from models import Users
from config import config

bearer = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
fernet = Fernet(config.FERNET_KEY)

def verify_password(income_user: UserLogin, user_db: Users) -> bool:
    return pwd_context.verify(income_user.password, user_db.password_hash)

#Tokens
def create_token(data: dict) -> str:
    payload = data.copy()
    expiracion = datetime.now(timezone.utc) + timedelta(minutes=int(config.JWT_EXPIRE_MINUTES))
    payload["exp"] = expiracion
    token = jwt.encode(payload, config.JWT_CLAVE_INSTA_SECRETA, algorithm=config.ALGORITH)  # sin corchetes
    return token
    
def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, config.JWT_CLAVE_INSTA_SECRETA, algorithms=[config.ALGORITH])  # con corchetes
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail={"msg":"Credenciales erroneas"})
    
async def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db)
) -> Users:
    user_repo = UsersRepository(db)
    payload = decode_token(token.credentials)
    username = payload.get("sub")
    usuario = await user_repo.get_user_by_username(username)
    if not usuario:
        raise HTTPException(status_code=401, detail={"msg":"Credenciales erroneas"})
    return usuario

#Encriptar
def encrypt_key(texto_plano: str) -> str:
    return fernet.encrypt(texto_plano.encode()).decode()

def decode_key(texto_encriptado: str) -> str:
    return fernet.decrypt(texto_encriptado.encode()).decode()