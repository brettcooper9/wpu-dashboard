# main_app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz

st.set_page_config(page_title="WPU Basket Dashboard", layout="wide")

# -------------------------
# Helpers
# -------------------------
def load_csv(path, datetime_col, tz=None, parse_dates=True):
    df = pd.read_csv(path, parse_dates=[datetime_col]) if parse_dates else pd.read_csv(path)
    df = df.rename(columns={datetime_col: "datetime"})
    if tz:
        df['datetime'] = pd.to_datetime(df['datetime']).dt.tz_localize(tz, ambiguous='infer', nonexistent='shift_forward')
    else:
        df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    return df

def unify_price_series(daily_df, minute_df, tick_df):
    """Return a single dataframe with datetime (tz-aware) and price columns.
       Prefer most granular data when overlapping (tick > minute > daily).
    """
    # Normalize columns
    daily = daily_df.copy()
    daily['datetime'] = pd.to_datetime(daily['datetime']).dt.tz_localize(None)  # keep naive for resampling but convert later
    # Expand daily to midnight timestamps so we can merge; keep 'price' at close for daily
    daily = daily.rename(columns={'price': 'price_daily'})
    minute = minute_df.copy().rename(columns={'price': 'price_minute'})
    tick = tick_df.copy().rename(columns={'price': 'price_tick'})

    # Ensure all datetime are timezone-aware in same tz (UTC) for consistent slicing
    for df in (daily, minute, tick):
        df['datetime'] = pd.to_datetime(df['datetime']).dt.tz_convert('UTC') if pd.api.types.is_datetime64tz_dtype(df['datetime']) else pd.to_datetime(df['datetime']).dt.tz_localize('UTC')

    # Build a timeline from the highest-frequency data available (tick -> minute -> daily)
    # Start with daily as base (one sample per day at 00:00 UTC)
    # Then upsample to minutes and overwrite with minute/tick where available.
    # Create a master index between min and max datetimes at 1 minute resolution
    min_dt = min(d['datetime'].min() for d in (daily, minute, tick) if not d.empty)
    max_dt = max(d['datetime'].max() for d in (daily, minute, tick) if not d.empty)
    master_idx = pd.date_range(start=min_dt.floor('D'), end=max_dt.ceil('D'), freq='1min', tz='UTC')
    master = pd.DataFrame({'datetime': master_idx})

    # Merge daily -> forward fill to minutes (use daily price as end-of-day price across that day)
    daily_min = daily.set_index('datetime').resample('1min').ffill().reset_index()  # this expands daily, but works if daily has midnight timestamps
    master = master.merge(daily_min[['datetime','price_daily']], on='datetime', how='left')

    # Merge minute and tick and prefer tick then minute then daily
    master = master.merge(minute[['datetime','price_minute']], on='datetime', how='left')
    master = master.merge(tick[['datetime','price_tick']], on='datetime', how='left')

    # Compose final price: tick if present else minute if present else daily
    master['price'] = master['price_tick'].combine_first(master['price_minute']).combine_first(master['price_daily'])
    master = master[['datetime','price']].dropna().reset_index(drop=True)
    return master

def filter_by_range(df, range_label):
    now = df['datetime'].max()
    if range_label == 'Prior Day':
        # prior trading day = previous calendar day (24h slice before the start of today in UTC)
        end = now.normalize()  # midnight of latest day
        start = end - pd.Timedelta(days=1)
    elif range_label == '1d':
        end = df['datetime'].max()
        start = end - pd.Timedelta(days=1)
    elif range_label == '5d':
        end = df['datetime'].max()
        start = end - pd.Timedelta(days=5)
    elif range_label == '1w':
        end = df['datetime'].max()
        start = end - pd.Timedelta(weeks=1)
    elif range_label == '1m':
        end = df['datetime'].max()
        start = end - pd.Timedelta(days=30)
    elif range_label == '3m':
        end = df['datetime'].max()
        start = end - pd.Timedelta(days=90)
    elif range_label == '6m':
        end = df['datetime'].max()
        start = end - pd.Timedelta(days=182)
    elif range_label == '1y':
        end = df['datetime'].max()
        start = end - pd.Timedelta(days=365)
    elif range_label == '3y':
        end = df['datetime'].max()
        start = end - pd.Timedelta(days=365*3)
    elif range_label == '5y':
        end = df['datetime'].max()
        start = end - pd.Timedelta(days=365*5)
    elif range_label == '10y':
        end = df['datetime'].max()
        start = end - pd.Timedelta(days=365*10)
    else:
        # fallback: show all
        start = df['datetime'].min()
        end = df['datetime'].max()
    mask = (df['datetime'] >= start) & (df['datetime'] <= end)
    return df.loc[mask].copy()

