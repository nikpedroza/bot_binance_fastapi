from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext

from schema import UserLogin
from models import Users
from config import config

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(income_user: UserLogin, user_db: Users) -> bool:
    return pwd_context.verify(income_user.password, user_db.password_hash)

def crear_token(data: dict) -> str:
    payload = data.copy()
    expiracion = datetime.now(timezone.utc) + timedelta(minutes=config.JWT_EXPIRE_MINUTES)
    payload["exp"] = expiracion
    token = jwt.encode(payload, config.JWT_CLAVE_INSTA_SECRETA, algorithm=config.ALGORITH)
    return token