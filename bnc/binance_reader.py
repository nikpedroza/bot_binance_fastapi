from binance.client import Client
from binance.exceptions import BinanceAPIException
from datetime import datetime, timezone, timedelta
import pandas as pd
import logging

logger = logging.getLogger(__name__)

POSICIONES_CACHE = {}

class BinanceConnectionError(Exception):
    pass

class BinanceAdmin():
    def __init__(self, username, api_key_public, api_key_secret):
        self.username = username
        self.client = Client(api_key_public, api_key_secret)

    def _buscar_sl_tp_activos(self, symbol: str) -> tuple[float | None, float | None]:
        sl, tp = None, None
        try:
            ordenes = self.client.futures_get_open_algo_orders(symbol=symbol)
            for o in ordenes:
                if o.get("orderType") == "STOP_MARKET":
                    sl = float(o["triggerPrice"])
                elif o.get("orderType") == "TAKE_PROFIT_MARKET":
                    tp = float(o["triggerPrice"])
        except Exception:
            logger.error("Error al buscar SL/TP activos", exc_info=True)
        return sl, tp

    def get_balance_futuros(self) -> float | None:
        try:
            balances = self.client.futures_account_balance()
            for asset in balances:
                if asset["asset"] == "USDT":
                    disponible = float(asset["availableBalance"])
                    return disponible
            logger.warning("No se encontro balance USDT en futuros.")
            return None
        except BinanceAPIException as e:
            logger.error("Error al obtener balance de futuros",exc_info=True)
            raise BinanceConnectionError("No se pudo obtener el balance de Binance") from e

    def get_posiciones_activas(self) -> list[dict]:
        global POSICIONES_CACHE
        user_cacheado = POSICIONES_CACHE.get(self.username, {})
        posiciones_abiertas = []
        try:
            posiciones = self.client.futures_position_information()
            for pos in posiciones:
                amt = float(pos["positionAmt"])
                if amt == 0.0:
                    continue

                symbol = pos["symbol"]
                tipo = "LONG" if amt > 0 else "SHORT"
                entrada = float(pos["entryPrice"])
                precio_actual = float(pos["markPrice"])
                pnl_usdt = float(pos["unRealizedProfit"])
                notional = abs(float(pos["notional"]))
                isolated_margin = float(pos.get("isolatedMargin", 0) or 0)

                leverage = round(notional / isolated_margin) if isolated_margin > 0 else None
                pnl_pct = (pnl_usdt / isolated_margin) * 100.0 if isolated_margin > 0 else None

                distancia_sl_pct = None
                distancia_tp_pct = None
                symbol_cacheado = user_cacheado.get(symbol, {})

                if symbol_cacheado and datetime.now(timezone.utc) - (symbol_cacheado.get("last_update") or datetime.min) < timedelta(seconds=30):
                    sl = symbol_cacheado.get("sl")
                    tp = symbol_cacheado.get("tp")
                    tiempo_entrada = symbol_cacheado.get("tiempo_entrada")
                    direccion = 1 if tipo == "LONG" else -1
                    if sl is not None and precio_actual != 0:
                        distancia_sl_pct = ((precio_actual - sl) / precio_actual) * 100.0 * direccion
                    if tp is not None and precio_actual != 0:
                        distancia_tp_pct = ((tp - precio_actual) / precio_actual) * 100.0 * direccion
                else:
                    sl, tp = self._buscar_sl_tp_activos(symbol)

                    direccion = 1 if tipo == "LONG" else -1
                    if sl is not None and precio_actual != 0:
                        distancia_sl_pct = ((precio_actual - sl) / precio_actual) * 100.0 * direccion
                    if tp is not None and precio_actual != 0:
                        distancia_tp_pct = ((tp - precio_actual) / precio_actual) * 100.0 * direccion

                    tiempo_entrada = None
                    try:
                        side_esperado = "BUY" if tipo == "LONG" else "SELL"
                        trades = self.client.futures_account_trades(symbol=symbol, limit=50)
                        idx_ultimo_cierre = -1
                        for i, t in enumerate(trades):
                            if float(t["realizedPnl"]) != 0.0:
                                idx_ultimo_cierre = i
                        trades_pos_actual = trades[idx_ultimo_cierre + 1:] if idx_ultimo_cierre != -1 else trades
                        candidatos = [t for t in trades_pos_actual if t["side"] == side_esperado and float(t["realizedPnl"]) == 0.0]
                        if candidatos:
                            mas_antiguo = min(candidatos, key=lambda t: t["time"])
                            tiempo_entrada = pd.to_datetime(int(mas_antiguo["time"]), unit="ms")
                    except Exception:
                        logger.error("No se pudo reconstruir tiempo_entrada de posición recuperada", exc_info=True)

                    POSICIONES_CACHE.setdefault(self.username, {})
                    POSICIONES_CACHE[self.username][symbol] = {
                        "sl": sl,
                        "tp": tp,
                        "tiempo_entrada": tiempo_entrada,
                        "last_update": datetime.now(timezone.utc)
                    }

                posiciones_abiertas.append({
                    "symbol": symbol,
                    "en_posicion": True,
                    "type": tipo,
                    "entrada": entrada,
                    "cantidad": abs(amt),
                    "cantidad_usdt": round(abs(amt) * entrada, 2),
                    "leverage": leverage,
                    "isolated_margin": round(isolated_margin, 2),
                    "precio_actual": precio_actual,
                    "pnl_usdt": round(pnl_usdt, 2),
                    "pnl_pct": round(pnl_pct, 2) if pnl_pct is not None else None,
                    "sl": sl,
                    "tp": tp,
                    "distancia_sl_pct": round(distancia_sl_pct, 2) if distancia_sl_pct is not None else None,
                    "distancia_tp_pct": round(distancia_tp_pct, 2) if distancia_tp_pct is not None else None,
                    "tiempo_entrada": tiempo_entrada,
                })

            return posiciones_abiertas

        except BinanceAPIException as e:
            logger.error("Error al consultar posiciones activas", exc_info=True)
            raise BinanceConnectionError("No se pudieron obtener las posiciones de Binance") from e