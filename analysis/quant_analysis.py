from datetime import datetime
import traceback
import pandas as pd
import numpy as np

from config import LOG_ERROR
from models import Trades


def analyze_bot(trades: list[Trades]) -> dict | None:
    try:
        records = []
        for t in trades:
            records.append({
                "symbol": t.symbol,
                "entrada": float(t.entrada) if t.entrada is not None else 0.0,
                "salida": float(t.salida) if t.salida is not None else 0.0,
                "tipo": t.tipo,
                "razon_salida": t.razon_salida,
                "pnl_neto": float(t.pnl_neto) if t.pnl_neto is not None else 0.0,
                "comision": float(t.comision) if t.comision is not None else 0.0,
                "funding_total": float(t.funding_total) if t.funding_total is not None else 0.0,
                "tiempo_entrada": t.tiempo_entrada,
                "tiempo_salida": t.tiempo_salida,
                "balance_acumulado": float(t.balance_acumulado) if t.balance_acumulado is not None else None,
                "strategy": t.strategy,
            })

        df = pd.DataFrame(records)

        df['tiempo_salida'] = pd.to_datetime(df['tiempo_salida'])
        df = df[df['tiempo_salida'].notna()].copy()
        df = df.sort_values('tiempo_salida').reset_index(drop=True)

        if df.empty:
            return None

        primer_trade = df.iloc[0]
        primer_balance = float(primer_trade['balance_acumulado']) if primer_trade['balance_acumulado'] is not None else 0.0
        primer_pnl = float(primer_trade['pnl_neto'])
        balance_inicial = primer_balance - primer_pnl
        balance_reconstruido = balance_inicial + df["pnl_neto"].cumsum()
        if balance_inicial <= 0:
            balance_inicial = primer_balance if primer_balance > 0 else 1.0

        if df['balance_acumulado'].notna().all():
            df['balance'] = df['balance_acumulado'].astype(float)
        else:
            df['balance'] = balance_reconstruido.astype(float)

        total_pnl = float(df['pnl_neto'].sum())
        total_days = int((df['tiempo_salida'].max() - df['tiempo_salida'].min()).days)
        years_factor = total_days / 365.25 if total_days > 0 else 1.0

        # 1. EXPECTANCY Y EDGE REAL
        wins = df[df['pnl_neto'] > 0]
        losses = df[df['pnl_neto'] <= 0]

        total_trades = len(df)
        win_rate = len(wins) / total_trades if total_trades > 0 else 0.0
        avg_win = float(wins['pnl_neto'].mean()) if len(wins) > 0 else 0.0
        avg_loss = abs(float(losses['pnl_neto'].mean())) if len(losses) > 0 else 0.0
        expectancy = (win_rate * avg_win) - ((1.0 - win_rate) * avg_loss)
        expectancy_anualizada = expectancy * (total_trades / years_factor) if years_factor > 0 else 0.0

        sum_losses = abs(float(losses['pnl_neto'].sum()))
        sum_wins = float(wins['pnl_neto'].sum())
        profit_factor = (sum_wins / sum_losses) if sum_losses != 0 else None
        reward_risk_ratio = (avg_win / avg_loss) if avg_loss != 0 else 0.0

        sorted_pnl = sorted(df['pnl_neto'].values, reverse=True)
        top_5_pct_idx = max(1, int(total_trades * 0.05))
        top_5_pnl = sum(sorted_pnl[:top_5_pct_idx])
        dependencia_top_5_pct = (top_5_pnl / total_pnl) * 100.0 if total_pnl != 0 else 0.0

        # 2. RENDIMIENTO POR CONFIGURACIÓN
        rendimiento_por_tipo = {}
        for t in df['tipo'].dropna().unique():
            sub = df[df['tipo'] == t]
            sub_pnl = float(sub['pnl_neto'].sum())
            sub_wr = len(sub[sub['pnl_neto'] > 0]) / len(sub) if len(sub) > 0 else 0.0
            rendimiento_por_tipo[str(t)] = {
                "pnl": round(sub_pnl, 2),
                "win_rate": round(sub_wr * 100.0, 2),
                "trades": int(len(sub))
            }

        rendimiento_por_razon_salida = {}
        for r in df['razon_salida'].dropna().unique():
            sub = df[df['razon_salida'] == r]
            avg_res = float(sub['pnl_neto'].mean()) if len(sub) > 0 else 0.0
            sub_pnl = float(sub['pnl_neto'].sum())
            rendimiento_por_razon_salida[str(r)] = {
                "avg_pnl": round(avg_res, 2),
                "total_pnl": round(sub_pnl, 2),
                "trades": int(len(sub))
            }

        # 3. DRAWDOWN Y RECUPERACIÓN
        df['peak'] = df['balance'].cummax()
        df['drawdown_usd'] = df['balance'] - df['peak']
        df['drawdown_pct'] = np.where(df['peak'] > 0, (df['balance'] - df['peak']) / df['peak'], 0.0)

        balance_curve = [
            {
                "fecha": row['tiempo_salida'].strftime('%Y-%m-%d'),
                "balance": round(float(row['balance']), 2)
            }
            for _, row in df.iterrows()
        ]
        max_dd_usd = float(df['drawdown_usd'].min())
        max_dd_pct = float(df['drawdown_pct'].min() * 100.0)
        recovery_factor = (total_pnl / abs(max_dd_usd)) if max_dd_usd != 0 else 0.0

        df['underwater'] = df['drawdown_usd'] < 0
        streaks_uw = []
        count = 0
        for val in df['underwater']:
            if val:
                count += 1
            else:
                if count > 0:
                    streaks_uw.append(count)
                count = 0
        if count > 0:
            streaks_uw.append(count)

        promedio_trades_recuperacion = float(np.mean(streaks_uw)) if streaks_uw else 0.0
        max_trades_estancado = int(np.max(streaks_uw)) if streaks_uw else 0

        # 4. ANÁLISIS DE RACHAS (STREAKS)
        def get_max_streak(pnls, positive=True):
            max_s = 0
            curr_s = 0
            for p in pnls:
                if (p > 0 if positive else p <= 0):
                    curr_s += 1
                    max_s = max(max_s, curr_s)
                else:
                    curr_s = 0
            return max_s

        max_racha_ganadora = get_max_streak(df['pnl_neto'], True)
        max_racha_perdedora = get_max_streak(df['pnl_neto'], False)

        # 5. RATIOS DE EFICIENCIA
        daily_returns = df.groupby(df['tiempo_salida'].dt.date)['pnl_neto'].sum() / balance_inicial
        ann_return = (total_pnl / balance_inicial) / years_factor if years_factor > 0 else 0.0

        ann_vol_crypto = None
        sharpe_ann = None
        if total_days > 30 and len(daily_returns) > 1:
            vol = float(daily_returns.std() * np.sqrt(365))
            if not np.isnan(vol):
                ann_vol_crypto = round(vol * 100.0, 2)
                if vol != 0:
                    sharpe_ann = round(ann_return / vol, 2)

        std_pnl = float(df['pnl_neto'].std())
        sqn = (np.sqrt(total_trades) * float(df['pnl_neto'].mean()) / std_pnl) if (std_pnl != 0 and not np.isnan(std_pnl)) else 0.0

        # 6. ANÁLISIS TEMPORAL
        df['hour'] = df['tiempo_salida'].dt.hour
        df['day'] = df['tiempo_salida'].dt.dayofweek

        hour_pnl = df.groupby('hour')['pnl_neto'].sum()
        best_hour = int(hour_pnl.idxmax()) if not hour_pnl.empty else None
        worst_hour = int(hour_pnl.idxmin()) if not hour_pnl.empty else None

        day_names = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        day_pnl = df.groupby('day')['pnl_neto'].sum()
        best_day = day_names[int(day_pnl.idxmax())] if not day_pnl.empty else None

        # 7. COSTOS DE OPERACIÓN
        gross_profit = sum_wins
        total_fees = float(df['comision'].sum())
        impacto_comisiones = (total_fees / gross_profit) * 100.0 if gross_profit > 0 else 0.0

        # 8. RENDIMIENTO MENSUAL
        df['month'] = df['tiempo_salida'].dt.month
        df['year'] = df['tiempo_salida'].dt.year
        monthly_pnl = df.groupby(['year', 'month'])['pnl_neto'].sum().reset_index()
        rendimiento_mensual = [
            {
                "year": int(row['year']),
                "month": int(row['month']),
                "pnl_pct": round(float((row['pnl_neto'] / balance_inicial) * 100.0), 2)
            }
            for _, row in monthly_pnl.iterrows()
        ]

        # DICCIONARIO DE RESULTADOS CON CLAVES DE ANÁLISIS
        report = {
            "periodo": {
                "fecha_inicio": df['tiempo_salida'].min().strftime('%Y-%m-%d'),
                "fecha_fin": df['tiempo_salida'].max().strftime('%Y-%m-%d'),
                "total_dias": total_days,
            },
            "balance_inicial": round(balance_inicial, 2),
            "total_trades": total_trades,
            "total_pnl": round(total_pnl, 2),
            "win_rate": round(win_rate * 100.0, 2),
            "trades_ganadores": int(len(wins)),
            "trades_perdedores": int(len(losses)),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "expectancy": round(expectancy, 2),
            "expectancy_anualizada": round(expectancy_anualizada, 2),
            "profit_factor": round(profit_factor, 2) if (profit_factor is not None and profit_factor != float('inf')) else None,
            "reward_risk_ratio": round(reward_risk_ratio, 2),
            "dependencia_top_5_pct": round(dependencia_top_5_pct, 2),
            "rendimiento_por_tipo": rendimiento_por_tipo,
            "rendimiento_por_razon_salida": rendimiento_por_razon_salida,
            "max_drawdown_usd": round(max_dd_usd, 2),
            "max_drawdown_pct": round(max_dd_pct, 2),
            "recovery_factor": round(recovery_factor, 2),
            "promedio_trades_recuperacion": round(promedio_trades_recuperacion, 1),
            "max_trades_estancado": max_trades_estancado,
            "max_racha_ganadora": int(max_racha_ganadora),
            "max_racha_perdedora": int(max_racha_perdedora),
            "retorno_anualizado": round(ann_return * 100.0, 2),
            "volatilidad_anualizada": ann_vol_crypto,
            "sharpe_ratio": sharpe_ann,
            "system_quality_number": round(sqn, 2),
            "mejor_hora_cierre": best_hour,
            "peor_hora_cierre": worst_hour,
            "mejor_dia_semana": best_day,
            "comisiones_totales": round(total_fees, 2),
            "impacto_comisiones": round(impacto_comisiones, 2),
            "rendimiento_mensual": rendimiento_mensual,
            "balance_curve": balance_curve
        }

        return report

    except Exception as e:
        msg = f"Error al generar reporte de análisis: {e}"
        print(f"[ERROR] {msg}")
        with open(LOG_ERROR, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] [quant_analysis] {msg}\n{traceback.format_exc()}\n")
        return None
