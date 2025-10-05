import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from scipy.signal import find_peaks
from datetime import date, datetime, timedelta


st.set_page_config(page_title="Stock Extrema Finder", layout="wide")
st.title("Stock Extrema Finder")


# LOGIC
# @st.cache_data(ttl=3600, show_spinner=False)
def fetch_data(ticker: str, start_date: date, end_date: date) -> pd.DataFrame:
    """Fetch historical data for a given ticker and date range using yfinance."""
    data = yf.download(ticker, start=start_date, end=end_date + timedelta(days=1))
    if data.empty or data is None:
        raise ValueError(f"No data found for ticker {ticker} in the given date range.")
    return data


def clean_data(data: pd.DataFrame) -> pd.DataFrame:
    data_cp = data.copy()
    data_cp.columns = data.columns.droplevel(1)  # need to drop company name level
    return data_cp


def find_extrema(
    data: pd.DataFrame, column, prominence_factor=0.4, maximum=True
) -> pd.DataFrame:
    """Find specified number of minimas or maximas in the given column of the data."""
    if column not in data.columns:
        raise ValueError(f"Column {column} not found in data.")
    # Ensure the column data is a 1-D array
    column_data = data[column].dropna().values.squeeze()
    # Find extrema
    if not maximum:
        column_data = -column_data
    price_range = column_data.max() - column_data.min()
    prominence = price_range * prominence_factor  # Adjust prominence as needed
    extrema_indices, _ = find_peaks(column_data, prominence=prominence)
    # extrema_indices =
    extrema = data.iloc[extrema_indices]
    # .nlargest(peak_count, column)

    return extrema


def ensure_maximum_after_minimum(
    low_minima, high_maxima
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns first minimum followed by the first maximum after it."""
    minimum = low_minima.iloc[[0]]  # purposefuly keeping dataframe format
    maximum = high_maxima[high_maxima.index > minimum.index].iloc[[0]]
    return minimum, maximum


def plot_candlestick(fig: go.Figure, data: pd.DataFrame) -> None:
    """Plot a candlestick chart with extrema points using Plotly."""
    # Candlestick
    fig.update_layout(
        title="Candlestick Chart with Extrema",
        xaxis_title="Date",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
    )
    fig.add_trace(
        go.Candlestick(
            x=data.index,
            open=data["Open"],
            high=data["High"],
            low=data["Low"],
            close=data["Close"],
            name="Candlestick",
        )
    )


def plot_extrema(
    fig: go.Figure,
    data: pd.DataFrame,
    low_minima: pd.DataFrame,
    high_maxima: pd.DataFrame,
) -> None:
    if not low_minima.empty:
        fig.add_trace(
            go.Scatter(
                x=low_minima.index,
                y=low_minima["Low"],
                mode="markers",
                marker=dict(color="red", size=10),
                name="Low Minima",
            )
        )
    # High maximas
    if not high_maxima.empty:
        fig.add_trace(
            go.Scatter(
                x=high_maxima.index,
                y=high_maxima["High"],
                mode="markers",
                marker=dict(color="green", size=10),
                name="High Maxima",
            )
        )
    # fig.show()

    # plot a line between first high and minimum low, then between minimum low and maximum high, then between maximum high and last low
    # A->B->C
    if not low_minima.empty and not high_maxima.empty:
        fig.add_trace(
            go.Scatter(
                x=[
                    data.index.min(),
                    low_minima.index.min(),
                    high_maxima.index.max(),
                    data.index.max(),
                ],
                y=[
                    data["High"].iloc[0],
                    low_minima["Low"].iloc[0],
                    high_maxima["High"].iloc[0],
                    data["Low"].iloc[-1],
                ],
                mode="lines+markers",
                line=dict(color="blue", width=2, dash="dash"),
                marker=dict(color="blue", size=8),
                name="A-B-C Line",
            )
        )


def table_summary(data, low_minima, high_maxima) -> pd.DataFrame:
    summary = pd.DataFrame(
        {
            "A-Start-date": [data.index.min().strftime("%Y-%m-%d")],
            "A-High": [round(data["High"].iloc[0], 2)],
            "AB-Start-date": [
                low_minima.index.min().strftime("%Y-%m-%d")
                if not low_minima.empty
                else ""
            ],
            "B-Low": [
                round(low_minima["Low"].iloc[0], 2) if not low_minima.empty else ""
            ],
            "BC-Start-date": [
                high_maxima.index.max().strftime("%Y-%m-%d")
                if not high_maxima.empty
                else ""
            ],
            "C-High": [
                round(high_maxima["High"].iloc[0], 2) if not high_maxima.empty else ""
            ],
            "C-End-date": [data.index.max().strftime("%Y-%m-%d")],
            "C-Low": [round(data["Low"].iloc[-1], 2)],
        }
    )
    return summary


st.sidebar.header("Input Parameters")

# Defining input variables
DEFAULT_TICKER = "BLK"
DEFAULT_END = datetime.today()
DEFAULT_START = DEFAULT_END - timedelta(days=30)
DEFAULT_PROMINENCE_FACTOR = 0.4  # also tested to be the best if ensure_... applied

ticker = st.sidebar.text_input("Enter ticker symbol", DEFAULT_TICKER)

start_date = st.sidebar.date_input("Start date", DEFAULT_START)
end_date = st.sidebar.date_input("End date", DEFAULT_END)

prominence_factor = st.sidebar.slider(
    "Prominence factor", 0.1, 0.9, DEFAULT_PROMINENCE_FACTOR, 0.1
)

process_button = st.sidebar.button("Calculate Extremas")

# Interactive logic

if process_button:
    try:
        with st.spinner("Fetching and processing data..."):
            data = fetch_data(ticker, start_date, end_date)
            data = clean_data(data)
            fig = go.Figure()

            plot_candlestick(fig, data)

            low_minima = find_extrema(
                data, "Low", prominence_factor=prominence_factor, maximum=False
            )
            high_maxima = find_extrema(
                data, "High", prominence_factor=prominence_factor, maximum=True
            )
            if len(low_minima) > 1 or len(high_maxima) > 1:
                low_minima, high_maxima = ensure_maximum_after_minimum(
                    low_minima, high_maxima
                )
            elif low_minima.empty or high_maxima.empty:
                st.warning(
                    "Could not find sufficient extrema points, displaying what 'we have'"
                )
            plot_extrema(fig, data, low_minima, high_maxima)

        st.plotly_chart(fig, use_container_width=True)
        st.table(table_summary(data, low_minima, high_maxima))
    except Exception as e:
        st.error(f"An error occurred: {e}")
#
# if st.button("Clear Cache"):
#     # Clear all st.cache_data caches
#     st.cache_data.clear()
#     st.write("Cache cleared!")
