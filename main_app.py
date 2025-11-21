import streamlit as st
from wpu.data_loader import read_daily_wpu, read_minute_wpu, read_tick_wpu
from wpu.processing import merge_resample_forward_fill, filter_by_zoom
from wpu.plotting import plot_price_line

st.title("WPU Currency Basket Viewer")

# Upload files
daily_file = st.sidebar.file_uploader("Upload daily CSV (10 years)", type=['csv'])
minute_file = st.sidebar.file_uploader("Upload minute CSV/XLSX (5 days)", type=['csv','xlsx'])
tick_file = st.sidebar.file_uploader("Upload tick CSV/XLSX (1 day)", type=['csv','xlsx'])

# Zoom selector
zoom_option = st.sidebar.selectbox(
    "Select time range",
    ['1d','5d','1w','1m','3m','6m','1y','3y','5y','10y'],
    index=0
)

daily_raw = daily_tidy = None
minute_raw = minute_tidy = None
tick_tidy = None

if daily_file is not None:
    daily_raw, daily_tidy, _ = read_daily_wpu(daily_file)

if minute_file is not None:
    minute_raw, minute_tidy, _ = read_minute_wpu(minute_file)

if tick_file is not None:
    tick_tidy = read_tick_wpu(tick_file)

if daily_tidy is not None:
    merged_df = merge_resample_forward_fill(daily_tidy, minute_tidy, tick_tidy)
    zoomed_df = filter_by_zoom(merged_df, zoom=zoom_option)
    plot_price_line(zoomed_df, price_col='price', title=f"WPUUSD Price ({zoom_option})")
