from binance.client import Client
from binance.exceptions import BinanceAPIException
from datetime import datetime
import traceback
import pandas as pd

from config import LOG_ERROR

class BinanceAdmin():
    def __init__(self, username, api_key_public, api_key_secret):
        self.username = username
        self.client = Client(api_key_public, api_key_secret)

    def _manejar_error_api(self, e, contexto: str):
        if hasattr(e, 'code') and e.code == -2015:
            msg = f"Error -2015 (IP cambió o key revocada) en {contexto}."
            print(msg)
            with open(LOG_ERROR, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now()}] [{self.username}] {msg}\n{traceback.format_exc()}\n")
            raise e
    
    def _buscar_sl_tp_activos(self, symbol: str) -> tuple[float | None, float | None]:
        sl, tp = None, None
        try:
            ordenes = self.client.futures_get_open_algo_orders(symbol=symbol)
            for o in ordenes:
                if o.get("orderType") == "STOP_MARKET":
                    sl = float(o["triggerPrice"])
                elif o.get("orderType") == "TAKE_PROFIT_MARKET":
                    tp = float(o["triggerPrice"])
        except Exception as e:
            print(f"Error al buscar SL/TP activos: {e}")
        return sl, tp

    def get_balance_futuros(self) -> float | None:
        try:
            balances = self.client.futures_account_balance()
            for asset in balances:
                if asset["asset"] == "USDT":
                    disponible = float(asset["availableBalance"])
                    return disponible
            print("No se encontró balance USDT en futuros.")
            return None
        except BinanceAPIException as e:
            if e.code == -2015:
                self._manejar_error_api(e, "get_balance_futuros")
            print(f"✗ Error al obtener balance de futuros: {e}")

    def get_posicion_activa(self, symbol: str) -> dict | None:
        try:
            posiciones = self.client.futures_position_information(symbol=symbol)
            for pos in posiciones:
                amt = float(pos["positionAmt"])
                if amt != 0.0:
                    tipo = "LONG" if amt > 0 else "SHORT"
                    entrada = float(pos["entryPrice"])
                    sl, tp = self._buscar_sl_tp_activos(symbol)

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
                    except Exception as e:
                        print(f"No se pudo reconstruir tiempo_entrada de posición recuperada: {e}")

                    return {
                        "en_posicion": True,
                        "type": tipo,
                        "entrada": entrada,
                        "cantidad_btc": abs(amt),
                        "cantidad_usdt": abs(amt) * entrada,
                        "sl": sl,
                        "tp": tp,
                        "tiempo_entrada": tiempo_entrada,
                    }
            return None
        except BinanceAPIException as e:
            if e.code == -2015:
                self._manejar_error_api(e, "get_posicion_activa")
            print(f"Error al consultar posición activa: {e}")
            return None       
    