def plot_price(df, title="WPU Price"):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['datetime'], y=df['price'], mode='lines', name='Price'))
    fig.update_layout(title=title, xaxis_title='Time', yaxis_title='Price', margin=dict(l=40, r=20, t=40, b=40))
    return fig

# -------------------------
# App initialization
# -------------------------
st.title("FTSE WPU Basket — Interactive Dashboard")

# File uploader + examples
st.sidebar.header("Data inputs")
daily_file = st.sidebar.file_uploader("Upload WPU daily CSV (10 years)", type=['csv'], key='daily')
minute_file = st.sidebar.file_uploader("Upload WPU minute CSV (5 days)", type=['csv'], key='minute')
tick_file = st.sidebar.file_uploader("Upload WPU tick CSV (1 day)", type=['csv'], key='tick')

st.sidebar.markdown("Expected CSV column names:")
st.sidebar.markdown("- daily: `date` or `datetime`, `price`")
st.sidebar.markdown("- minute: `datetime`, `price`")
st.sidebar.markdown("- tick: `timestamp` or `datetime`, `price`")

# For demo mode, allow sample generation if files not provided
demo_mode = False
if not daily_file or not minute_file or not tick_file:
    if st.sidebar.button("Use demo synthetic data"):
        demo_mode = True

# -------------------------
# Load / Prepare Data
# -------------------------
if demo_mode:
    # Create synthetic demo data
    rng_daily = pd.date_range(end=pd.Timestamp.utcnow().normalize(), periods=365*10, freq='D', tz='UTC')
    daily_df = pd.DataFrame({'datetime': rng_daily, 'price': (100 + np.cumsum(np.random.randn(len(rng_daily))*0.1)).round(4)})
    rng_min = pd.date_range(end=pd.Timestamp.utcnow(), periods=5*24*60, freq='1min', tz='UTC')  # 5 days minute
    minute_df = pd.DataFrame({'datetime': rng_min, 'price': (100 + np.cumsum(np.random.randn(len(rng_min))*0.01)).round(4)})
    rng_tick = pd.date_range(end=pd.Timestamp.utcnow(), periods=24*60*10, freq='T', tz='UTC')  # simulate many ticks in 1 day
    tick_df = pd.DataFrame({'datetime': rng_tick, 'price': (100 + np.cumsum(np.random.randn(len(rng_tick))*0.005)).round(4)})
else:
    # attempt to load user CSVs
    try:
        if daily_file:
            df_daily = pd.read_csv(daily_file, parse_dates=True)
            # try common column names
            if 'date' in df_daily.columns:
                daily_df = df_daily.rename(columns={'date':'datetime'}).loc[:, ['datetime', 'price']]
            elif 'datetime' in df_daily.columns:
                daily_df = df_daily.loc[:, ['datetime','price']]
            else:
                st.error("Daily CSV missing 'date' or 'datetime' column.")
                st.stop()
        else:
            st.warning("Upload daily CSV or use demo data.")
            st.stop()

        if minute_file:
            df_min = pd.read_csv(minute_file, parse_dates=True)
            if 'datetime' in df_min.columns:
                minute_df = df_min.loc[:, ['datetime','price']]
            else:
                # try 'timestamp'
                if 'timestamp' in df_min.columns:
                    minute_df = df_min.rename(columns={'timestamp':'datetime'}).loc[:, ['datetime','price']]
                else:
                    st.error("Minute CSV missing 'datetime' or 'timestamp' column.")
                    st.stop()
        else:
            st.warning("Upload minute CSV or use demo data.")
            st.stop()

        if tick_file:
            df_tick = pd.read_csv(tick_file, parse_dates=True)
            if 'datetime' in df_tick.columns:
                tick_df = df_tick.loc[:, ['datetime','price']]
            elif 'timestamp' in df_tick.columns:
                tick_df = df_tick.rename(columns={'timestamp':'datetime'}).loc[:, ['datetime','price']]
            else:
                st.error("Tick CSV missing 'datetime' or 'timestamp' column.")
                st.stop()
        else:
            st.warning("Upload tick CSV or use demo data.")
            st.stop()

        # ensure all are timezone-aware UTC
        for d in (daily_df, minute_df, tick_df):
            d['datetime'] = pd.to_datetime(d['datetime']).dt.tz_localize('UTC', ambiguous='infer', nonexistent='shift_forward')

    except Exception as e:
        st.exception(e)
        st.stop()

