import pandas as pd

def merge_resample_forward_fill(daily_df, minute_df=None, tick_df=None, freq='1min', tz='UTC'):
    """
    Merge daily, minute, and tick data into a single time series.
    - Forward-fill missing prices per currency
    - Resample tick/minute to the given frequency
    """
    dfs = []

    if daily_df is not None:
        df = daily_df.copy()
        df = df.set_index('datetime').sort_index()
        dfs.append(df)

    if minute_df is not None:
        df = minute_df.copy()
        df = df.set_index('datetime').sort_index()
        df = df.resample(freq).ffill()
        dfs.append(df)

    if tick_df is not None:
        # pivot tick_df to wide format by currency, then resample
        pivot = tick_df.pivot(index='datetime', columns='currency', values='price')
        pivot = pivot.sort_index().resample(freq).ffill()
        dfs.append(pivot)

    if dfs:
        merged = pd.concat(dfs, axis=1)
        # forward-fill any remaining missing values
        merged = merged.ffill()
    else:
        merged = pd.DataFrame()

    # reset index to have datetime column
    merged = merged.reset_index()
    return merged


ZOOM_MAPPING = {
    '1d': 'tick',      # tick data preferred
    '5d': 'minute',    # minute data preferred
    '1w': 'minute',
    '1m': 'daily',
    '3m': 'daily',
    '6m': 'daily',
    '1y': 'daily',
    '3y': 'daily',
    '5y': 'daily',
    '10y': 'daily'
}

def filter_by_zoom(df, zoom='1d', price_col='price'):
    """
    Filter or resample merged dataframe based on zoom level
    """
    if df.empty:
        return df

    now = pd.Timestamp.now(tz=df['datetime'].dt.tz)
    if zoom.endswith('d'):
        delta_days = int(zoom[:-1])
        start = now - pd.Timedelta(days=delta_days)
    elif zoom.endswith('w'):
        delta_weeks = int(zoom[:-1])
        start = now - pd.Timedelta(weeks=delta_weeks)
    elif zoom.endswith('m'):
        delta_months = int(zoom[:-1])
        start = now - pd.DateOffset(months=delta_months)
    elif zoom.endswith('y'):
        delta_years = int(zoom[:-1])
        start = now - pd.DateOffset(years=delta_years)
    else:
        start = df['datetime'].min()

    filtered = df[df['datetime'] >= start].copy()
    return filtered



def calculate_wpu_price(rate_df, weights_df, date_col="datetime"):
    """
    Calculate WPUUSD from wide-format exchange rate data and daily weights.

    Missing rates or weights are forward-filled.

    Parameters
    ----------
    rate_df : pd.DataFrame
        Wide-format exchange rate data. Columns: ['datetime', 'AUD', 'BRL', ..., 'USD']
    weights_df : pd.DataFrame
        Daily WPU weights. Columns: ['AUD', 'BRL', ..., 'USD'], indexed by date.
    date_col : str
        Column in rate_df containing timestamps.

    Returns
    -------
    pd.DataFrame
        DataFrame with ['datetime', 'WPUUSD']
    """
    df = rate_df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col).reset_index(drop=True)

    # Forward-fill missing rates per currency
    currency_cols = [c for c in df.columns if c != date_col]
    df[currency_cols] = df[currency_cols].ffill()

    # Prepare weights: ensure index is datetime and forward-fill missing weights
    weights = weights_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(weights.index):
        weights.index = pd.to_datetime(weights.index)
    weights = weights.sort_index().ffill()

    # Align each timestamp with the appropriate daily weights
    df['weight_date'] = df[date_col].dt.floor('D')  # truncate to date
    merged = df.merge(weights, left_on='weight_date', right_index=True,
                      how='left', suffixes=('', '_wt'))

    # Construct weight column names
    wt_cols = [c + '_wt' for c in currency_cols]

    # Forward-fill missing weights (in case of missing merge)
    merged[wt_cols] = merged[wt_cols].ffill()

    # Compute WPUUSD = sum(rate * weight)
    merged['WPUUSD'] = merged[currency_cols].mul(merged[wt_cols], axis=0).sum(axis=1)

    # Return only datetime and WPUUSD
    return merged[[date_col, 'WPUUSD']].copy()
