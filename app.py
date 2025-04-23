import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import base64
from io import StringIO
import re

# Page configuration
st.set_page_config(
    page_title="Stock Analysis Tool",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed" # Collapse sidebar on mobile by default
)

st.title("Stock Analysis Tool")
st.markdown("Enter a stock symbol to view financial data and analysis.")

# Function to get stock data
@st.cache_data(ttl=3600)  # Cache data for 1 hour
def get_stock_data(ticker, start_date, end_date):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(start=start_date, end=end_date)
        
        if hist.empty:
            return None, None, None
        
        # Get company info
        info = stock.info
        
        # Get financial data
        financial_data = {
            "Market Cap": info.get("marketCap", "N/A"),
            "P/E Ratio": info.get("trailingPE", "N/A"),
            "EPS": info.get("trailingEps", "N/A"),
            "52 Week High": info.get("fiftyTwoWeekHigh", "N/A"),
            "52 Week Low": info.get("fiftyTwoWeekLow", "N/A"),
            "Dividend Yield": info.get("dividendYield", "N/A"),
            "Beta": info.get("beta", "N/A"),
            "Average Volume": info.get("averageVolume", "N/A"),
            "Forward P/E": info.get("forwardPE", "N/A"),
            "Book Value": info.get("bookValue", "N/A"),
            "Price to Book": info.get("priceToBook", "N/A"),
        }
        
        # Format values
        for key, value in financial_data.items():
            if key == "Market Cap" and isinstance(value, (int, float)):
                if value >= 1_000_000_000:
                    financial_data[key] = f"${value/1_000_000_000:.2f}B"
                elif value >= 1_000_000:
                    financial_data[key] = f"${value/1_000_000:.2f}M"
            elif key == "Dividend Yield" and isinstance(value, (int, float)):
                financial_data[key] = f"{value*100:.2f}%" if value else "N/A"
            elif isinstance(value, (int, float)):
                financial_data[key] = f"{value:.2f}"
        
        # Create financial dataframe
        financial_df = pd.DataFrame({
            'Metric': list(financial_data.keys()),
            'Value': list(financial_data.values())
        })
        
        return hist, info, financial_df
    except Exception as e:
        st.error(f"Error retrieving data: {e}")
        return None, None, None

# Function to create downloadable link for CSV
def get_csv_download_link(df, filename="data.csv"):
    csv = df.to_csv(index=True)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download CSV File</a>'
    return href

# Function to plot stock data
def plot_stock_data(data, title, ticker=""):
    fig = go.Figure()
    
    # Add candlestick chart
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name="Price"
    ))
    
    # Add volume as bar chart
    fig.add_trace(go.Bar(
        x=data.index,
        y=data['Volume'],
        name='Volume',
        yaxis='y2',
        marker_color='rgba(0, 0, 255, 0.3)',
        opacity=0.5
    ))
    
    # Determine currency symbol based on ticker
    currency_symbol = "₹" if ".NS" in ticker or ".BO" in ticker else "$"
    
    # Update layout for better mobile experience
    fig.update_layout(
        title=title,
        xaxis_title='Date',
        yaxis_title=f'Price ({currency_symbol})',
        xaxis_rangeslider_visible=True,  # Enable rangeslider for easier navigation
        xaxis_rangeslider_thickness=0.05,  # Make rangeslider thin
        dragmode='pan',  # Set default interaction mode to pan instead of zoom
        yaxis2=dict(
            title='Volume',
            overlaying='y',
            side='right',
            showgrid=False
        ),
        height=500,  # Slightly smaller height for mobile
        margin=dict(l=10, r=10, t=50, b=10),  # Tighter margins
        hovermode='closest',  # Better hover experience
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        # Improve touch interaction
        modebar=dict(
            orientation='v',
            bgcolor='rgba(255,255,255,0.7)',
        )
    )
    
    # Add buttons to make mobile navigation easier
    if len(data.index) >= 90:  # Only add buttons if we have enough data
        fig.update_layout(
            updatemenus=[
                dict(
                    type="buttons",
                    direction="right",
                    x=0.1,
                    y=1.1,
                    showactive=True,
                    buttons=[
                        dict(
                            label="1M",
                            method="relayout",
                            args=[{"xaxis.range": [data.index[-min(30, len(data.index))].timestamp()*1000, data.index[-1].timestamp()*1000]}]
                        ),
                        dict(
                            label="3M",
                            method="relayout",
                            args=[{"xaxis.range": [data.index[-min(90, len(data.index))].timestamp()*1000, data.index[-1].timestamp()*1000]}]
                        ),
                        dict(
                            label="All",
                            method="relayout",
                            args=[{"xaxis.autorange": True}]
                        )
                    ]
                )
            ]
        )
    
    return fig

