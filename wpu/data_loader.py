import pandas as pd
from pathlib import Path

# -------------------------
# Load daily WPU exchange rates
# -------------------------
def load_daily_exchange_rates(file_path, tz='UTC'):
    """
    Load a CSV of daily WPU exchange rates.

    Args:
        file_path (str): Path to CSV file, e.g., "/data/wpu_exchange_rates.csv"
        tz (str): Timezone for datetime column

    Returns:
        pd.DataFrame: dataframe with datetime and WPU exchange rate columns

    Example:
        exchange_df = load_daily_exchange_rates("/data/wpu_exchange_rates.csv")
        print(exchange_df.head())
    """
    df = pd.read_csv(file_path)
    df['datetime'] = pd.to_datetime(df['Date'], format='%m/%d/%Y', errors='coerce')
    df = df.dropna(subset=['datetime']).reset_index(drop=True)
    if df['datetime'].dt.tz is None:
        df['datetime'] = df['datetime'].dt.tz_localize(tz)
    
    # convert all numeric columns (exchange rates) to floats
    for c in df.columns[1:]:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    
    return df


# -------------------------
# Load daily WPU constituent weights
# -------------------------
def load_wpu_weights(file_path):
    """
    Load WPU constituent weights from CSV.
    The first column is always treated as the date.
    """
    file_path = Path(file_path)
    df = pd.read_csv(file_path)

    # Rename first column to 'Date'
    df = df.rename(columns={df.columns[0]: 'Date'})

    # Parse as datetime
    df['Date'] = pd.to_datetime(df['Date'])

    # Optional: set Date as index
    df = df.set_index('Date').sort_index()

    return df


# -------------------------
# Minute loader
# -------------------------
def read_minute_wpu(file_path, ts_col="Timestamp"):
    """
    Reads a minute-level WPU exchange rate CSV and returns:
    - raw: wide dataframe with ['datetime', 'AUD', 'BRL', ...]
    - currencies: list of currency columns
    """
    file_path = Path(file_path)
    raw = pd.read_csv(file_path)
    raw.columns = [col.rstrip('=') for col in raw.columns]

    if ts_col not in raw.columns:
        raise ValueError(f"Expected timestamp column '{ts_col}' not found. Columns are: {list(raw.columns)}")

    raw['datetime'] = pd.to_datetime(raw[ts_col], errors='coerce')
    raw = raw.dropna(subset=['datetime']).reset_index(drop=True)

    currencies = [col for col in raw.columns if col not in [ts_col, 'datetime']]
    
    return raw, currencies

# -------------------------
# Tick loader
# -------------------------
def read_tick_wpu(file_obj, tz='UTC'):
    name = getattr(file_obj, "name", "")
    if name.endswith('.xlsx') or name.endswith('.xls'):
        raw = pd.read_excel(file_obj, skiprows=1)
    else:
        raw = pd.read_csv(file_obj, skiprows=1)

    raw.columns = [c.strip() for c in raw.columns]
    n_cols = raw.shape[1]
    tidy_frames = []

    i = 0
    while i < n_cols:
        col_ts = raw.columns[i]
        col_px = raw.columns[i+1] if i+1 < n_cols else None
        if 'timestamp' in col_ts.lower() and col_px:
            df = raw[[col_ts, col_px]].rename(columns={col_ts:'datetime', col_px:'price'})
            df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
            df = df.dropna(subset=['datetime']).reset_index(drop=True)
            if df['datetime'].dt.tz is None:
                df['datetime'] = df['datetime'].dt.tz_localize(tz)
            df['currency'] = col_px.replace('=','')
            tidy_frames.append(df)
        i += 2

    tidy = pd.concat(tidy_frames, ignore_index=True).sort_values(['currency','datetime']).reset_index(drop=True) if tidy_frames else pd.DataFrame(columns=['datetime','price','currency'])
    return tidy
