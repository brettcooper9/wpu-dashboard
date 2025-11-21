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




def calculate_wpu_price(exchange_df, weights_df, currencies=None, tz='NYC'):
    """
    Compute WPU price for any frequency of exchange rates using daily weights.
    
    Args:
        exchange_df (pd.DataFrame): exchange rates with a 'datetime' column and currency columns.
                                    Can be minute, tick, or daily frequency.
        weights_df (pd.DataFrame): daily weights with 'datetime' column and same currency columns.
        currencies (list, optional): list of currencies to include. Default: all columns in weights_df except 'datetime'.
        tz (str): timezone to localize weights and exchange_df if naive.
    
    Returns:
        pd.DataFrame: dataframe with 'datetime' and calculated 'price'
    
    Notes:
        - Daily weights are forward-filled to match the timestamp of exchange_df.
        - Exchange rates are multiplied by weights/100 (assuming weights sum to 100%).
    
    Example:
        # Calculate WPUUSD for minute-level exchange rates using daily weights
        wpu_minute = calculate_wpu_price(minute_df, weights_df)
    """
    if currencies is None:
        currencies = [c for c in weights_df.columns if c != 'datetime']

    # Ensure datetime columns are timezone-aware
    if exchange_df['datetime'].dt.tz is None:
        exchange_df['datetime'] = exchange_df['datetime'].dt.tz_localize(tz)
    if weights_df['datetime'].dt.tz is None:
        weights_df['datetime'] = weights_df['datetime'].dt.tz_localize(tz)

    # Forward-fill weights to match timestamps in exchange_df
    weights_ff = weights_df.set_index('datetime').sort_index()
    # Reindex weights to match exchange_df's datetime index (nearest previous weight)
    weights_ff = weights_ff.reindex(exchange_df['datetime'], method='ffill').reset_index()
    
    # Compute weighted sum
    price_series = pd.Series(0, index=exchange_df.index, dtype=float)
    for c in currencies:
        if c in exchange_df.columns and c in weights_ff.columns:
            price_series += exchange_df[c] * weights_ff[c] / 100
    
    result = pd.DataFrame({
        'datetime': exchange_df['datetime'],
        'price': price_series
    })
    return result