# Merge into unified timeline
with st.spinner("Merging time series..."):
    full = unify_price_series(daily_df, minute_df, tick_df)

# If empty
if full.empty:
    st.error("Merged price series is empty — check your files.")
    st.stop()

# -------------------------
# Range selector (default = Prior Day)
# -------------------------
range_options = ['Prior Day','1d','5d','1w','1m','3m','6m','1y','3y','5y','10y','All']
default_range = 'Prior Day'
range_choice = st.selectbox("Select timeframe", range_options, index=range_options.index(default_range))

view_df = filter_by_range(full, range_choice)
if view_df.empty:
    st.warning("No data in selected range. Try a larger range.")
    
# -------------------------
# Chart + side controls
# -------------------------
col1, col2 = st.columns([3,1])

with col1:
    st.subheader(f"WPU Price — {range_choice}")
    fig = plot_price(view_df)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Holdings & Trading")
    # initialize session state
    if 'wpu_balance' not in st.session_state:
        st.session_state.wpu_balance = 0.0
    if 'cash_balance' not in st.session_state:
        st.session_state.cash_balance = 100000.0  # starting cash for demo
    if 'ledger' not in st.session_state:
        st.session_state.ledger = []  # list of trades

    latest_price = float(full['price'].iloc[-1])
    st.metric("Latest Price", f"{latest_price:.4f}")
    st.metric("WPU Holdings", f"{st.session_state.wpu_balance:.4f}")
    st.metric("Cash Balance", f"${st.session_state.cash_balance:,.2f}")

    amt = st.number_input("Amount (WPU)", min_value=0.0, step=0.01, value=1.0, format="%.4f")
    col_buy, col_sell = st.columns(2)
    with col_buy:
        if st.button("Buy"):
            cost = amt * latest_price
            if cost > st.session_state.cash_balance:
                st.error("Insufficient cash to buy.")
            else:
                # execute
                st.session_state.cash_balance -= cost
                st.session_state.wpu_balance += amt
                st.session_state.ledger.append({
                    'ts': datetime.utcnow().isoformat() + 'Z',
                    'side': 'BUY',
                    'amount': amt,
                    'price': latest_price,
                    'cash_after': st.session_state.cash_balance,
                    'wpu_after': st.session_state.wpu_balance
                })
                st.success(f"Bought {amt:.4f} WPU at {latest_price:.4f} — cost ${cost:,.2f}")

    with col_sell:
        if st.button("Sell"):
            if amt > st.session_state.wpu_balance:
                st.error("Insufficient WPU to sell.")
            else:
                proceeds = amt * latest_price
                st.session_state.cash_balance += proceeds
                st.session_state.wpu_balance -= amt
                st.session_state.ledger.append({
                    'ts': datetime.utcnow().isoformat() + 'Z',
                    'side': 'SELL',
                    'amount': amt,
                    'price': latest_price,
                    'cash_after': st.session_state.cash_balance,
                    'wpu_after': st.session_state.wpu_balance
                })
                st.success(f"Sold {amt:.4f} WPU at {latest_price:.4f} — proceeds ${proceeds:,.2f}")

    st.markdown("---")
    st.subheader("Position P&L")
    position_value = st.session_state.wpu_balance * latest_price
    total_equity = st.session_state.cash_balance + position_value
    st.write(f"Position market value: ${position_value:,.2f}")
    st.write(f"Total equity: ${total_equity:,.2f}")

    st.markdown("---")
    st.subheader("Trade Ledger (most recent)")
    ledger_df = pd.DataFrame(st.session_state.ledger[::-1])  # show recent first
    if not ledger_df.empty:
        st.dataframe(ledger_df.head(10))
    else:
        st.write("No trades yet.")

# -------------------------
# Footer: data summary + download
# -------------------------
st.markdown("---")
col_a, col_b = st.columns(2)
with col_a:
    st.write(f"Data range: {full['datetime'].min()}  to  {full['datetime'].max()}")
    st.write(f"Total samples: {len(full)}")
with col_b:
    if st.button("Download merged CSV"):
        tmp = full.copy()
        tmp['datetime'] = tmp['datetime'].astype(str)
        st.download_button("Download merged time series CSV", tmp.to_csv(index=False), file_name="wpu_merged.csv", mime="text/csv")

st.info("Tip: upload real CSVs or hit 'Use demo synthetic data' in the sidebar to see full functionality.")
