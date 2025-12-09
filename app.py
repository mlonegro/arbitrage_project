import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pyRofex
import os

# Import classes
try:
    from real_feed import RealFeed
    from scraper_feed import ScraperFeed
    from market_monitor import ArbMonitor
except ImportError as e:
    st.error(f"❌ Import Error: {e}")
    st.stop()

st.set_page_config(page_title="Rofex Arb Monitor", layout="wide", page_icon="💸", initial_sidebar_state="expanded")

# Custom CSS for light, professional appearance
st.markdown("""
<style>
    /* Force light theme */
    .stApp {
        background-color: #FFFFFF;
    }

    /* Main title styling */
    h1 {
        color: #1565C0 !important;
        font-weight: 700 !important;
        padding-bottom: 20px;
        border-bottom: 3px solid #1565C0;
        margin-bottom: 30px;
    }

    /* Subheader styling */
    h2, h3 {
        color: #1565C0 !important;
        font-weight: 600 !important;
        margin-top: 30px;
        margin-bottom: 15px;
    }

    /* Metric cards enhancement */
    div[data-testid="stMetric"] {
        background-color: #F5F5F5;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #E0E0E0;
    }

    [data-testid="stMetricValue"] {
        font-size: 32px !important;
        font-weight: 700 !important;
        color: #1565C0 !important;
    }

    [data-testid="stMetricLabel"] {
        font-size: 14px !important;
        font-weight: 600 !important;
        color: #424242 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    [data-testid="stMetricDelta"] {
        font-size: 13px !important;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #F8F9FA;
        border-right: 2px solid #E0E0E0;
    }

    [data-testid="stSidebar"] h2 {
        color: #1565C0 !important;
    }

    /* Table styling */
    [data-testid="stDataFrame"] {
        border: 2px solid #E0E0E0;
        border-radius: 8px;
        overflow: hidden;
        background-color: #FFFFFF;
    }

    /* Better spacing */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        background-color: #FFFFFF;
    }

    /* Expander styling */
    [data-testid="stExpander"] {
        background-color: #F5F5F5;
        border: 1px solid #E0E0E0;
        border-radius: 8px;
    }

    /* Caption text */
    .caption {
        color: #666666 !important;
    }

    /* General text */
    p, span, div {
        color: #212121;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuration")

    # 1. Select Mode
    env_mode = st.radio("Data Feed", ["ROFEX API (Real)", "Ambito Financiero (Diario)", "Simulation (Mock)"])
    
    st.divider()
    
    # 2. Financial Inputs
    st.subheader("Market Assumptions")
    # Default to 35% but allow range
    caucion_tna = st.slider("Funding Rate (Caución TNA)", 0.0, 0.80, 0.35, 0.01)
    st.caption(f"Daily Cost: {caucion_tna/365:.4%}")
    
    st.divider()
    
    # 3. Simulation Inputs
    st.subheader("Execution Simulation")
    commission = st.slider("Commission (%)", 0.0, 0.5, 0.0, 0.01)
    
    # Only show Spread simulation if using Mock data (Ambito and ROFEX have real spreads)
    sim_spread = 0
    if env_mode == "Simulation (Mock)":
        sim_spread = st.slider("Simulated Spread (bps)", 0, 500, 50, 10, help="Widens the spread to simulate illiquidity.")

# --- MAIN APP ---
st.title("💰 Argentine Dollar Futures Arbitrage Monitor")

# 1. Initialize Feed
if 'feed' not in st.session_state:
    st.session_state['feed'] = None

current_feed = None

if env_mode == "ROFEX API (Real)":
    try:
        import toml
        secrets_path = os.path.join(os.path.dirname(__file__), '.streamlit', 'secrets.toml')
        if os.path.exists(secrets_path):
            secrets = toml.load(secrets_path)
            current_feed = RealFeed(
                username=secrets['ROFEX_USER'],
                password=secrets['ROFEX_PASSWORD'],
                account_id=secrets['ROFEX_ACCOUNT'],
                environment=pyRofex.Environment.REMARKET
            )
        else:
            st.error("❌ secrets.toml not found. Please configure ROFEX credentials.")
            st.stop()
    except Exception as e:
        st.error(f"❌ Failed to load credentials: {e}")
        st.stop()
elif env_mode == "Ambito Financiero (Diario)":
    # Use Ambito Financiero web scraper as fallback data source
    current_feed = ScraperFeed()
elif env_mode == "Simulation (Mock)":
    # We use RealFeed class just for its mock generator
    current_feed = RealFeed("dummy", "dummy", "dummy")

# 2. Fetch Data
snapshot = None
if current_feed:
    try:
        if env_mode == "ROFEX API (Real)":
            spinner_text = "Connecting to ROFEX API..."
        elif env_mode == "Ambito Financiero (Diario)":
            spinner_text = "Scraping Ambito Financiero..."
        else:
            spinner_text = f"Fetching data from {env_mode}..."

        with st.spinner(spinner_text):
            # use_mock_fallback=True allows Simulation mode to generate data
            snapshot = current_feed.get_snapshot(use_mock_fallback=(env_mode == "Simulation (Mock)"))
            
            # --- SIMULATION LAYER ---
            if snapshot and not snapshot.futures_chain.empty:
                df = snapshot.futures_chain
                
                # A. Synthetic Spread (Only for Mock)
                if sim_spread > 0:
                    half_spread = (sim_spread / 10000) / 2
                    df['Bid'] = df['Last'] * (1 - half_spread)
                    df['Ask'] = df['Last'] * (1 + half_spread)
                
                # B. Commission Drag (Applies to ALL modes)
                if commission > 0:
                    fee_factor = commission / 100
                    df['Bid'] = df['Bid'] * (1 - fee_factor)
                    df['Ask'] = df['Ask'] * (1 + fee_factor)
                
                snapshot.futures_chain = df
            
    except Exception as e:
        error_message = str(e)
        if "ROFEX API" in error_message or env_mode == "ROFEX API (Real)":
            st.error(f"❌ ROFEX API Error: {error_message}")
            st.warning("💡 **Suggestion:** Try switching to **'Ambito Financiero'** data source in the sidebar for a more reliable connection.")
        else:
            st.error(f"Data Error: {error_message}")

# 3. Display Results
if snapshot and not snapshot.futures_chain.empty:
    # Set Funding Rate from Slider
    detected_rate = snapshot.funding_rates.get('1d', 0.0)
    snapshot.funding_rates['1d'] = caucion_tna
    
    # Run Math
    monitor = ArbMonitor(risk_free_rate_tenor='1d')
    df = monitor.process_tick(snapshot)
    
    # KPI Section
    # Find best opportunities avoiding NaNs
    if not df.empty: 
        best_row = df.loc[df['Max_Spread_bps'].idxmax()]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Spot Price", f"${snapshot.spot_price:,.2f}" if snapshot.spot_price else "N/A")
        c2.metric("Caución (Input)", f"{caucion_tna:.2%}", delta=f"Mkt: {detected_rate:.2%}", delta_color="off")
        c3.metric("Best Spread", f"{best_row['Max_Spread_bps']:.0f} bps",
                  delta=best_row['Strategy'], delta_color="normal" if best_row['Max_Spread_bps'] > 0 else "inverse")
        c4.metric("Best Ticker", best_row['Ticker'])

        # Strategy explanation
        with st.expander("📚 Arbitrage Strategies Explained"):
            st.markdown("""
            ### **Strategy 1: Carry Trade (Sell Futures)**
            **When to use:** Market implied rate > Your funding rate (positive spread)

            **Steps:**
            1. **Borrow ARS** at your funding rate (Caución)
            2. **Buy USD spot** in the market
            3. **Sell USD futures** at the market's implied rate
            4. **At maturity:** Settle future, receive ARS, repay loan + interest
            5. **Profit:** Keep the difference between implied rate and funding rate

            ---

            ### **Strategy 2: Reverse Carry (Buy Futures)**
            **When to use:** Market implied rate < Your funding rate (negative spread on classic carry)

            **Steps:**
            1. **Borrow USD** (or use existing USD position)
            2. **Sell USD spot** for ARS
            3. **Deposit ARS** at your funding rate (Caución)
            4. **Buy USD futures** at market's lower implied rate
            5. **At maturity:** Settle future with USD, collect ARS deposit + interest
            6. **Profit:** Keep the difference between your funding rate and implied rate

            ---

            💡 **Key Insight:** You're exploiting the difference between what the market thinks the devaluation will be (implied rate)
            versus what you can actually borrow/lend at (funding rate).
            """)

        # Debug info
        with st.expander("🔍 Calculation Details (Debug)"):
            st.caption(f"**Spot Reference:** ${snapshot.spot_price:.2f} (from Ámbito Mayorista)")
            st.caption(f"**Best Contract:** {best_row['Ticker']} @ {best_row['Days']} days")
            st.caption(f"**Best Bid:** ${best_row['Bid']:.2f} | **Ask:** ${best_row['Ask']:.2f}")
            st.caption(f"**Implied TNA (Bid):** {best_row['Implied_TNA_Bid']:.2%}")
            st.caption(f"**Funding Rate (Input):** {caucion_tna:.2%}")
            st.caption(f"**Spread Formula:** ({best_row['Implied_TNA_Bid']:.2%} - {caucion_tna:.2%}) × 10,000 = {best_row['Max_Spread_bps']:.0f} bps")

        # Chart Section
        st.subheader("📈 Implied Rate Term Structure")

        # Sort data by Days for cleaner chart
        df_sorted = df.sort_values('Days')

        fig = go.Figure()

        # Plot Implied Yield from Futures (when you SELL futures)
        fig.add_trace(go.Scatter(
            x=df_sorted['Days'],
            y=df_sorted['Implied_TNA_Bid'],
            mode='lines+markers',
            name='Futures Implied Rate (Sell Future)',
            line=dict(color='#2E86AB', width=3),
            marker=dict(size=8, symbol='circle'),
            hovertemplate='<b>%{x} days</b><br>Implied Rate: %{y:.2%}<extra></extra>'
        ))

        # Plot Funding Cost Reference Line
        fig.add_trace(go.Scatter(
            x=df_sorted['Days'],
            y=[caucion_tna]*len(df_sorted),
            mode='lines',
            name=f'Funding Cost (Caución {caucion_tna:.1%})',
            line=dict(color='#F77F00', width=3, dash='dash'),
            hovertemplate='<b>Funding Rate</b><br>%{y:.2%}<extra></extra>'
        ))

        # Add shaded region for positive arbitrage
        fig.add_trace(go.Scatter(
            x=df_sorted['Days'].tolist() + df_sorted['Days'].tolist()[::-1],
            y=df_sorted['Implied_TNA_Bid'].tolist() + [caucion_tna]*len(df_sorted),
            fill='toself',
            fillcolor='rgba(46, 134, 171, 0.1)',
            line=dict(width=0),
            showlegend=False,
            hoverinfo='skip'
        ))

        fig.update_layout(
            height=450,
            template="plotly_white",
            title=dict(
                text="Market Implied Devaluation vs Your Funding Cost",
                font=dict(size=16, color='#1565C0')
            ),
            yaxis=dict(
                title="Annualized Rate (TNA)",
                tickformat='.1%',
                gridcolor='#E0E0E0',
                tickfont=dict(size=14, color='#424242'),
            ),
            xaxis=dict(
                title="Days to Maturity",
                gridcolor='#E0E0E0',
                tickfont=dict(size=14, color='#424242'),
            ),
            hovermode="x unified",
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor='rgba(255,255,255,0.9)',
                bordercolor='#E0E0E0',
                borderwidth=1,
                font=dict(size=12, color='#212121')
            ),
            plot_bgcolor='#FAFAFA',
            paper_bgcolor='#FFFFFF'
        )

        st.plotly_chart(fig, use_container_width=True)

        # Add interpretation note
        st.caption("💡 **How to read:** When blue line is above orange line, you can profit by selling futures and borrowing at your funding rate.")

        # Table Section
        st.subheader("📊 Contracts Overview")

        # Filter for contracts with valid bid/ask prices only
        df_display = df[(df['Bid'].notna()) & (df['Ask'].notna())].copy()

        if df_display.empty:
            st.warning("No contracts with valid bid/ask quotes found.")
        else:
            # Sort by Days (shortest expiry first)
            df_display = df_display.sort_values('Days').reset_index(drop=True)

            # Simplified columns - only essential trading info
            cols_display = [
                'Ticker',
                'Maturity',
                'Days',
                'Bid',
                'Ask',
                'Strategy',
                'Max_Spread_bps'
            ]

            # Custom color function for spreads (light theme)
            def color_spread(val):
                try:
                    v = float(val)
                    if v > 100:
                        return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold'
                    elif v > 0:
                        return 'background-color: #E8F5E9; color: #2E7D32'
                    elif v < 0:
                        return 'background-color: #FFCDD2; color: #C62828'
                    else:
                        return 'background-color: #F5F5F5; color: #424242'
                except:
                    return ''

            styled_df = df_display[cols_display].style.format({
                'Maturity': lambda x: x.strftime('%b %d, %Y') if pd.notna(x) else 'N/A',
                'Bid': lambda x: f'${x:.2f}' if pd.notna(x) else 'N/A',
                'Ask': lambda x: f'${x:.2f}' if pd.notna(x) else 'N/A',
                'Max_Spread_bps': lambda x: f'{x:.0f}' if pd.notna(x) else 'N/A'
            }).applymap(color_spread, subset=['Max_Spread_bps'])

            st.table(styled_df)

            # Add legend
            st.caption("🟢 **Green:** Positive spread (arbitrage opportunity) | 🔴 **Red:** Negative spread")
    else:
        st.warning("Data fetched but no valid rows found (check scraped data format).")

else:
    st.info("👈 Waiting for data... Check your internet connection if scraping.")