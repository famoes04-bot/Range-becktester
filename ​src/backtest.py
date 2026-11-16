
import pandas as pd
from src.indicators import calculate_opening_range, detect_fvg_and_eq_filter

def run_quant_backtest_engine(df: pd.DataFrame, asset_type: str = "NAS100", rr_target: float = 2.0, manual_buf: float = 5.0) -> pd.DataFrame:
    """Executa o motor estatístico de backtest integrando volatilidade e regras de saída."""
    print(f"--- [Backtest Engine] A executar motor para o ativo: {asset_type} ---")
    
    vol_multipliers = {
        "GOLD": 2.0, "SILVER": 1.8, "CRYPTO": 3.0, 
        "NAS100": 1.5, "OIL": 1.2, "JPY": 0.8, "FOREX": 0.5, "DXY": 0.4
    }
    v_mult = vol_multipliers.get(asset_type, 1.0)
    dynamic_buf = manual_buf * v_mult

    trades_log = []

    for trade_date, group in df.groupby('date'):
        group = group.reset_index(drop=True)
        if len(group) < 30:
            continue
            
        s_high, s_low, s_eq = calculate_opening_range(group, session_hour=8, session_minute=0)
        if s_high is None:
            continue
            
        operational_window = group[(group['hour'] >= 8) & ((group['hour'] > 8) | (group['minute'] >= 5))]
        
        fvg_active = False
        fvg_dir = 0
        fvg_top = 0.0
        fvg_bottom = 0.0
        breakout_done = False
        
        for i in range(2, len(operational_window)):
            row = operational_window.iloc[i]
            r_prev1 = operational_window.iloc[i-1]
            r_prev2 = operational_window.iloc[i-2]
            
            raw_bull, raw_bear, eq_break_bull, eq_break_bear = detect_fvg_and_eq_filter(
                row, r_prev1, r_prev2, s_high, s_low, s_eq
            )
            
            # Deteção FVG Bearish
            if raw_bear and not fvg_active:
                if (row['close'] < s_low or row['low'] < s_low) or eq_break_bear:
                    fvg_active = True
                    fvg_dir = -1
                    fvg_top = r_prev2['low']
                    fvg_bottom = row['high']
                    breakout_done = (row['close'] < s_low or row['low'] < s_low or eq_break_bear)
            
            # Deteção FVG Bullish
            if raw_bull and not fvg_active:
                if (row['close'] > s_high or row['high'] > s_high) or eq_break_bull:
                    fvg_active = True
                    fvg_dir = 1
                    fvg_top = row['low']
                    fvg_bottom = r_prev2['high']
                    breakout_done = (row['close'] > s_high or row['high'] > s_high or eq_break_bull)
            
            if fvg_active and not breakout_done:
                if fvg_dir == -1 and (row['low'] < s_low or eq_break_bear):
                    breakout_done = True
                elif fvg_dir == 1 and (row['high'] > s_high or eq_break_bull):
                    breakout_done = True
            
            # Execução e Simulação de Reteste
            if fvg_active and breakout_done:
                if fvg_dir == -1 and row['high'] >= fvg_bottom and row['high'] <= (fvg_top + dynamic_buf):
                    entry_p = max(row['open'], fvg_bottom)
                    sl_p = fvg_top + dynamic_buf
                    risk = sl_p - entry_p
                    tp_p = entry_p - (risk * rr_target)
                    
                    outcome = evaluate_outcome(operational_window.iloc[i:], entry_p, sl_p, tp_p, direction=-1)
                    trades_log.append({'date': trade_date, 'type': 'SHORT', 'pnl': outcome})
                    fvg_active = False
                    break
                
                elif fvg_dir == 1 and row['low'] <= fvg_top and row['low'] >= (fvg_bottom - dynamic_buf):
                    entry_p = min(row['open'], fvg_top)
                    sl_p = fvg_bottom - dynamic_buf
                    risk = entry_p - sl_p
                    tp_p = entry_p + (risk * rr_target)
                    
                    outcome = evaluate_outcome(operational_window.iloc[i:], entry_p, sl_p, tp_p, direction=1)
                    trades_log.append({'date': trade_date, 'type': 'LONG', 'pnl': outcome})
                    fvg_active = False
                    break

    return pd.DataFrame(trades_log)

def evaluate_outcome(sub_df, entry, sl, tp, direction):
    for _, bar in sub_df.iterrows():
        if direction == 1:
            if bar['low'] <= sl: return -1.0
            if bar['high'] >= tp: return 2.0
        else:
            if bar['high'] >= sl: return -1.0
            if bar['low'] <= tp: return 2.0
    return 0.0
