import os
import numpy as np
import pandas as pd
from datetime import datetime

def run_quant_backtest(csv_path, asset_type="NAS100", rr_target=2.0, manual_buf=5.0):
    """
    Motor de Backtest Quantitativo para Estratégia ORB + FVG Retest + EQ Filter
    Desenvolvido com base no rigor metodológico de análise estatística.
    """
    print(f"--- A carregar dados para o ativo: {asset_type} ---")
    df = pd.read_csv(csv_path)
    
    # 1. Padronização Temporal e Conversão para Europe/Lisbon
    df['date_time'] = pd.to_datetime(df['date_time'])
    df['date_time'] = df['date_time'].dt.tz_localize('UTC').dt.tz_convert('Europe/Lisbon')
    df['date'] = df['date_time'].dt.date
    df['hour'] = df['date_time'].dt.hour
    df['minute'] = df['date_time'].dt.minute
    
    # 2. Definição do Multiplicador de Volatilidade Dinâmico (Alinhado ao Pine Script)
    vol_multipliers = {
        "GOLD": 2.0, "SILVER": 1.8, "CRYPTO": 3.0, 
        "NAS100": 1.5, "OIL": 1.2, "JPY": 0.8, "FOREX": 0.5, "DXY": 0.4
    }
    v_mult = vol_multipliers.get(asset_type, 1.0)
    dynamic_buf = manual_buf * v_mult

    trades_log = []

    # Agrupamento por dia de negociação para isolar as sessões
    for trade_date, group in df.groupby('date'):
        group = group.reset_index(drop=True)
        if len(group) < 30:
            continue
            
        # Identificação da Vela de Abertura de Londres (08:00)
        open_bar = group[(group['hour'] == 8) & (group['minute'] == 0)]
        if open_bar.empty:
            continue
            
        s_high = open_bar.iloc[0]['high']
        s_low = open_bar.iloc[0]['low']
        s_eq = (s_high + s_low) / 2.0
        
        # Janela Operacional (08:05 em diante)
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
            
            # Condições de FVG Bruto
            raw_bull_fvg = (row['low'] > r_prev2['high']) and (r_prev1['close'] > r_prev2['high'])
            raw_bear_fvg = (row['high'] < r_prev2['low']) and (r_prev1['close'] < r_prev2['low'])
            
            # Filtro de EQ / Rompimento do Range
            eq_broken_bull = (row['close'] > s_eq) and (r_prev1['close'] <= s_eq)
            eq_broken_bear = (row['close'] < s_eq) and (r_prev1['close'] >= s_eq)
            
            # Deteção Bearish FVG Validado
            if raw_bear_fvg and not fvg_active:
                if (row['close'] < s_low or row['low'] < s_low) or eq_broken_bear:
                    fvg_active = True
                    fvg_dir = -1
                    fvg_top = r_prev2['low']
                    fvg_bottom = row['high']
                    breakout_done = (row['close'] < s_low or row['low'] < s_low or eq_broken_bear)
            
            # Deteção Bullish FVG Validado
            if raw_bull_fvg and not fvg_active:
                if (row['close'] > s_high or high > s_high or row['close'] > s_high) or eq_broken_bull:
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
            
            # Simulação do Reteste e Execução do Trade
            if fvg_active and breakout_done:
                # Reteste Short
                if fvg_dir == -1 and row['high'] >= fvg_bottom and row['high'] <= (fvg_top + dynamic_buf):
                    entry_p = max(row['open'], fvg_bottom)
                    sl_p = fvg_top + dynamic_buf
                    risk = sl_p - entry_p
                    tp_p = entry_p - (risk * rr_target)
                    
                    outcome = evaluate_trade_outcome(operational_window.iloc[i:], entry_p, sl_p, tp_p, direction=-1)
                    trades_log.append({'date': trade_date, 'type': 'SHORT', 'pnl': outcome})
                    fvg_active = False
                    break
                
                # Reteste Long
                elif fvg_dir == 1 and row['low'] <= fvg_top and row['low'] >= (fvg_bottom - dynamic_buf):
                    entry_p = min(row['open'], fvg_top)
                    sl_p = fvg_bottom - dynamic_buf
                    risk = entry_p - sl_p
                    tp_p = entry_p + (risk * rr_target)
                    
                    outcome = evaluate_trade_outcome(operational_window.iloc[i:], entry_p, sl_p, tp_p, direction=1)
                    trades_log.append({'date': trade_date, 'type': 'LONG', 'pnl': outcome})
                    fvg_active = False
                    break

    return pd.DataFrame(trades_log)

def evaluate_trade_outcome(sub_df, entry, sl, tp, direction):
    """Função auxiliar para calcular se o trade atingiu o Take Profit ou Stop Loss."""
    for _, bar in sub_df.iterrows():
        if direction == 1: # Long
            if bar['low'] <= sl:
                return -1.0
            if bar['high'] >= tp:
                return 2.0
        else: # Short
            if bar['high'] >= sl:
                return -1.0
            if bar['low'] <= tp:
                return 2.0
    return 0.0

if __name__ == "__main__":
    # Exemplo de execução do script apontando para o seu ficheiro de dados
    # Substitua "data/historical_data.csv" pelo caminho real do seu ficheiro CSV
    try:
        results_df = run_quant_backtest("data/historical_data.csv", asset_type="NAS100")
        print("\n--- Relatório de Resultados Estatísticos ---")
        print(results_df.head())
        print(f"Total de Trades Executados: {len(results_df)}")
    except FileNotFoundError:
        print("Ficheiro CSV não encontrado. Por favor, adicione o ficheiro na pasta 'data/' para iniciar o teste.")
