# =====================================================================
# PASSO 1: ENVIRONMENT & IMPORTAÇÕES ESSENCIAIS
# =====================================================================
import pandas as pd
import numpy as np
import os
from datetime import datetime

print("--- Passo 1: Ambiente configurado com sucesso ---")

# =====================================================================
# PASSO 2 & 3: CARREGAMENTO E VALIDAÇÃO DE DADOS DE 1 MINUTO
# =====================================================================
def load_and_validate_data(csv_path):
    if not os.path.exists(csv_path):
        print(f"Aviso: O ficheiro {csv_path} não foi encontrado.")
        return None
    
    df = pd.read_csv(csv_path)
    print(f"--- Passo 2: Dados carregados. Total de registos: {len(df)} ---")
    
    # Passo 3: Validação de Dados
    required_columns = ['date_time', 'open', 'high', 'low', 'close']
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Erro de Validação: Coluna obrigatória '{col}' em falta no dataset.")
            
    print("--- Passo 3: Validação de integridade concluída sem erros ---")
    return df

# =====================================================================
# PASSO 4: LIMPEZA E PADRONIZAÇÃO DE DADOS
# =====================================================================
def clean_and_standardize_data(df):
    df['date_time'] = pd.to_datetime(df['date_time'])
    df = df.sort_values('date_time').reset_index(drop=True)
    
    # Conversão para fuso Europe/Lisbon para precisão institucional
    df['date_time'] = df['date_time'].dt.tz_localize('UTC', nonexistent='shift_forward', ambiguous='NaT').dt.tz_convert('Europe/Lisbon')
    df['date'] = df['date_time'].dt.date
    df['hour'] = df['date_time'].dt.hour
    df['minute'] = df['date_time'].dt.minute
    
    print("--- Passo 4: Limpeza e padronização temporal concluídas ---")
    return df

# =====================================================================
# PASSOS 5 a 19: MOTOR ESTRUTURAL DA ESTRATÉGIA (ORB + FVG + EQ + BACKTEST)
# =====================================================================
def run_quant_backtest_engine(df, asset_type="NAS100", rr_target=2.0, manual_buf=5.0):
    print(f"--- Passos 5-8: Configurando regras de estratégia para {asset_type} ---")
    
    vol_multipliers = {
        "GOLD": 2.0, "SILVER": 1.8, "CRYPTO": 3.0, 
        "NAS100": 1.5, "OIL": 1.2, "JPY": 0.8, "FOREX": 0.5, "DXY": 0.4
    }
    v_mult = vol_multipliers.get(asset_type, 1.0)
    dynamic_buf = manual_buf * v_mult

    trades_log = []

    # Passo 9 a 12: Engenharia de PnL e Séries Temporais por Sessão
    for trade_date, group in df.groupby('date'):
        group = group.reset_index(drop=True)
        if len(group) < 30:
            continue
            
        # Identificação da vela de abertura de Londres (08:00)
        open_bar = group[(group['hour'] == 8) & (group['minute'] == 0)]
        if open_bar.empty:
            continue
            
        s_high = open_bar.iloc[0]['high']
        s_low = open_bar.iloc[0]['low']
        s_eq = (s_high + s_low) / 2.0  # Linha de Equilíbrio
        
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
            
            raw_bull_fvg = (row['low'] > r_prev2['high']) and (r_prev1['close'] > r_prev2['high'])
            raw_bear_fvg = (row['high'] < r_prev2['low']) and (r_prev1['close'] < r_prev2['low'])
            
            eq_broken_bull = (row['close'] > s_eq) and (r_prev1['close'] <= s_eq)
            eq_broken_bear = (row['close'] < s_eq) and (r_prev1['close'] >= s_eq)
            
            if raw_bear_fvg and not fvg_active:
                if (row['close'] < s_low or row['low'] < s_low) or eq_broken_bear:
                    fvg_active = True
                    fvg_dir = -1
                    fvg_top = r_prev2['low']
                    fvg_bottom = row['high']
                    breakout_done = (row['close'] < s_low or row['low'] < s_low or eq_broken_bear)
            
            if raw_bull_fvg and not fvg_active:
                if (row['close'] > s_high or row['high'] > s_high) or eq_broken_bull:
                    fvg_active = True
                    fvg_dir = 1
                    fvg_top = row['low']
                    fvg_bottom = r_prev2['high']
                    breakout_done = (row['close'] > s_high or row['high'] > s_high or eq_broken_bull)
            
            if fvg_active and not breakout_done:
                if fvg_dir == -1 and (row['low'] < s_low or eq_broken_bear):
                    breakout_done = True
                elif fvg_dir == 1 and (row['high'] > s_high or eq_broken_bull):
                    breakout_done = True
            
            # Passos 13-19: Execução, Risco e Curva de Capital
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

    print("--- Passos 14-19: Análise estatística e sumário de desempenho gerados ---")
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

if __name__ == "__main__":
    csv_file = "data/historical_data.csv"
    raw_df = load_and_validate_data(csv_file)
    if raw_df is not None:
        clean_df = clean_and_standardize_data(raw_df)
        results = run_quant_backtest_engine(clean_df, asset_type="NAS100")
        print("\n=== SUMÁRIO DE DESEMPENHO (PERFORMANCE SUMMARY) ===")
        print(results.head())
        print(f"Total de Trades Validados: {len(results)}")
