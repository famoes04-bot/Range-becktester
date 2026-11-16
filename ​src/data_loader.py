import os
import pandas as pd
import numpy as np

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza os nomes das colunas de um DataFrame para um formato standard:
    ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    Independentemente de virem de MetaTrader, yfinance ou exchanges de cripto.
    """
    # Remove espaços em branco, `<` e `>`, e converte para minúsculas
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace('<', '', regex=False)
        .str.replace('>', '', regex=False)
        .str.replace('date', 'timestamp', regex=False)
        .str.replace('datetime', 'timestamp', regex=False)
    )
    
    # Dicionário de mapeamento para sinónimos comuns
    rename_map = {
        't': 'timestamp',
        'time': 'timestamp',
        'o': 'open',
        'h': 'high',
        'l': 'low',
        'c': 'close',
        'v': 'volume',
        'vol': 'volume'
    }
    
    df = df.rename(columns=rename_map)
    
    # Validação das colunas obrigatórias
    required_cols = ['timestamp', 'open', 'high', 'low', 'close']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Colunas obrigatórias em falta após normalização: {missing}. Colunas detetadas: {list(df.columns)}")
    
    return df

def load_and_resample_asset(file_path: str, timeframe: str = '1D') -> pd.DataFrame:
    """
    Carrega um ficheiro CSV bruto, normaliza as colunas, converte o timestamp,
    e faz o resampling para o timeframe alvo (ex: '1H', '1D').
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Ficheiro não encontrado: {file_path}")
    
    # Leitura do CSV
    df = pd.read_csv(file_path)
    
    # Normalização de colunas
    df = normalize_columns(df)
    
    # Tratamento e conversão da coluna de tempo
    # Suporta timestamps em formato string (ISO/Data) ou numéricos (Unix millis)
    if pd.api.types.is_numeric_dtype(df['timestamp']):
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    else:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
    df = df.set_index('timestamp')
    df = df.sort_index()
    
    # Regras de agregação padrão para OHLCV
    aggregation_rules = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum' if 'volume' in df.columns else lambda x: np.nan
    }
    
    # Remove colunas que não estejam nas regras
    aggregation_rules = {k: v for k, v in aggregation_rules.items() if k in df.columns}
    
    # Resampling para o timeframe desejado
    df_resampled = df.resample(timeframe).agg(aggregation_rules)
    
    # Remove linhas onde todos os valores OHLC são NaN
    df_resampled = df_resampled.dropna(subset=['close'], how='all')
    
    return df_resampled

def build_unified_panel(file_paths_dict: dict, timeframe: str = '1D', max_ffill: int = None) -> pd.DataFrame:
    """
    Recebe um dicionário de ativos e caminhos de ficheiros, processa cada um,
    e junta-os numa única matriz unificada (Panel Data).
    """
    unified_df = pd.DataFrame()
    
    for asset_name, path in file_paths_dict.items():
        print(f"A processar {asset_name} a partir de {path}...")
        df_asset = load_and_resample_asset(path, timeframe=timeframe)
        
        # Prefixa as colunas com o nome do ativo (ex: BTC_close, NAS_close)
        df_asset = df_asset.rename(columns={col: f"{asset_name}_{col}" for col in df_asset.columns})
        
        if unified_df.empty:
            unified_df = df_asset
        else:
            # Outer join para alinhar todos os timestamps
            unified_df = unified_df.join(df_asset, how='outer')
            
    # Ordena cronologicamente por segurança
    unified_df = unified_df.sort_index()
    
    # Opcional: Forward fill limitado (ex: útil para gráficos/indicadores específicos sem rebentar com fins de semana longos)
    if max_ffill is not None:
        unified_df = unified_df.ffill(limit=max_ffill)
        
    return unified_df

