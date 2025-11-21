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
