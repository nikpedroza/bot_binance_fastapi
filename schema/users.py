from pydantic import BaseModel, ConfigDict
from typing import Optional, Literal
from datetime import datetime

Interval = Literal["1m", "5m", "15m", "30m", "1h", "4h"]

class ActivePositions(BaseModel):
    symbol: str
    en_posicion: bool
    type: str
    entrada: float
    cantidad: float
    cantidad_usdt: float
    isolated_margin: float
    leverage: int | None
    precio_actual: float
    pnl_usdt: float
    pnl_pct: float | None
    sl: float | None
    tp: float | None
    distancia_sl_pct: float | None
    distancia_tp_pct: float | None
    tiempo_entrada: datetime

class Status(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    username: str
    balance: float | None
    posiciones: Optional[list[ActivePositions]]