from pydantic import BaseModel, ConfigDict
from datetime import datetime

class TradesSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    strategy: str
    tiempo_entrada: datetime | None
    tiempo_salida: datetime | None
    entrada: float
    salida: float
    tipo: str
    razon_salida: str | None
    comision: float | None
    funding_total : float | None
    pnl_neto: float
    balance_acumulado: float | None

class PaginatedTrades(BaseModel):
    data: list[TradesSchema]
    total: int
    page: int
    page_size: int
    total_pages: int