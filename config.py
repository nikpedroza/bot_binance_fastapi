from dotenv import load_dotenv
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "log")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_ERROR = os.path.join(LOG_DIR, "log_errores.log")

ENV_PATH = os.path.join(BASE_DIR, ".env")

class Config:
    def __init__(self):
        self.reload_config()
    
    def reload_config(self):
        load_dotenv(ENV_PATH, override=True)

    @property
    def BINANCE_API_KEY_PUBLIC(self):
        return os.getenv("BINANCE_APY_KEY_PUBLIC")
    
    @property
    def BINANCE_APY_KEY_PRIVATE(self):
        return os.getenv("BINANCE_APY_KEY_PRIVATE")
    
    @property
    def DATABASE_URL_SYNC(self):
        return os.getenv("DATABASE_URL_SYNC")
    
    @property
    def DATABASE_URL_ASYNC(self):
        return os.getenv("DATABASE_URL_ASYNC")
    
    @property
    def JWT_CLAVE_INSTA_SECRETA(self):
        return os.getenv("JWT_CLAVE_INSTA_SECRETA")
    
    @property
    def JWT_EXPIRE_MINUTES(self):
        return os.getenv("JWT_EXPIRE_MINUTES")
    
    @property
    def FERNET_KEY(self):
        return os.getenv("FERNET_KEY")

    @property
    def ALGORITH(self):
        return os.getenv("ALGORITH")

config = Config()