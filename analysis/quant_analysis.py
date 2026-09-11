from datetime import datetime, date
import io
import logging
import pandas as pd
import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from models import Trades

logger = logging.getLogger(__name__)

#Armador de Dataframe default para reuso
def trades_to_records(trades: list[Trades]) -> list[dict]:
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
    return records

#ENDPOINT /analysis
def analyze_bot(trades: list[Trades]) -> dict | None:
    try:
        records = trades_to_records(trades)
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

        drawdown_curve = [
            {
                "fecha": row['tiempo_salida'].strftime('%Y-%m-%d'),
                "drawdown_pct": round(float(row['drawdown_pct']) * 100.0, 2)
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

        # ROLLING PROFIT FACTOR & EXPECTANCY
        ROLLING_WINDOW = 20  #Ajustar a 50 una vez tengamos minimo 50trades
        pos_pnl = df['pnl_neto'].apply(lambda x: x if x > 0 else 0.0)
        neg_pnl = df['pnl_neto'].apply(lambda x: abs(x) if x < 0 else 0.0)

        roll_pos = pos_pnl.rolling(window=ROLLING_WINDOW, min_periods=1).sum()
        roll_neg = neg_pnl.rolling(window=ROLLING_WINDOW, min_periods=1).sum()

        rolling_pf_series = pd.Series(np.nan, index=df.index)
        valid_loss = roll_neg > 0
        rolling_pf_series[valid_loss] = roll_pos[valid_loss] / roll_neg[valid_loss]

        rolling_exp_series = df['pnl_neto'].rolling(window=ROLLING_WINDOW, min_periods=1).mean()

        rolling_metrics = [
            {
                "trade_num": i + 1,
                "fecha": row['tiempo_salida'].strftime('%Y-%m-%d'),
                "rolling_pf": round(float(rolling_pf_series.iloc[i]), 2) if not pd.isna(rolling_pf_series.iloc[i]) else None,
                "rolling_expectancy": round(float(rolling_exp_series.iloc[i]), 2)
            }
            for i, (_, row) in enumerate(df.iterrows())
        ]

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
            "balance_curve": balance_curve,
            "drawdown_curve": drawdown_curve,
            "rolling_metrics": rolling_metrics
        }

        return report

    except Exception as e:
        logger.error(f"Error al generar reporte de analisis: {e}", exc_info=True)
        return None

# ENDPOINT /photo
def generate_analysis_photo(trades: list[Trades], rolling_window: int = 50, dpi: int = 150) -> io.BytesIO | None:
    try:
        df = preparar_datos_dashboard(trades)
        if df is None or df.empty:
            return None

        m = calcular_metricas(df)
        return generar_dashboard(df, m, rolling_window=rolling_window, dpi=dpi)
    except Exception as e:
        logger.error(f"Error al generar foto de análisis: {e}", exc_info=True)
        return None

def preparar_datos_dashboard(trades: list[Trades]) -> pd.DataFrame | None:
    """Prepara y normaliza los trades obtenidos desde la base de datos."""
    if not trades:
        return None

    records = trades_to_records(trades)
    df = pd.DataFrame(records)
    if df.empty:
        return None

    df['tiempo_entrada'] = pd.to_datetime(df['tiempo_entrada'], errors='coerce')
    df['tiempo_salida'] = pd.to_datetime(df['tiempo_salida'], errors='coerce')

    if getattr(df['tiempo_entrada'].dt, 'tz', None) is not None:
        df['tiempo_entrada'] = df['tiempo_entrada'].dt.tz_localize(None)
    if getattr(df['tiempo_salida'].dt, 'tz', None) is not None:
        df['tiempo_salida'] = df['tiempo_salida'].dt.tz_localize(None)

    df['pnl_neto'] = pd.to_numeric(df['pnl_neto'], errors='coerce').fillna(0.0)
    df['comision'] = pd.to_numeric(df['comision'], errors='coerce').fillna(0.0)
    df['funding_total'] = pd.to_numeric(df['funding_total'], errors='coerce').fillna(0.0)
    df['tipo'] = df['tipo'].fillna('DESCONOCIDO').astype(str).str.upper()
    df['razon_salida'] = df['razon_salida'].fillna('N/A').astype(str)
    df['strategy'] = df['strategy'].fillna('General').astype(str)

    df = df.dropna(subset=['tiempo_salida', 'tiempo_entrada']).copy()
    if df.empty:
        return None

    df = df.sort_values('tiempo_salida').reset_index(drop=True)

    # Reconstruir balance_acumulado si falta
    primer_trade = df.iloc[0]
    primer_balance = float(primer_trade['balance_acumulado']) if pd.notna(primer_trade['balance_acumulado']) else 0.0
    primer_pnl = float(primer_trade['pnl_neto'])
    balance_inicial = primer_balance - primer_pnl
    if balance_inicial <= 0:
        balance_inicial = primer_balance if primer_balance > 0 else 1000.0

    balance_reconstruido = balance_inicial + df['pnl_neto'].cumsum()

    if df['balance_acumulado'].notna().all():
        df['balance_acumulado'] = df['balance_acumulado'].astype(float)
    else:
        df['balance_acumulado'] = balance_reconstruido.astype(float)

    return df

def calcular_metricas(df: pd.DataFrame) -> dict:
    """Calcula las métricas financieras necesarias para el reporte."""
    total_trades = len(df)
    wins = df[df['pnl_neto'] > 0]
    losses = df[df['pnl_neto'] < 0]
    breakevens = df[df['pnl_neto'] == 0]

    num_wins = len(wins)
    num_losses = len(losses)
    num_be = len(breakevens)

    win_rate = (num_wins / total_trades * 100.0) if total_trades > 0 else 0.0

    gross_profit = float(wins['pnl_neto'].sum())
    gross_loss = float(abs(losses['pnl_neto'].sum()))
    pnl_neto_total = float(df['pnl_neto'].sum())

    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (float('inf') if gross_profit > 0 else 0.0)

    # Drawdowns
    df_salida = df.sort_values('tiempo_salida').copy()
    peak = df_salida['balance_acumulado'].cummax()
    dd_dollar_series = peak - df_salida['balance_acumulado']
    max_dd_dollar = float(dd_dollar_series.max()) if not dd_dollar_series.empty else 0.0

    safe_peak = peak.replace(0, np.nan)
    dd_pct_series = ((df_salida['balance_acumulado'] - peak) / safe_peak) * 100.0
    max_dd_pct = float(dd_pct_series.fillna(0.0).min()) if not dd_pct_series.empty else 0.0

    recovery_factor = (pnl_neto_total / max_dd_dollar) if max_dd_dollar > 0 else (float('inf') if pnl_neto_total > 0 else 0.0)

    longs = df[df['tipo'] == 'LONG']
    shorts = df[df['tipo'] == 'SHORT']

    win_rate_long = (len(longs[longs['pnl_neto'] > 0]) / len(longs) * 100.0) if len(longs) > 0 else 0.0
    win_rate_short = (len(shorts[shorts['pnl_neto'] > 0]) / len(shorts) * 100.0) if len(shorts) > 0 else 0.0

    pnl_long = float(longs['pnl_neto'].sum())
    pnl_short = float(shorts['pnl_neto'].sum())

    avg_win = float(wins['pnl_neto'].mean()) if num_wins > 0 else 0.0
    avg_loss = float(losses['pnl_neto'].mean()) if num_losses > 0 else 0.0

    mejor_trade = float(df['pnl_neto'].max()) if total_trades > 0 else 0.0
    peor_trade = float(df['pnl_neto'].min()) if total_trades > 0 else 0.0

    # Rachas consecutivas
    df_entrada = df.sort_values('tiempo_entrada').reset_index(drop=True)
    win_streaks, loss_streaks = [], []
    curr_w, curr_l = 0, 0

    pnl_array = df_entrada['pnl_neto'].to_numpy()
    for pnl in pnl_array:
        if pnl > 0:
            if curr_l > 0:
                loss_streaks.append(curr_l)
                curr_l = 0
            curr_w += 1
        elif pnl < 0:
            if curr_w > 0:
                win_streaks.append(curr_w)
                curr_w = 0
            curr_l += 1

    if curr_w > 0:
        win_streaks.append(curr_w)
    if curr_l > 0:
        loss_streaks.append(curr_l)

    max_win_streak = max(win_streaks) if win_streaks else 0
    max_loss_streak = max(loss_streaks) if loss_streaks else 0
    avg_win_streak = float(np.mean(win_streaks)) if win_streaks else 0.0
    avg_loss_streak = float(np.mean(loss_streaks)) if loss_streaks else 0.0

    return {
        'total_trades': total_trades,
        'num_wins': num_wins,
        'num_losses': num_losses,
        'num_be': num_be,
        'win_rate': win_rate,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'pnl_neto_total': pnl_neto_total,
        'profit_factor': profit_factor,
        'max_dd_pct': max_dd_pct,
        'max_dd_dollar': max_dd_dollar,
        'recovery_factor': recovery_factor,
        'win_rate_long': win_rate_long,
        'win_rate_short': win_rate_short,
        'pnl_long': pnl_long,
        'pnl_short': pnl_short,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'mejor_trade': mejor_trade,
        'peor_trade': peor_trade,
        'avg_win_streak': avg_win_streak,
        'avg_loss_streak': avg_loss_streak,
        'max_win_streak': max_win_streak,
        'max_loss_streak': max_loss_streak,
        'comisiones_totales': float(df['comision'].sum()),
        'funding_total': float(df['funding_total'].sum()),
        'balance_inicial': float(df_salida['balance_acumulado'].iloc[0] - df_salida['pnl_neto'].iloc[0]),
        'balance_final': float(df_salida['balance_acumulado'].iloc[-1])
    }

def render_metrica_una_linea(ax, x_center, y, label, val_str, val_color='#0f172a'):
    """
    Renderiza la etiqueta y el valor en UNA SOLA LÍNEA HORIZONTAL (ej: "Profit: $1234")
    manteniendo la etiqueta en gris y el valor destacado con color.
    """
    offset_x = 0.003
    ax.text(x_center - offset_x, y, f"{label}: ", ha='right', va='center', fontsize=8.8, fontweight='bold', color='#475569', transform=ax.transData)
    ax.text(x_center + offset_x, y, val_str, ha='left', va='center', fontsize=9.2, fontweight='bold', color=val_color, transform=ax.transData)

def generar_dashboard(df: pd.DataFrame, m: dict, rolling_window: int = 50, dpi: int = 150) -> io.BytesIO:
    """Genera el reporte y lo devuelve como buffer en memoria BytesIO optimizado."""
    
    COLOR_BG = '#ffffff'          # Blanco puro
    COLOR_TEXT_MAIN = '#0f172a'   # Texto principal slate
    COLOR_TEXT_MUTED = '#64748b'  # Texto secundario
    COLOR_GRID = '#e2e8f0'        # Rejilla
    COLOR_BORDER = '#cbd5e1'      # Bordes de ejes

    COLOR_GREEN = '#15803d'       # Verde ganancia
    COLOR_RED = '#b91c1c'         # Rojo pérdida
    COLOR_BLUE = '#2563eb'        # Azul balance
    COLOR_PURPLE = '#7c3aed'      # Púrpura rolling PF
    COLOR_AMBER = '#d97706'       # Ámbar rolling Expectancy

    plt.style.use('default')
    fig = plt.figure(figsize=(16, 15), facecolor=COLOR_BG)

    # Título principal y subtítulo
    today_str = date.today().strftime('%Y-%m-%d')
    sub_info = f"Reporte de Trades | Generado: {today_str} | Total Trades: {m['total_trades']} | Balance Final: ${m['balance_final']:,.2f} USDT"
    fig.text(0.5, 0.970, sub_info, ha='center', fontsize=10, color=COLOR_TEXT_MUTED, fontweight='bold')

    # Grilla de subplots (GridSpec)
    gs = fig.add_gridspec(4, 2, height_ratios=[1.4, 2.4, 2.0, 2.4], top=0.94, bottom=0.035, left=0.04, right=0.96, hspace=0.35, wspace=0.22)

    # -------------------------------------------------------------
    # FILA 0: Métricas en UNA SOLA LÍNEA
    # -------------------------------------------------------------
    ax_metrics = fig.add_subplot(gs[0, :])
    ax_metrics.set_facecolor(COLOR_BG)
    ax_metrics.set_axis_off()
    ax_metrics.set_xlim(0, 1)
    ax_metrics.set_ylim(0, 1)

    fmt_pnl = lambda v: f"${v:+,.2f}"
    fmt_color = lambda v: COLOR_GREEN if v > 0 else (COLOR_RED if v < 0 else COLOR_TEXT_MAIN)

    pf_str = f"{m['profit_factor']:.2f}" if m['profit_factor'] != float('inf') else "Inf"
    rec_str = f"{m['recovery_factor']:.2f}" if m['recovery_factor'] != float('inf') else "Inf"

    row_a = [
        ("PnL Neto", fmt_pnl(m['pnl_neto_total']), fmt_color(m['pnl_neto_total'])),
        ("Profit Bruto", fmt_pnl(m['gross_profit']), COLOR_GREEN),
        ("Pérdida Bruta", f"-${m['gross_loss']:,.2f}", COLOR_RED),
        ("Profit Factor", pf_str, COLOR_TEXT_MAIN),
        ("Recovery Factor", rec_str, COLOR_TEXT_MAIN),
        ("Total Trades", f"{m['total_trades']}", COLOR_TEXT_MAIN),
    ]

    row_b = [
        ("Max DD %", f"{m['max_dd_pct']:.2f}%", COLOR_RED),
        ("Max DD $", f"-${m['max_dd_dollar']:,.2f}", COLOR_RED),
        ("Win Rate LONG", f"{m['win_rate_long']:.1f}%", COLOR_TEXT_MAIN),
        ("Win Rate SHORT", f"{m['win_rate_short']:.1f}%", COLOR_TEXT_MAIN),
        ("PnL LONG", fmt_pnl(m['pnl_long']), fmt_color(m['pnl_long'])),
        ("PnL SHORT", fmt_pnl(m['pnl_short']), fmt_color(m['pnl_short'])),
    ]

    row_c = [
        ("Ganancia Prom.", fmt_pnl(m['avg_win']), COLOR_GREEN),
        ("Pérdida Prom.", fmt_pnl(m['avg_loss']), COLOR_RED),
        ("Mejor Trade", fmt_pnl(m['mejor_trade']), COLOR_GREEN),
        ("Peor Trade", fmt_pnl(m['peor_trade']), COLOR_RED),
        ("Comisiones", f"-${m['comisiones_totales']:,.2f}", COLOR_RED),
        ("Funding", fmt_pnl(m['funding_total']), fmt_color(m['funding_total'])),
    ]

    row_d = [
        ("Racha Gan. Prom.", f"{m['avg_win_streak']:.1f} trades", COLOR_TEXT_MAIN),
        ("Racha Perd. Prom.", f"{m['avg_loss_streak']:.1f} trades", COLOR_TEXT_MAIN),
        ("Máx Racha Gan.", f"{m['max_win_streak']} trades", COLOR_GREEN),
        ("Máx Racha Perd.", f"{m['max_loss_streak']} trades", COLOR_RED),
    ]

    w_6 = 1.0 / 6.0
    x_pos_6 = [(i + 0.5) * w_6 for i in range(6)]

    y_a = 0.88
    for i, (t, v, c) in enumerate(row_a):
        render_metrica_una_linea(ax_metrics, x_pos_6[i], y_a, t, v, c)

    y_b = 0.63
    for i, (t, v, c) in enumerate(row_b):
        render_metrica_una_linea(ax_metrics, x_pos_6[i], y_b, t, v, c)

    w_4 = 1.0 / 4.0
    x_pos_4 = [(i + 0.5) * w_4 for i in range(4)]

    y_c = 0.38
    for i, (t, v, c) in enumerate(row_c):
        render_metrica_una_linea(ax_metrics, x_pos_6[i], y_c, t, v, c)

    y_d = 0.13
    for i, (t, v, c) in enumerate(row_d):
        render_metrica_una_linea(ax_metrics, x_pos_4[i], y_d, t, v, c)

    # -------------------------------------------------------------
    # FILA 1: Balance Acumulado en el Tiempo
    # -------------------------------------------------------------
    ax1 = fig.add_subplot(gs[1, :])
    ax1.set_facecolor(COLOR_BG)
    ax1.grid(True, linestyle='--', alpha=0.5, color=COLOR_GRID)
    for spine in ax1.spines.values():
        spine.set_color(COLOR_BORDER)

    # df ya viene ordenado por tiempo_salida
    df_sorted_salida = df
    ax1.plot(df_sorted_salida['tiempo_salida'], df_sorted_salida['balance_acumulado'], color=COLOR_BLUE, linewidth=2.2)
    
    min_bal = df_sorted_salida['balance_acumulado'].min()
    ax1.fill_between(df_sorted_salida['tiempo_salida'], df_sorted_salida['balance_acumulado'], 
                     min_bal * 0.998 if min_bal > 0 else 0, color=COLOR_BLUE, alpha=0.10)

    ax1.set_title('1. Balance Acumulado en el Tiempo (USDT)', fontsize=12, fontweight='bold', color=COLOR_TEXT_MAIN, pad=8, loc='left')
    ax1.set_ylabel('Balance (USDT)', color=COLOR_TEXT_MAIN, fontsize=9.5, fontweight='bold')
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax1.tick_params(colors=COLOR_TEXT_MAIN, labelsize=9)

    bal_ini = df_sorted_salida['balance_acumulado'].iloc[0] - df_sorted_salida['pnl_neto'].iloc[0]
    bal_fin = df_sorted_salida['balance_acumulado'].iloc[-1]
    ax1.annotate(f'Inicial: ${bal_ini:,.2f}', xy=(0.015, 0.85), xycoords='axes fraction',
                 fontsize=8.5, fontweight='bold', color=COLOR_TEXT_MAIN,
                 bbox=dict(boxstyle='round,pad=0.3', facecolor=COLOR_BG, edgecolor=COLOR_BORDER, alpha=0.9))
    ax1.annotate(f'Final: ${bal_fin:,.2f}', xy=(0.87, 0.85), xycoords='axes fraction',
                 fontsize=8.5, fontweight='bold', color=COLOR_BLUE,
                 bbox=dict(boxstyle='round,pad=0.3', facecolor=COLOR_BG, edgecolor=COLOR_BLUE, alpha=0.9))

    # -------------------------------------------------------------
    # FILA 2: Curva de Drawdown (%)
    # -------------------------------------------------------------
    ax2 = fig.add_subplot(gs[2, :])
    ax2.set_facecolor(COLOR_BG)
    ax2.grid(True, linestyle='--', alpha=0.5, color=COLOR_GRID)
    for spine in ax2.spines.values():
        spine.set_color(COLOR_BORDER)

    peak = df_sorted_salida['balance_acumulado'].cummax()
    safe_peak = peak.replace(0, np.nan)
    drawdown_pct = ((df_sorted_salida['balance_acumulado'] - peak) / safe_peak) * 100.0
    drawdown_pct = drawdown_pct.fillna(0.0)

    ax2.plot(df_sorted_salida['tiempo_salida'], drawdown_pct, color=COLOR_RED, linewidth=1.8)
    ax2.fill_between(df_sorted_salida['tiempo_salida'], drawdown_pct, 0, color=COLOR_RED, alpha=0.15)

    ax2.set_title('2. Curva de Drawdown (%)', fontsize=12, fontweight='bold', color=COLOR_TEXT_MAIN, pad=8, loc='left')
    ax2.set_ylabel('Caída (%)', color=COLOR_TEXT_MAIN, fontsize=9.5, fontweight='bold')
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax2.tick_params(colors=COLOR_TEXT_MAIN, labelsize=9)

    max_dd_val = drawdown_pct.min() if not drawdown_pct.empty else 0.0
    ax2.annotate(f'Max DD: {max_dd_val:.2f}% (-${m["max_dd_dollar"]:,.2f} USDT)', xy=(0.015, 0.12), xycoords='axes fraction',
                 color=COLOR_RED, fontweight='bold', fontsize=9.0,
                 bbox=dict(boxstyle='round,pad=0.3', facecolor='#fef2f2', edgecolor=COLOR_RED, alpha=0.9))

    # -------------------------------------------------------------
    # FILA 3: PnL por Mes (Izq) y Rolling Metrics (Der)
    # -------------------------------------------------------------
    ax3_left = fig.add_subplot(gs[3, 0])
    ax3_left.set_facecolor(COLOR_BG)
    ax3_left.grid(True, linestyle='--', alpha=0.5, color=COLOR_GRID)
    for spine in ax3_left.spines.values():
        spine.set_color(COLOR_BORDER)

    meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    df_sorted_salida['mes_num'] = df_sorted_salida['tiempo_salida'].dt.month

    wins_by_month = df_sorted_salida[df_sorted_salida['pnl_neto'] > 0].groupby('mes_num')['pnl_neto'].sum()
    loss_by_month = df_sorted_salida[df_sorted_salida['pnl_neto'] < 0].groupby('mes_num')['pnl_neto'].sum()

    gains_val = [wins_by_month.get(i, 0.0) for i in range(1, 13)]
    loss_val = [loss_by_month.get(i, 0.0) for i in range(1, 13)]

    x = np.arange(12)
    w_bar = 0.38

    bars_win = ax3_left.bar(x - w_bar / 2, gains_val, w_bar, label='Ganancias (+)', color=COLOR_GREEN, edgecolor=COLOR_BORDER, linewidth=0.7)
    bars_loss = ax3_left.bar(x + w_bar / 2, loss_val, w_bar, label='Pérdidas (-)', color=COLOR_RED, edgecolor=COLOR_BORDER, linewidth=0.7)

    ax3_left.axhline(0, color=COLOR_TEXT_MUTED, linestyle='-', linewidth=0.8, alpha=0.7)
    ax3_left.set_title('3A. Ganancias vs Pérdidas por Mes del Año (Ene-Dic)', fontsize=11.5, fontweight='bold', color=COLOR_TEXT_MAIN, pad=8, loc='left')
    ax3_left.set_ylabel('Monto (USDT)', color=COLOR_TEXT_MAIN, fontsize=9.0, fontweight='bold')
    ax3_left.set_xticks(x)
    ax3_left.set_xticklabels(meses_nombres, fontsize=9.0)
    plt.setp(ax3_left.get_xticklabels(), rotation=0, ha='center')

    ax3_left.legend(loc='upper left', facecolor=COLOR_BG, edgecolor=COLOR_BORDER, fontsize=8.0)

    max_gain = max(gains_val) if gains_val else 1.0
    min_loss = min(loss_val) if loss_val else -1.0
    ax3_left.set_ylim(min_loss * 1.25 if min_loss < 0 else -1.0, max_gain * 1.25 if max_gain > 0 else 1.0)

    for bar in bars_win:
        h = bar.get_height()
        if h > 0:
            lbl_str = f"+${h/1000:.1f}k" if h >= 1000 else f"+${h:.0f}"
            ax3_left.annotate(lbl_str, xy=(bar.get_x() + bar.get_width() / 2, h),
                              xytext=(0, 3), textcoords='offset points',
                              ha='center', va='bottom', color=COLOR_GREEN, fontsize=7.2, fontweight='bold')

    for bar in bars_loss:
        h = bar.get_height()
        if h < 0:
            lbl_str = f"-${abs(h)/1000:.1f}k" if abs(h) >= 1000 else f"-${abs(h):.0f}"
            ax3_left.annotate(lbl_str, xy=(bar.get_x() + bar.get_width() / 2, h),
                              xytext=(0, -11), textcoords='offset points',
                              ha='center', va='top', color=COLOR_RED, fontsize=7.2, fontweight='bold')

    # Rolling Metrics vectorizado
    ax3_right = fig.add_subplot(gs[3, 1])
    ax3_right.set_facecolor(COLOR_BG)
    ax3_right.grid(True, linestyle='--', alpha=0.5, color=COLOR_GRID)
    for spine in ax3_right.spines.values():
        spine.set_color(COLOR_BORDER)

    df_sorted_entrada = df.sort_values('tiempo_entrada').reset_index(drop=True)
    num_trades = len(df_sorted_entrada)
    trade_indices = np.arange(1, num_trades + 1)
    pnl_series = df_sorted_entrada['pnl_neto']
    pnl_arr = pnl_series.to_numpy()

    pos_pnl = pd.Series(np.maximum(pnl_arr, 0.0), index=df_sorted_entrada.index)
    neg_pnl = pd.Series(np.maximum(-pnl_arr, 0.0), index=df_sorted_entrada.index)

    roll_pos = pos_pnl.rolling(window=rolling_window, min_periods=1).sum()
    roll_neg = neg_pnl.rolling(window=rolling_window, min_periods=1).sum()

    rolling_pf = pd.Series(np.nan, index=df_sorted_entrada.index)
    valid_loss = roll_neg > 0
    rolling_pf[valid_loss] = roll_pos[valid_loss] / roll_neg[valid_loss]

    rolling_exp = pnl_series.rolling(window=rolling_window, min_periods=1).mean()

    line1 = ax3_right.plot(trade_indices, rolling_pf, color=COLOR_PURPLE, linewidth=2.0, label='Rolling Profit Factor')
    ax3_right.axhline(1.0, color=COLOR_PURPLE, linestyle=':', linewidth=1.2, alpha=0.7)
    ax3_right.set_ylabel('Profit Factor', color=COLOR_PURPLE, fontsize=9.0, fontweight='bold')
    ax3_right.tick_params(axis='y', colors=COLOR_PURPLE, labelsize=8.5)
    ax3_right.tick_params(axis='x', colors=COLOR_TEXT_MAIN, labelsize=8.5)
    ax3_right.set_xlabel('Trade # (Ordenado por tiempo_entrada)', color=COLOR_TEXT_MAIN, fontsize=9.0)

    ax3_right_twin = ax3_right.twinx()
    line2 = ax3_right_twin.plot(trade_indices, rolling_exp, color=COLOR_AMBER, linewidth=1.8, linestyle='--', label='Rolling Expectancy ($)')
    ax3_right_twin.axhline(0.0, color=COLOR_AMBER, linestyle=':', linewidth=1.2, alpha=0.7)
    ax3_right_twin.set_ylabel('Expectancy (USDT)', color=COLOR_AMBER, fontsize=9.0, fontweight='bold')
    ax3_right_twin.tick_params(axis='y', colors=COLOR_AMBER, labelsize=8.5)

    note_roll = f"w={rolling_window}"
    if num_trades < rolling_window:
        note_roll += f" (Trades disp: {num_trades})"
    ax3_right.set_title(f'3B. Rolling Profit Factor & Expectancy ({note_roll})', fontsize=11.5, fontweight='bold', color=COLOR_TEXT_MAIN, pad=8, loc='left')

    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax3_right.legend(lines, labels, loc='upper left', facecolor=COLOR_BG, edgecolor=COLOR_BORDER, fontsize=8.0)

    buf = io.BytesIO()
    fig.savefig(
        buf,
        format='png',
        dpi=dpi,
        facecolor=fig.get_facecolor(),
        pil_kwargs={'compress_level': 1}
    )
    fig.clear()
    plt.close(fig)
    buf.seek(0)
    return buf
