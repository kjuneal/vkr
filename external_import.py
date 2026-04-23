import pandas as pd
from pathlib import Path
from data_generate import load_to_postgres, load_to_sqlite, load_to_csv


def load_external_data(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
    if path.suffix.lower() in {'.csv'}:
        df = pd.read_csv(path)
    elif path.suffix.lower() in {'.xlsx', '.xls'}:
        df = pd.read_excel(path)
    else:
        raise ValueError(f'Unsupported file format: {path.suffix}')

    required = {'timestamp', 'value'}
    if not required.issubset(df.columns):
        raise ValueError(f'File must contain columns: {required}')

    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df[['timestamp', 'value']]


def prepare_external_experiment(file_path: str, postgres_engine, sqlite_path: str, csv_path: str):
    df = load_external_data(file_path)
    load_to_postgres(df, postgres_engine)
    load_to_sqlite(df, sqlite_path)
    load_to_csv(df, csv_path)
    return df