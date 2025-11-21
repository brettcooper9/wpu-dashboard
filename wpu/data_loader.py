import pandas as pd

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
def load_wpu_weights(file_path, tz='UTC'):
    """
    Load a CSV of daily WPU constituent weights.

    Args:
        file_path (str): Path to CSV file, e.g., "/data/wpu_constituents.csv"
        tz (str): Timezone for datetime column

    Returns:
        pd.DataFrame: dataframe with datetime and weight columns for each currency

    Example:
        weights_df = load_wpu_weights("/data/wpu_constituents.csv")
        print(weights_df.head())
    """
    df = pd.read_csv(file_path)
    df['datetime'] = pd.to_datetime(df.iloc[:,0], format='%m/%d/%Y', errors='coerce')
    df = df.dropna(subset=['datetime']).reset_index(drop=True)
    if df['datetime'].dt.tz is None:
        df['datetime'] = df['datetime'].dt.tz_localize(tz)
    
    # convert all numeric columns (weights) to floats
    for c in df.columns[1:]:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    
    return df


# -------------------------
# Minute loader
# -------------------------
def read_minute_wpu(file_obj, tz='UTC', default_col='USD='):
    name = getattr(file_obj, "name", "")
    if name.endswith('.xlsx') or name.endswith('.xls'):
        raw = pd.read_excel(file_obj, skiprows=1)
    else:
        raw = pd.read_csv(file_obj, skiprows=1)

    raw.columns = [c.strip() for c in raw.columns]
    ts_col_candidates = [c for c in raw.columns if 'time' in c.lower()]
    ts_col = ts_col_candidates[0] if ts_col_candidates else raw.columns[0]

    raw['datetime'] = pd.to_datetime(raw[ts_col], errors='coerce')
    raw = raw.dropna(subset=['datetime']).reset_index(drop=True)
    if raw['datetime'].dt.tz is None:
        raw['datetime'] = raw['datetime'].dt.tz_localize(tz)

    price_cols = [c for c in raw.columns if c != ts_col]
    for c in price_cols:
        raw[c] = pd.to_numeric(raw[c], errors='coerce')

    chosen_col = default_col if default_col in price_cols else price_cols[0] if price_cols else None
    tidy = raw[['datetime', chosen_col]].rename(columns={chosen_col:'price'}).dropna(subset=['price']).reset_index(drop=True) if chosen_col else pd.DataFrame(columns=['datetime','price'])
    return raw, tidy, price_cols

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
