from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class ActivePositions(BaseModel):
    symbol: str
    en_posicion: bool
    type: str
    entrada: float
    cantidad: float
    cantidad_usdt: float
    sl: float
    tp: float
    tiempo_entrada: datetime

class Status(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    username: str 
    balance: float | None
    posiciones: Optional[list[ActivePositions]]
    