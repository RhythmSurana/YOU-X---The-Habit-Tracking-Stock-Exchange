import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import sqlite3
import time

# --- 1. THEME & CSS INJECTION (UPDATED TO HIDE HEADER) ---
st.set_page_config(layout="wide", page_title="YOU-X TERMINAL", page_icon="📟")


def apply_terminal_theme():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;700&display=swap');

        /* HIDE DEFAULT STREAMLIT ELEMENTS TO PREVENT CLIPPING */
        header {visibility: hidden;}
        footer {visibility: hidden;}
        #MainMenu {visibility: hidden;}

        /* DARK BACKGROUND */
        .stApp, .main, .stSidebar {
            background-color: #050505 !important;
            color: #00FF41 !important;
            font-family: 'Fira Code', monospace !important;
        }

        /* METRICS */
        [data-testid="stMetricValue"] { color: #00FF41 !important; }
        .stMetric {
            background: #0a0a0a !important;
            border: 1px solid #1a1a1a !important;
            padding: 15px !important;
        }

        /* BUTTONS: COMPLETE = GREEN, MISS = RED */
        div[data-testid="column"] .stButton:nth-of-type(1) button {
            border: 1px solid #00FF41 !important;
            color: #00FF41 !important;
            background-color: transparent !important;
        }
        div[data-testid="column"] .stButton:nth-of-type(1) button:hover {
            background-color: #00FF41 !important;
            color: #000 !important;
        }

        div[data-testid="column"] .stButton:nth-of-type(2) button {
            border: 1px solid #FF3131 !important;
            color: #FF3131 !important;
            background-color: transparent !important;
        }
        div[data-testid="column"] .stButton:nth-of-type(2) button:hover {
            background-color: #FF3131 !important;
            color: #fff !important;
        }

        [data-testid="stSidebar"] .stButton button {
            border: 1px solid #FF3131 !important;
            color: #FF3131 !important;
        }

        input {
            background-color: #0a0a0a !important;
            color: #00FF41 !important;
            border: 1px solid #00FF41 !important;
        }

        /* Set top padding to zero since we are using a custom ticker header */
        .block-container { padding-top: 0rem !important; }
        </style>
    """, unsafe_allow_html=True)


apply_terminal_theme()


# --- 2. DATABASE ---
def init_db():
    conn = sqlite3.connect('youx_v3.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS portfolio
                 (
                     ticker
                     TEXT
                     PRIMARY
                     KEY,
                     name
                     TEXT,
                     price
                     REAL,
                     streak
                     INTEGER
                 )''')
    c.execute('''CREATE TABLE IF NOT EXISTS history
                 (
                     id
                     INTEGER
                     PRIMARY
                     KEY
                     AUTOINCREMENT,
                     ticker
                     TEXT,
                     date
                     TEXT,
                     status
                     TEXT,
                     price
                     REAL
                 )''')
    c.execute("SELECT count(*) FROM portfolio")
    if c.fetchone()[0] == 0:
        assets = [('$GYM', 'Health', 100.0, 0), ('$CODE', 'Skill', 100.0, 0), ('$SLEEP', 'Recovery', 100.0, 0)]
        c.executemany("INSERT INTO portfolio VALUES (?,?,?,?)", assets)
    conn.commit()
    return conn


db = init_db()


# --- 3. THE ENGINE ---
def execute_trade(ticker, status):
    c = db.cursor()
    c.execute("SELECT price, streak FROM portfolio WHERE ticker=?", (ticker,))
    result = c.fetchone()
    if not result: return

    price, streak = result
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if status == "COMPLETE":
        new_streak = streak + 1
        gain = 0.05 + (new_streak * 0.005)
        new_price = price * (1 + gain)
        st.toast(f"TRADE FILLED: {ticker}", icon="💹")
    else:
        new_streak = 0
        new_price = price * 0.80
        st.toast(f"MARGIN CALL: {ticker}", icon="🚨")

    c.execute("UPDATE portfolio SET price=?, streak=? WHERE ticker=?", (new_price, new_streak, ticker))
    c.execute("INSERT INTO history (ticker, date, status, price) VALUES (?,?,?,?)", (ticker, now, status, new_price))
    db.commit()
    time.sleep(0.4)
    st.rerun()


def delist_asset(ticker):
    c = db.cursor()
    c.execute("DELETE FROM portfolio WHERE ticker=?", (ticker,))
    db.commit()
    st.rerun()


# --- 4. TOP UI: TICKER BAR (FIXED CLIPPING) ---
def render_ticker_bar(df):
    ticker_items = ""
    for _, row in df.iterrows():
        color = "#00FF41" if row['price'] >= 100 else "#FF3131"
        ticker_items += f"""
            <span style="color:white; font-family:monospace; font-size:18px; padding: 0 50px;">
                {row['ticker']} <span style="color:{color}; font-weight:bold;">${row['price']:.2f}</span>
            </span>"""

    # Wrap in HTML/CSS with margin-top to clear the very top edge
    ticker_html = f"""
    <div style="background: black; border-bottom: 2px solid #00FF41; overflow: hidden; white-space: nowrap; width: 100%; padding: 12px 0; margin-top: 10px;">
        <div style="display: inline-block; animation: scroll 25s linear infinite;">
            {ticker_items * 5}
        </div>
    </div>
    <style>
        @keyframes scroll {{
            from {{ transform: translateX(0); }}
            to {{ transform: translateX(-50%); }}
        }}
        body {{ margin: 0; background-color: black; }}
    </style>
    """
    # Increased height slightly to accommodate the margin
    components.html(ticker_html, height=70)


# --- 5. DASHBOARD EXECUTION ---
all_assets = pd.read_sql_query("SELECT * FROM portfolio", db)

# Call the ticker function
render_ticker_bar(all_assets)

st.title("📟 YOU-X: ASSET MANAGER")

# Header Metrics
net_worth = all_assets['price'].sum()
m1, m2, m3 = st.columns(3)
with m1:
    st.metric("NET WORTH", f"${net_worth:.2f}", delta=f"{net_worth - 300:.2f}")
with m2:
    st.metric("ACCOUNT STATUS", "BLUE CHIP" if (all_assets['streak'].mean() >= 3) else "SUB-PRIME")
with m3:
    st.metric("ACTIVE SYMBOLS", len(all_assets))

st.divider()

# --- 6. ADMIN ---
with st.sidebar:
    st.header("🛠️ MARKET ADMIN")
    with st.expander("🚀 LAUNCH NEW IPO"):
        new_t = st.text_input("TICKER (e.g., $MEDITATE)").upper()
        if st.button("EXECUTE IPO"):
            if new_t:
                if not new_t.startswith('$'): new_t = '$' + new_t
                try:
                    c = db.cursor()
                    c.execute("INSERT INTO portfolio VALUES (?, 'Asset', 100.0, 0)", (new_t,))
                    db.commit()
                    st.rerun()
                except:
                    st.error("Exists.")

    with st.expander("🗑️ DELIST"):
        to_delete = st.selectbox("Liquidate", all_assets['ticker'].tolist() if not all_assets.empty else ["None"])
        if st.button("CONFIRM DELIST"):
            delist_asset(to_delete)

# --- 7. TRADING FLOOR ---
st.subheader("🚀 THE TRADING FLOOR")
if all_assets.empty:
    st.info("No active assets.")
else:
    cols = st.columns(len(all_assets))
    for i, row in all_assets.iterrows():
        with cols[i]:
            st.markdown(f"### {row['ticker']}")
            st.write(f"Value: **${row['price']:.2f}**")
            st.write(f"Streak: `{row['streak']}d`")
            if st.button(f"COMPLETE", key=f"c_{row['ticker']}"): execute_trade(row['ticker'], "COMPLETE")
            if st.button(f"MISS", key=f"m_{row['ticker']}"): execute_trade(row['ticker'], "MISS")

st.divider()

# --- 8. ANALYSIS ---
st.subheader("📊 MARKET ANALYSIS")
if not all_assets.empty:
    selected = st.selectbox("Symbol", all_assets['ticker'])
    h_df = pd.read_sql_query(f"SELECT * FROM history WHERE ticker='{selected}'", db)
    if not h_df.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(x=h_df['date'], y=h_df['price'], mode='lines+markers', line=dict(color='#00FF41', width=3),
                       fill='tozeroy', fillcolor='rgba(0, 255, 65, 0.1)'))
        fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)