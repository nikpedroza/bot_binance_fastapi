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

class PeriodoAnalysis(BaseModel):
    fecha_inicio: str | None
    fecha_fin: str | None
    total_dias: int

class RendimientoTipo(BaseModel):
    pnl: float
    win_rate: float
    trades: int

class RendimientoRazonSalida(BaseModel):
    avg_pnl: float
    total_pnl: float
    trades: int

class RendimientoMensual(BaseModel):
    year: int
    month: int
    pnl_pct: float

class BalanceCurve(BaseModel):
    fecha: str
    balance: float

class TradesAnalysis(BaseModel):
    periodo: PeriodoAnalysis
    balance_inicial: float
    total_trades: int
    total_pnl: float
    win_rate: float
    trades_ganadores: int
    trades_perdedores: int
    avg_win: float
    avg_loss: float
    expectancy: float
    expectancy_anualizada: float
    profit_factor: float | None = None
    reward_risk_ratio: float
    dependencia_top_5_pct: float
    rendimiento_por_tipo: dict[str, RendimientoTipo]
    rendimiento_por_razon_salida: dict[str, RendimientoRazonSalida]
    max_drawdown_usd: float
    max_drawdown_pct: float
    recovery_factor: float
    promedio_trades_recuperacion: float
    max_trades_estancado: int
    max_racha_ganadora: int
    max_racha_perdedora: int
    retorno_anualizado: float
    volatilidad_anualizada: float | None = None
    sharpe_ratio: float | None = None
    system_quality_number: float
    mejor_hora_cierre: int | None = None
    peor_hora_cierre: int | None = None
    mejor_dia_semana: str | None = None
    comisiones_totales: float
    impacto_comisiones: float
    rendimiento_mensual: list[RendimientoMensual]
    balance_curve: list[BalanceCurve]