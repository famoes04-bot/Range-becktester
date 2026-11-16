import pandas as pd
import numpy as np

def calculate_opening_range(group_df, session_hour=8, session_minute=0):
    """Extrai estritamente o High, Low e EQ da vela de abertura da sessão."""
    open_bar = group_df[(group_df['hour'] == session_hour) & (group_df['minute'] == session_minute)]
    if open_bar.empty:
        return None, None, None
        
    s_high = open_bar.iloc[0]['high']
    s_low = open_bar.iloc[0]['low']
    s_eq = (s_high + s_low) / 2.0
    return s_high, s_low, s_eq

def detect_fvg_and_eq_filter(row, r_prev1, r_prev2, s_high, s_low, s_eq):
    """Valida a formação de FVG em correlação com a quebra ou rejeição do EQ e limites do Range."""
    raw_bull_fvg = (row['low'] > r_prev2['high']) and (r_prev1['close'] > r_prev2['high'])
    raw_bear_fvg = (row['high'] < r_prev2['low']) and (r_prev1['close'] < r_prev2['low'])
    
    eq_broken_bull = (row['close'] > s_eq) and (r_prev1['close'] <= s_eq)
    eq_broken_bear = (row['close'] < s_eq) and (r_prev1['close'] >= s_eq)
    
    return raw_bull_fvg, raw_bear_fvg, eq_broken_bull, eq_broken_bear

