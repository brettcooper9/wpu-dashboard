import streamlit as st
import altair as alt

def plot_price_line(df, price_col='price', title='WPU Price', width=800, height=400):
    """
    Plot a simple line chart of WPU prices
    """
    if df.empty or price_col not in df.columns:
        st.warning("No data to plot")
        return

    chart = alt.Chart(df).mark_line().encode(
        x='datetime:T',
        y=alt.Y(price_col, title='Price'),
        tooltip=['datetime:T', f'{price_col}:Q']
    ).properties(
        width=width,
        height=height,
        title=title
    ).interactive()

    st.altair_chart(chart, use_container_width=True)