# Function to handle stock ticker symbols
def format_ticker(ticker):
    """Format ticker symbols for different exchanges"""
    ticker = ticker.upper().strip()
    
    # Check if it's an Indian stock (BSE/NSE) without exchange suffix
    indian_stock_pattern = r'^[A-Z]+$'
    if re.match(indian_stock_pattern, ticker) and ticker not in ['AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'TSLA', 'NFLX']:
        # Try to check if this might be an Indian stock
        try:
            # Check if NSE version exists
            test = yf.Ticker(f"{ticker}.NS")
            info = test.info
            if info and 'shortName' in info:
                return f"{ticker}.NS"
        except:
            pass
    
    return ticker

# Sidebar - User inputs
with st.sidebar:
    st.header("Stock Selection")
    ticker_input = st.text_input("Enter Stock Symbol (e.g., AAPL, APOLLOHOSP.NS):", "AAPL")
    ticker = format_ticker(ticker_input)
    
    # Show help for Indian stocks
    with st.expander("Help with Stock Symbols"):
        st.markdown("""
        ### Stock Symbol Formats:
        - **US Stocks**: Use the regular symbol (e.g., AAPL, MSFT)
        - **Indian NSE Stocks**: Add '.NS' suffix (e.g., RELIANCE.NS, APOLLOHOSP.NS)
        - **Indian BSE Stocks**: Add '.BO' suffix (e.g., RELIANCE.BO, APOLLOHOSP.BO)
        - **Other International Markets**: Check Yahoo Finance for the correct suffix
        """)
    
    st.header("Date Range")
    today = datetime.now()
    
    # Predefined date ranges
    date_ranges = {
        "1 Month": today - timedelta(days=30),
        "3 Months": today - timedelta(days=90),
        "6 Months": today - timedelta(days=180),
        "1 Year": today - timedelta(days=365),
        "5 Years": today - timedelta(days=365*5),
        "Custom": None
    }
    
    selected_range = st.selectbox("Select Period:", list(date_ranges.keys()))
    
    if selected_range == "Custom":
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", today - timedelta(days=365))
        with col2:
            end_date = st.date_input("End Date", today)
    else:
        start_date = date_ranges[selected_range]
        end_date = today
        st.info(f"Selected period: {selected_range} ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})")

# Add a "mobile-friendly" notice at the top
st.markdown("""
<div style="background-color: #f0f2f6; padding: 8px; border-radius: 5px; margin-bottom: 10px;">
    <h4 style="margin: 0;">📱 Mobile Controls</h4>
    <p style="margin: 5px 0 0 0; font-size: 0.9em;">
        • <b>Drag</b> to move chart<br>
        • <b>Pinch</b> to zoom in/out<br>
        • Use <b>range slider</b> at bottom to browse data<br>
        • Try the <b>1M/3M</b> buttons for quick views
    </p>
</div>
""", unsafe_allow_html=True)

# Main content
if ticker:
    # Show loading spinner
    with st.spinner(f"Loading data for {ticker}..."):
        stock_data, stock_info, financial_data = get_stock_data(ticker, start_date, end_date)

    if stock_data is not None and not stock_data.empty:
        # Display company info
        col1, col2 = st.columns([3, 1])
        
        with col1:
            company_name = stock_info.get('longName', ticker)
            st.header(f"{company_name} ({ticker})")
            
            # Display company description with a read more/less toggle
            if stock_info.get('longBusinessSummary'):
                with st.expander("Company Description"):
                    st.write(stock_info.get('longBusinessSummary'))
        
        with col2:
            # Display current price and change
            latest_day = stock_data.index[-1]
            previous_day = stock_data.index[-2] if len(stock_data.index) > 1 else stock_data.index[0]
            
            current_price = stock_data['Close'].iloc[-1]
            previous_price = stock_data['Close'].iloc[stock_data.index.get_loc(previous_day)]
            price_change = current_price - previous_price
            price_change_pct = (price_change / previous_price) * 100
            
            currency_symbol = "₹" if ".NS" in ticker or ".BO" in ticker else "$"
            st.metric(
                "Current Price",
                f"{currency_symbol}{current_price:.2f}",
                f"{price_change:.2f} ({price_change_pct:.2f}%)",
                delta_color="normal" if price_change >= 0 else "inverse"
            )
            
            # Display trading information
            latest_date_str = latest_day.strftime('%Y-%m-%d')
            st.write(f"**As of:** {latest_date_str}")
        
        # Tabs for different visualizations
        tab1, tab2 = st.tabs(["Price Chart", "Financial Information"])
        
        with tab1:
            # Plot the stock data
            st.subheader(f"{ticker} Stock Price Chart")
            fig = plot_stock_data(stock_data, f"{company_name} ({ticker}) Stock Price", ticker)
            st.plotly_chart(fig, use_container_width=True)
            
            # Add some statistics
            st.subheader("Price Statistics")
            col1, col2, col3, col4 = st.columns(4)
            
            currency_symbol = "₹" if ".NS" in ticker or ".BO" in ticker else "$"
            with col1:
                st.metric("Highest", f"{currency_symbol}{stock_data['High'].max():.2f}")
            with col2:
                st.metric("Lowest", f"{currency_symbol}{stock_data['Low'].min():.2f}")
            with col3:
                st.metric("Average", f"{currency_symbol}{stock_data['Close'].mean():.2f}")
            with col4:
                st.metric("Volume (Avg)", f"{stock_data['Volume'].mean():.0f}")
        
        with tab2:
            st.subheader("Key Financial Metrics")
            
            # Display the financial metrics in a table
            st.dataframe(financial_data, use_container_width=True)
            
            # Add download button for financial data
            st.markdown(get_csv_download_link(financial_data, f"{ticker}_financial_metrics.csv"), unsafe_allow_html=True)
            
            # Historical Data
            st.subheader("Historical Stock Data")
            st.dataframe(stock_data.reset_index(), use_container_width=True)
            
            # Add download button for historical data
            st.markdown(get_csv_download_link(stock_data, f"{ticker}_historical_data_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"), unsafe_allow_html=True)
    
    else:
        st.error(f"No data found for ticker '{ticker}'. Please check the symbol and try again.")
else:
    # Display default instructions
    st.info("Enter a stock symbol in the sidebar to begin analysis.")
    st.markdown("""
    ### How to use this tool:
    1. Enter a valid stock ticker symbol in the sidebar (e.g., AAPL for Apple Inc.)
    2. Select a date range for historical data
    3. View the company information, stock price chart, and key financial metrics
    4. Download data as CSV for further analysis
    
    ### Available Information:
    - **Price Chart**: Historical stock price with candlestick pattern and volume
    - **Financial Metrics**: Key metrics like Market Cap, P/E Ratio, EPS, etc.
    - **Historical Data**: Complete historical data for the selected period
    """)

# Add footer with explanatory tooltips
st.markdown("---")
with st.expander("Financial Terms Glossary"):
    st.markdown("""
    - **Market Cap**: Total market value of a company's outstanding shares.
    - **P/E Ratio**: Price-to-Earnings ratio, valuation metric comparing share price to earnings per share.
    - **EPS**: Earnings Per Share, a company's profit divided by outstanding shares.
    - **Dividend Yield**: Annual dividend payment divided by stock price, expressed as percentage.
    - **Beta**: Measure of stock's volatility compared to the market. >1 means more volatile than market.
    - **52 Week High/Low**: Highest and lowest price points in the past year.
    - **Forward P/E**: P/E calculated using projected future earnings.
    - **Book Value**: Net asset value of a company (total assets minus liabilities).
    - **Price to Book**: Ratio of market price to book value per share.
    """)

st.markdown("Data provided by Yahoo Finance via yfinance")
