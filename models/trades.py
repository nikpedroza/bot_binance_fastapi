from sqlalchemy import Column, String, TIMESTAMP, ForeignKey, Numeric, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from database import Base

class Trades(Base):
    __tablename__ = "trades"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    entrada = Column(Numeric, nullable=False)
    salida = Column(Numeric, nullable=False)
    tipo = Column(String(10), nullable=False)
    razon_salida = Column(String(50))
    pnl_neto = Column(Numeric, nullable=False)
    comision = Column(Numeric)
    funding_total = Column(Numeric)
    tiempo_entrada = Column(TIMESTAMP(timezone=False))
    tiempo_salida = Column(TIMESTAMP(timezone=False))
    balance_acumulado = Column(Numeric)
    strategy = Column(String(10), nullable=False)

    order_id_market = Column(BigInteger)
    order_id_sl = Column(BigInteger)
    order_id_tp = Column(BigInteger)

    created_at = Column(TIMESTAMP(timezone=False), server_default=func.now())