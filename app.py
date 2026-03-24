"""
🎯 Explosion Hunter v3.0 — Full Auto Mode
==========================================
- Auto-scans 1,160 Halal NYSE stocks every hour during market hours
- Email alerts when score >= 70
- Dashboard auto-refreshes — no manual clicks needed
- Batch processing with smart rate-limit handling
- Deployed on Railway.app for 24/7 uptime
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import warnings
import time
import concurrent.futures
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import json

warnings.filterwarnings('ignore')

# ============================================================
# CONFIG — From Railway Environment Variables
# ============================================================
GMAIL_ADDRESS = os.environ.get('GMAIL_ADDRESS', '')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD', '')
ALERT_TO_EMAIL = os.environ.get('ALERT_TO_EMAIL', GMAIL_ADDRESS)
SCAN_INTERVAL_MINUTES = int(os.environ.get('SCAN_INTERVAL', '60'))
ALERT_SCORE_THRESHOLD = int(os.environ.get('ALERT_THRESHOLD', '70'))

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(page_title='Explosion Hunter', page_icon='🎯', layout='centered', initial_sidebar_state='collapsed')

# ============================================================
# CSS
# ============================================================
st.markdown('''
<style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stSidebarCollapsedControl"] { display: none; }
    .stMainMenu { display: none; }
    header { visibility: hidden; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stApp { background: linear-gradient(180deg, #060e1a 0%, #0a1628 50%, #0d1b2a 100%); color: #e6f1ff; }
    *:not([class*='icon']):not([data-testid*='icon']):not(.material-icons):not([class*='Icon']) { font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif !important; }
    [data-testid='stExpander'] svg { font-family: inherit !important; }
    .mono { font-family: "JetBrains Mono", "Courier New", monospace !important; }
    .block-container { padding: 0.5rem 0.8rem 3rem !important; max-width: 540px !important; }
    .main-header { text-align: center; padding: 1rem 0; }
    .main-header h1 { font-size: 1.6rem; font-weight: 900; background: linear-gradient(135deg, #00d2be, #00ff88); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0; }
    .main-header .subtitle { font-size: 0.75rem; color: #8892b0; margin-top: 4px; }
    .live-badge { display: inline-flex; align-items: center; gap: 8px; margin-top: 8px; padding: 5px 14px; border-radius: 20px; background: rgba(0,210,190,0.08); border: 1px solid rgba(0,210,190,0.2); font-size: 0.75rem; }
    .live-dot { width: 8px; height: 8px; border-radius: 50%; background: #00ff88; box-shadow: 0 0 6px #00ff88; animation: pulse 2s infinite; }
    .live-dot.offline { background: #ff6b6b; box-shadow: 0 0 6px #ff6b6b; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
    .alert-banner { padding: 12px 14px; border-radius: 14px; border: 1px solid rgba(0,255,136,0.25); background: rgba(0,255,136,0.05); margin-bottom: 12px; }
    .alert-banner .alert-title { display: flex; align-items: center; gap: 6px; font-size: 0.82rem; font-weight: 700; color: #ff6b6b; margin-bottom: 4px; }
    .alert-banner .alert-detail { font-size: 0.72rem; color: #8892b0; padding-left: 26px; }
    .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 14px; }
    .stat-card { padding: 12px; border-radius: 14px; text-align: center; }
    .stat-card .stat-label { font-size: 0.68rem; color: #8892b0; }
    .stat-card .stat-value { font-size: 1.8rem; font-weight: 800; font-family: "JetBrains Mono", monospace !important; line-height: 1.2; }
    .stat-card .stat-sub { font-size: 0.62rem; color: #8892b0; margin-top: 2px; }
    .stock-card { background: linear-gradient(180deg, rgba(13,27,42,0.95), rgba(10,22,40,0.98)); border-radius: 18px; border: 1px solid rgba(0,210,190,0.12); padding: 14px; margin-bottom: 12px; }
    .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
    .score-gauge { display: flex; flex-direction: column; align-items: center; padding: 6px 12px; border-radius: 12px; min-width: 80px; }
    .score-gauge .score-label { font-size: 0.6rem; color: #8892b0; }
    .score-gauge .score-value { font-size: 1.6rem; font-weight: 800; font-family: "JetBrains Mono", monospace !important; line-height: 1; }
    .score-gauge .score-text { font-size: 0.6rem; margin-top: 2px; }
    .ticker-info { text-align: right; }
    .ticker-info .ticker { font-size: 1.3rem; font-weight: 800; color: #00d2be; font-family: "JetBrains Mono", monospace !important; }
    .ticker-info .name { font-size: 0.7rem; color: #8892b0; margin-top: 2px; }
    .tags-row { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 10px; }
    .tag-pill { display: inline-flex; align-items: center; gap: 3px; padding: 2px 9px; border-radius: 14px; font-size: 0.68rem; white-space: nowrap; }
    .vol-bar-container { margin-bottom: 10px; }
    .vol-bar-label { font-size: 0.65rem; color: #8892b0; margin-bottom: 3px; }
    .vol-bar-track { width: 100%; height: 7px; border-radius: 4px; background: rgba(255,255,255,0.05); overflow: hidden; }
    .vol-bar-fill { height: 100%; border-radius: 4px; background: linear-gradient(90deg, #ff4444, #ff8800, #ffcc00); }
    .stat-boxes { display: grid; grid-template-columns: 1fr 1fr; gap: 7px; margin-bottom: 8px; }
    .stat-box { padding: 8px 10px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.08); background: rgba(255,255,255,0.02); text-align: center; }
    .stat-box .sb-label { font-size: 0.62rem; color: #8892b0; }
    .stat-box .sb-value { font-size: 1rem; font-weight: 700; font-family: "JetBrains Mono", monospace !important; }
    .explosion-card { background: linear-gradient(180deg, rgba(13,27,42,0.95), rgba(10,22,40,0.98)); border-radius: 18px; border: 1px solid rgba(0,255,136,0.15); padding: 14px; margin-bottom: 12px; }
    .explosion-pct { font-size: 2.2rem; font-weight: 900; color: #00ff88; font-family: "JetBrains Mono", monospace !important; line-height: 1; }
    .criteria-item { padding: 10px; margin-bottom: 6px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.06); background: rgba(255,255,255,0.02); }
    .criteria-item.new-criteria { border-color: rgba(156,39,176,0.2); background: rgba(156,39,176,0.04); }
    .criteria-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
    .criteria-name { font-size: 0.78rem; font-weight: 600; color: #e6f1ff; }
    .criteria-bar { width: 100%; height: 3px; border-radius: 2px; background: rgba(255,255,255,0.05); margin-bottom: 3px; }
    .criteria-bar-fill { height: 100%; border-radius: 2px; }
    .criteria-detail { font-size: 0.65rem; color: #8892b0; }
    .new-badge { font-size: 0.55rem; padding: 1px 5px; border-radius: 6px; background: rgba(156,39,176,0.3); color: #ce93d8; margin-left: 4px; }
    .auto-status { padding: 10px 14px; border-radius: 12px; margin-bottom: 12px; font-size: 0.75rem; text-align: center; }
    .auto-status.active { background: rgba(0,255,136,0.06); border: 1px solid rgba(0,255,136,0.15); color: #00ff88; }
    .auto-status.inactive { background: rgba(255,107,107,0.06); border: 1px solid rgba(255,107,107,0.15); color: #ff6b6b; }
    .methodology { margin-top: 16px; padding: 14px; border-radius: 16px; border: 1px solid rgba(156,39,176,0.15); background: rgba(156,39,176,0.04); }
    .methodology-title { font-size: 0.85rem; font-weight: 700; color: #ce93d8; text-align: center; margin-bottom: 10px; }
    .methodology-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; }
    .method-item { display: flex; justify-content: space-between; align-items: center; padding: 3px 7px; border-radius: 5px; font-size: 0.65rem; background: rgba(255,255,255,0.02); }
    .method-item.new-method { background: rgba(156,39,176,0.08); }
    .disclaimer { margin-top: 14px; padding: 10px; border-radius: 12px; background: rgba(255,107,107,0.05); border: 1px solid rgba(255,107,107,0.1); font-size: 0.62rem; color: #8892b0; text-align: center; line-height: 1.6; }
    .stTabs [data-baseweb="tab-list"] { gap: 0; background: rgba(0,210,190,0.05); border-radius: 14px; border: 1px solid rgba(0,210,190,0.2); padding: 3px; }
    .stTabs [data-baseweb="tab"] { border-radius: 12px; color: #4a5568; font-weight: 600; padding: 8px 16px; }
    .stTabs [aria-selected="true"] { background: rgba(0,210,190,0.15) !important; color: #00d2be !important; }
    .stTabs [data-baseweb="tab-highlight"] { display: none; }
    .stTabs [data-baseweb="tab-border"] { display: none; }
    .streamlit-expanderHeader { background: rgba(0,210,190,0.05) !important; border-radius: 12px !important; border: 1px solid rgba(0,210,190,0.15) !important; color: #00d2be !important; font-weight: 600 !important; }
    .element-container { margin: 0 !important; padding: 0 !important; }
    .stMarkdown { margin: 0 !important; }
    div[data-testid="stVerticalBlock"] > div { gap: 0.3rem !important; }
    .stButton > button { background: rgba(0,210,190,0.1) !important; border: 1px solid rgba(0,210,190,0.3) !important; color: #00d2be !important; border-radius: 12px !important; font-weight: 600 !important; width: 100% !important; }
    .stButton > button:hover { background: rgba(0,210,190,0.2) !important; border-color: rgba(0,210,190,0.5) !important; }
</style>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;800&display=swap" rel="stylesheet">
''', unsafe_allow_html=True)


# ============================================================
# WATCHLIST — 1,160 Halal NYSE Stocks
# ============================================================
def load_watchlist():
    """Load tickers from tickers.txt file"""
    try:
        import os
        tickers_path = os.path.join(os.path.dirname(__file__), 'tickers.txt')
        with open(tickers_path, 'r') as f:
            content = f.read()
        tickers = [t.strip() for t in content.split(',') if t.strip()]
        return tickers
    except:
        # Fallback
        return ['HIMS', 'ZETA', 'ADBE', 'TTD', 'UNH', 'OSCR', 'RARE', 'UP',
                'SMCI', 'IONQ', 'RIVN', 'PLTR', 'SOFI', 'RKLB', 'MARA']

DEFAULT_WATCHLIST = load_watchlist()


# ============================================================
# MARKET HOURS CHECK
# ============================================================
def is_market_open():
    """Check if US stock market is currently open"""
    et = pytz.timezone('US/Eastern')
    now = datetime.now(et)
    # Weekday check (Mon=0, Fri=4)
    if now.weekday() > 4:
        return False
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= now <= market_close

def get_market_status():
    """Get detailed market status string"""
    et = pytz.timezone('US/Eastern')
    now = datetime.now(et)
    if now.weekday() > 4:
        return "CLOSED", "Weekend", "#ff6b6b"
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    if now < market_open:
        delta = market_open - now
        mins = int(delta.total_seconds() / 60)
        return "PRE-MARKET", f"Opens in {mins//60}h {mins%60}m", "#ffd700"
    elif now > market_close:
        return "CLOSED", "After hours", "#ff6b6b"
    else:
        delta = market_close - now
        mins = int(delta.total_seconds() / 60)
        return "OPEN", f"Closes in {mins//60}h {mins%60}m", "#00ff88"


# ============================================================
# EMAIL ALERTS
# ============================================================
def send_email_alert(triggered_stocks):
    """Send Gmail alert for triggered stocks"""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        return False

    et = pytz.timezone('US/Eastern')
    now = datetime.now(et).strftime('%I:%M %p ET')

    # Build email body
    subject = f"🎯 Explosion Alert: {len(triggered_stocks)} Stock{'s' if len(triggered_stocks) > 1 else ''} Triggered! ({now})"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0d1b2a; color: #e6f1ff; padding: 20px; border-radius: 12px;">
        <h2 style="color: #00d2be; text-align: center;">🎯 Explosion Hunter Alert</h2>
        <p style="color: #8892b0; text-align: center; font-size: 14px;">{now} — {len(triggered_stocks)} stock{'s' if len(triggered_stocks) > 1 else ''} above threshold (Score ≥ {ALERT_SCORE_THRESHOLD})</p>
        <hr style="border-color: rgba(0,210,190,0.2);">
    """

    for s in triggered_stocks:
        sc = '#00ff88' if s['explosionScore'] >= 85 else ('#00d2be' if s['explosionScore'] >= 70 else '#ffd700')
        html_body += f"""
        <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(0,210,190,0.15); border-radius: 12px; padding: 14px; margin: 10px 0;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 24px; font-weight: 800; color: {sc};">{s['explosionScore']}</span>
                <div style="text-align: right;">
                    <div style="font-size: 20px; font-weight: 800; color: #00d2be;">{s['ticker']}</div>
                    <div style="font-size: 12px; color: #8892b0;">{s['name']} · {s['capCategory']}</div>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 8px; margin-top: 10px;">
                <div style="text-align: center;">
                    <div style="font-size: 10px; color: #8892b0;">Price</div>
                    <div style="font-size: 14px; font-weight: 700; color: #00ff88;">${s['price']}</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 10px; color: #8892b0;">Short %</div>
                    <div style="font-size: 14px; font-weight: 700; color: #ff4444;">{s['shortInterest']}%</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 10px; color: #8892b0;">Vol Change</div>
                    <div style="font-size: 14px; font-weight: 700; color: #ff8800;">+{s['volumeChange']:.0f}%</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 10px; color: #8892b0;">RSI</div>
                    <div style="font-size: 14px; font-weight: 700;">{s['rsi']}</div>
                </div>
            </div>
            <div style="margin-top: 8px; font-size: 11px; color: #8892b0;">
                Catalyst: {s['catalyst']['label']} · Pattern: {s['historicalMatch']}% · MFI: {s['mfi']}
                {'· TTM Squeeze Active (' + str(s['squeezeBars']) + ' bars)' if s['ttmSqueeze'] else ''}
            </div>
        </div>
        """

    html_body += """
        <hr style="border-color: rgba(0,210,190,0.2);">
        <p style="color: #4a5568; font-size: 11px; text-align: center;">
            ⚠️ For educational purposes only. Not financial advice. Do your own research.
        </p>
    </div>
    """

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = GMAIL_ADDRESS
        msg['To'] = ALERT_TO_EMAIL
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False


# ============================================================
# DATA FETCHING (with retry — no Streamlit cache to avoid SessionInfo errors)
# ============================================================
def fetch_stock_data(ticker, max_retries=2):
    for attempt in range(max_retries + 1):
        try:
            time.sleep(0.3)
            stock = yf.Ticker(ticker)
            info = stock.info or {}
            hist = stock.history(period='6mo')
            if hist.empty or len(hist) < 20:
                if attempt < max_retries:
                    time.sleep(1)
                    continue
                return None
            current_price = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            daily_change_pct = ((current_price - prev_close) / prev_close) * 100
            avg_volume_20 = hist['Volume'].iloc[-20:].mean()
            current_volume = hist['Volume'].iloc[-1]
            volume_ratio = (current_volume / avg_volume_20 * 100) - 100 if avg_volume_20 > 0 else 0
            vol_3d = hist['Volume'].iloc[-3:].mean()
            vol_trend_rising = vol_3d > avg_volume_20 * 1.5
            delta = hist['Close'].diff()
            gain = delta.where(delta > 0, 0); loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=14).mean(); avg_loss = loss.rolling(window=14).mean()
            rs = avg_gain / avg_loss; rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1] if not rsi.empty and not np.isnan(rsi.iloc[-1]) else 50
            sma20 = hist['Close'].rolling(window=20).mean(); std20 = hist['Close'].rolling(window=20).std()
            bb_upper = sma20 + (2 * std20); bb_lower = sma20 - (2 * std20)
            bb_width = ((bb_upper - bb_lower) / sma20 * 100).iloc[-1] if not sma20.empty else 10
            bb_width_series = (bb_upper - bb_lower) / sma20 * 100
            bb_width_min_20 = bb_width_series.iloc[-20:].min() if len(bb_width_series) >= 20 else bb_width
            bollinger_squeeze = bb_width <= bb_width_min_20 * 1.1
            tr_series = pd.DataFrame({'hl': hist['High'] - hist['Low'], 'hc': abs(hist['High'] - hist['Close'].shift(1)), 'lc': abs(hist['Low'] - hist['Close'].shift(1))}).max(axis=1)
            atr20 = tr_series.rolling(window=20).mean()
            kc_upper = sma20 + (1.5 * atr20); kc_lower = sma20 - (1.5 * atr20)
            ttm_squeeze = False; squeeze_bars = 0
            if len(bb_upper) >= 20 and len(kc_upper) >= 20:
                for i in range(1, min(21, len(bb_upper))):
                    try:
                        if bb_upper.iloc[-i] < kc_upper.iloc[-i] and bb_lower.iloc[-i] > kc_lower.iloc[-i]:
                            squeeze_bars += 1; ttm_squeeze = True
                        else: break
                    except: break
            obv = [0]
            for i in range(1, len(hist)):
                if hist['Close'].iloc[i] > hist['Close'].iloc[i-1]: obv.append(obv[-1] + hist['Volume'].iloc[i])
                elif hist['Close'].iloc[i] < hist['Close'].iloc[i-1]: obv.append(obv[-1] - hist['Volume'].iloc[i])
                else: obv.append(obv[-1])
            obv_series = pd.Series(obv, index=hist.index); obv_sma = obv_series.rolling(window=20).mean()
            obv_trend = 'Bullish' if obv_series.iloc[-1] > obv_sma.iloc[-1] else 'Bearish'
            if obv_series.iloc[-1] > obv_sma.iloc[-1] * 1.1: obv_trend = 'Strong Bullish'
            typical_price = (hist['High'] + hist['Low'] + hist['Close']) / 3
            money_flow = typical_price * hist['Volume']
            positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
            negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0)
            positive_mf = positive_flow.rolling(window=14).sum(); negative_mf = negative_flow.rolling(window=14).sum()
            mfi = 100 - (100 / (1 + positive_mf / negative_mf))
            current_mfi = mfi.iloc[-1] if not mfi.empty and not np.isnan(mfi.iloc[-1]) else 50
            high_52 = hist['High'].max(); low_52 = hist['Low'].min()
            pct_from_low = ((current_price - low_52) / low_52 * 100) if low_52 > 0 else 0
            gap_up_target = None
            for i in range(len(hist) - 2, max(0, len(hist) - 60), -1):
                gap = hist['Low'].iloc[i+1] - hist['High'].iloc[i]
                if gap > current_price * 0.03: gap_up_target = hist['High'].iloc[i]; break
            short_interest = info.get('shortPercentOfFloat', 0)
            if short_interest is None: short_interest = 0
            short_interest = short_interest * 100 if short_interest < 1 else short_interest
            short_ratio = info.get('shortRatio', 0) or 0
            float_shares = info.get('floatShares', 0) or 0
            float_display = f'{float_shares/1e6:.0f}M' if float_shares > 1e6 else f'{float_shares/1e3:.0f}K'
            float_small = float_shares < 50e6 if float_shares > 0 else False
            market_cap = info.get('marketCap', 0) or 0
            if market_cap >= 10e9: cap_label, cap_display = 'Large Cap', f'${market_cap/1e9:.1f}B'
            elif market_cap >= 2e9: cap_label, cap_display = 'Mid Cap', f'${market_cap/1e9:.1f}B'
            elif market_cap >= 300e6: cap_label, cap_display = 'Small Cap', f'${market_cap/1e6:.0f}M'
            else: cap_label, cap_display = 'Micro Cap', f'${market_cap/1e6:.0f}M'
            industry = (info.get('industry', '') or '').lower(); sector_raw = (info.get('sector', '') or '').lower()
            if any(k in industry for k in ['biotech', 'pharma', 'drug', 'therapeutic', 'genomic']): sector = 'biotech'
            elif any(k in industry for k in ['software', 'semiconductor', 'computer', 'internet', 'ai', 'quantum']): sector = 'tech'
            elif any(k in industry for k in ['bank', 'financial', 'insurance', 'fintech', 'payment']): sector = 'fintech'
            elif any(k in sector_raw for k in ['energy']): sector = 'energy'
            else: sector = 'other'
            is_exploding = daily_change_pct > 15 and volume_ratio > 300
            earnings_date = None
            try:
                cal = stock.calendar
                if cal is not None:
                    if isinstance(cal, dict):
                        ed = cal.get('Earnings Date', [])
                        if ed: earnings_date = ed[0] if isinstance(ed, list) else ed
                    elif isinstance(cal, pd.DataFrame) and not cal.empty:
                        if 'Earnings Date' in cal.index: earnings_date = cal.loc['Earnings Date'].iloc[0]
            except: pass
            catalyst_type, catalyst_label, catalyst_date = 'None', 'None', ''
            if earnings_date:
                try:
                    ed = pd.Timestamp(earnings_date); days_until = (ed - pd.Timestamp.now()).days
                    if 0 <= days_until <= 14: catalyst_type, catalyst_label, catalyst_date = 'Earnings', 'Earnings Report', ed.strftime('%b %d')
                except: pass
            if sector == 'biotech' and catalyst_type == 'None': catalyst_type, catalyst_label, catalyst_date = 'FDA', 'Potential FDA Event', 'Upcoming'
            insider_pct = info.get('heldPercentInsiders', 0) or 0; insider_buys_est = 1 if insider_pct > 0.1 else 0
            return {'ticker': ticker, 'name': info.get('shortName', ticker), 'exchange': info.get('exchange', 'N/A'), 'sector': sector, 'marketCap': cap_display, 'capCategory': cap_label, 'price': round(current_price, 2), 'prevClose': round(prev_close, 2), 'dailyChangePct': round(daily_change_pct, 2), 'low52': round(low_52, 2), 'high52': round(high_52, 2), 'pctFromLow': round(pct_from_low, 2), 'shortInterest': round(short_interest, 1), 'shortRatio': round(short_ratio, 1), 'rsi': round(current_rsi, 1), 'mfi': round(current_mfi, 1), 'volumeChange': round(volume_ratio, 0), 'avgVolume': avg_volume_20, 'currentVolume': current_volume, 'volumeMultiple': round(current_volume / avg_volume_20, 1) if avg_volume_20 > 0 else 1, 'volTrendRising': vol_trend_rising, 'catalyst': {'type': catalyst_type, 'label': catalyst_label, 'date': catalyst_date}, 'news': vol_trend_rising and volume_ratio > 200, 'ttmSqueeze': ttm_squeeze, 'squeezeBars': squeeze_bars, 'bollingerSqueeze': bollinger_squeeze, 'bbWidth': round(bb_width, 2), 'obvTrend': obv_trend, 'float': float_display, 'floatShares': float_shares, 'floatSmall': float_small, 'gapUpTarget': round(gap_up_target, 2) if gap_up_target else None, 'insiderBuys': insider_buys_est, 'insiderPct': round(insider_pct * 100, 1), 'isExploding': is_exploding}
        except:
            if attempt < max_retries:
                time.sleep(1.5)
                continue
            return None
    return None


def calculate_explosion_score(stock):
    scores = {}
    si = stock['shortInterest']
    if si >= 30: scores['shortInterest'] = 100
    elif si >= 20: scores['shortInterest'] = 85
    elif si >= 15: scores['shortInterest'] = 65
    elif si >= 10: scores['shortInterest'] = 40
    elif si >= 5: scores['shortInterest'] = 20
    else: scores['shortInterest'] = 5
    ct = stock['catalyst']['type']
    if ct == 'FDA': scores['catalystEvent'] = 90
    elif ct == 'Earnings': scores['catalystEvent'] = 80
    elif ct == 'Partnership': scores['catalystEvent'] = 70
    else: scores['catalystEvent'] = 10
    vc = stock['volumeChange']
    if vc >= 1000: scores['volumeAnomaly'] = 100
    elif vc >= 500: scores['volumeAnomaly'] = 90
    elif vc >= 300: scores['volumeAnomaly'] = 75
    elif vc >= 200: scores['volumeAnomaly'] = 60
    elif vc >= 100: scores['volumeAnomaly'] = 40
    elif vc >= 50: scores['volumeAnomaly'] = 20
    else: scores['volumeAnomaly'] = 5
    pattern_score = 0
    if stock['shortInterest'] > 15: pattern_score += 25
    if stock['volumeChange'] > 200: pattern_score += 25
    if stock['rsi'] < 40: pattern_score += 20
    if stock['ttmSqueeze']: pattern_score += 15
    if stock['catalyst']['type'] in ['FDA', 'Earnings']: pattern_score += 15
    scores['historicalPattern'] = min(pattern_score, 100)
    rsi = stock['rsi']
    if rsi < 25: scores['rsiPosition'] = 100
    elif rsi < 30: scores['rsiPosition'] = 90
    elif rsi < 35: scores['rsiPosition'] = 75
    elif rsi < 40: scores['rsiPosition'] = 60
    elif rsi < 50: scores['rsiPosition'] = 40
    elif rsi < 60: scores['rsiPosition'] = 20
    else: scores['rsiPosition'] = 5
    pfl = stock['pctFromLow']
    if pfl < 10: scores['near52WeekLow'] = 95
    elif pfl < 20: scores['near52WeekLow'] = 75
    elif pfl < 35: scores['near52WeekLow'] = 50
    elif pfl < 50: scores['near52WeekLow'] = 30
    else: scores['near52WeekLow'] = 10
    scores['newsBreaking'] = 85 if stock['news'] else 10
    gamma_score = 0
    if stock['shortInterest'] > 15: gamma_score += 35
    if stock['floatSmall']: gamma_score += 30
    if stock['volumeChange'] > 200: gamma_score += 35
    scores['optionsGamma'] = min(gamma_score, 100)
    scores['darkPoolActivity'] = 85 if stock['volumeChange'] > 150 and abs(stock['dailyChangePct']) < 3 else (50 if stock['volumeChange'] > 100 else 15)
    scores['insiderBuying'] = 80 if stock['insiderBuys'] > 0 else 10
    if stock['floatSmall']: scores['floatRotation'] = 90
    elif stock['floatShares'] < 100e6: scores['floatRotation'] = 60
    elif stock['floatShares'] < 500e6: scores['floatRotation'] = 30
    else: scores['floatRotation'] = 10
    if stock['sector'] in ['biotech']: scores['sectorMomentum'] = 85
    elif stock['sector'] in ['tech']: scores['sectorMomentum'] = 70
    else: scores['sectorMomentum'] = 40
    if stock['ttmSqueeze'] and stock['squeezeBars'] > 6: scores['ttmSqueeze'] = 95
    elif stock['ttmSqueeze']: scores['ttmSqueeze'] = 70
    elif stock['bollingerSqueeze']: scores['ttmSqueeze'] = 45
    else: scores['ttmSqueeze'] = 10
    if stock['gapUpTarget'] and stock['gapUpTarget'] > stock['price'] * 1.1: scores['gapFillPotential'] = 80
    elif stock['gapUpTarget']: scores['gapFillPotential'] = 50
    else: scores['gapFillPotential'] = 10
    weights = {'shortInterest': 18, 'catalystEvent': 16, 'volumeAnomaly': 14, 'historicalPattern': 12, 'rsiPosition': 8, 'near52WeekLow': 6, 'newsBreaking': 4, 'optionsGamma': 5, 'darkPoolActivity': 4, 'insiderBuying': 3, 'floatRotation': 3, 'sectorMomentum': 2, 'ttmSqueeze': 3, 'gapFillPotential': 2}
    total_weight = sum(weights.values())
    weighted_sum = sum(scores.get(k, 0) * v for k, v in weights.items())
    return round(weighted_sum / total_weight), scores


def fetch_all_stocks(watchlist):
    """Fetch all stocks in batches with inline stop button and timer"""
    results = []; failed = []
    scan_start = time.time()
    progress_bar = st.progress(0)
    timer_text = st.empty()
    status_text = st.empty()
    stop_container = st.empty()
    total = len(watchlist); completed = 0; lock = threading.Lock()
    stopped = False

    def format_elapsed(seconds):
        m, s = divmod(int(seconds), 60)
        return f"{m}:{s:02d}"

    # Process in batches of 50 to avoid rate limits
    BATCH_SIZE = 50
    batches = [watchlist[i:i+BATCH_SIZE] for i in range(0, len(watchlist), BATCH_SIZE)]

    for batch_idx, batch in enumerate(batches):
        if stopped:
            break

        # Show stop button
        with stop_container:
            if st.button('⏹️ Stop Scanning — Show Results So Far', key=f'stop_{batch_idx}', use_container_width=True):
                stopped = True
                # Save what we have so far BEFORE the rerun
                scanned_tickers = {r['ticker'] for r in results} | set(failed)
                remaining = [t for t in watchlist if t not in scanned_tickers]
                failed.extend(remaining)
                st.session_state['stocks_data'] = results
                st.session_state['failed_tickers'] = failed
                st.session_state['last_scan_time'] = datetime.now()
                st.session_state['scan_count'] = st.session_state.get('scan_count', 0) + 1
                st.session_state['last_scan_duration'] = format_elapsed(time.time() - scan_start)
                st.session_state['scan_was_stopped'] = True
                progress_bar.empty(); timer_text.empty(); status_text.empty(); stop_container.empty()
                st.rerun()

        def fetch_one(ticker):
            nonlocal completed
            data = fetch_stock_data(ticker)
            with lock: completed += 1
            return (ticker, data)

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_ticker = {executor.submit(fetch_one, t): t for t in batch}
            for future in concurrent.futures.as_completed(future_to_ticker):
                try:
                    ticker, data = future.result()
                    if data:
                        score, detailed = calculate_explosion_score(data)
                        if score >= 40:
                            data['explosionScore'] = score
                            data['detailedScores'] = detailed
                            data['historicalMatch'] = detailed.get('historicalPattern', 0)
                            results.append(data)
                    else:
                        failed.append(ticker)
                except:
                    pass
                elapsed = time.time() - scan_start
                pct = completed / total
                eta = (elapsed / pct - elapsed) if pct > 0.05 else 0
                progress_bar.progress(min(pct, 1.0))
                timer_text.markdown(f'<div style="text-align:center;font-size:0.85rem;font-weight:700;color:#00d2be;font-family:JetBrains Mono,monospace;">⏱️ {format_elapsed(elapsed)}{" · ETA " + format_elapsed(eta) if eta > 0 else ""}</div>', unsafe_allow_html=True)
                status_text.markdown(f'<div style="text-align:center;font-size:0.75rem;color:#8892b0;">Scanning {completed}/{total} stocks · Batch {batch_idx+1}/{len(batches)} · Found {len(results)} candidates</div>', unsafe_allow_html=True)

        # Save incrementally after each batch (safety net)
        st.session_state['stocks_data'] = results
        st.session_state['failed_tickers'] = failed

        # Pause between batches
        if batch_idx < len(batches) - 1 and not stopped:
            time.sleep(2)

    total_time = time.time() - scan_start
    st.session_state['last_scan_duration'] = format_elapsed(total_time)
    st.session_state['scan_was_stopped'] = False

    # Retry top failed tickers
    retry_list = failed[:30]
    if retry_list:
        status_text.markdown(f'<div style="text-align:center;font-size:0.75rem;color:#ffd700;">Retrying {len(retry_list)} of {len(failed)} failed tickers...</div>', unsafe_allow_html=True)
        for ticker in retry_list:
            time.sleep(0.5)
            try:
                data = fetch_stock_data(ticker)
                if data:
                    score, detailed = calculate_explosion_score(data)
                    if score >= 40:
                        data['explosionScore'] = score
                        data['detailedScores'] = detailed
                        data['historicalMatch'] = detailed.get('historicalPattern', 0)
                        results.append(data)
                        failed.remove(ticker)
            except: pass

    timer_text.markdown(f'<div style="text-align:center;font-size:0.85rem;font-weight:700;color:#00ff88;font-family:JetBrains Mono,monospace;">✅ Scan complete — {format_elapsed(total_time)} · {len(results)} candidates</div>', unsafe_allow_html=True)
    time.sleep(3)

    progress_bar.empty(); timer_text.empty(); status_text.empty(); stop_container.empty()
    return results, failed


# ============================================================
# RENDERING HELPERS
# ============================================================
def get_score_color(s):
    if s >= 85: return '#00ff88'
    if s >= 70: return '#00d2be'
    if s >= 55: return '#ffd700'
    return '#ff6b6b'

def get_score_label(s):
    if s >= 90: return 'Very High'
    if s >= 80: return 'High'
    if s >= 65: return 'Med-High'
    if s >= 50: return 'Medium'
    return 'Low'

def format_volume(vol):
    if vol >= 1e9: return f'{vol/1e9:.1f}B'
    if vol >= 1e6: return f'{vol/1e6:.1f}M'
    if vol >= 1e3: return f'{vol/1e3:.0f}K'
    return str(int(vol))

def render_stock_card(stock):
    sc = get_score_color(stock['explosionScore']); sl = get_score_label(stock['explosionScore'])
    tags = []
    if stock['shortInterest'] > 10: tags.append(f'<span class="tag-pill" style="background:rgba(255,68,68,0.15);border:1px solid rgba(255,68,68,0.3);color:#ff4444;">🔴 Short {stock["shortInterest"]}%</span>')
    if stock['catalyst']['type'] != 'None':
        cc = {'FDA':'#00d2be','Earnings':'#4CAF50','Partnership':'#9C27B0'}.get(stock['catalyst']['type'],'#ffd700')
        ci = {'FDA':'🔬','Earnings':'📊','Partnership':'🤝'}.get(stock['catalyst']['type'],'📅')
        tags.append(f'<span class="tag-pill" style="background:{cc}15;border:1px solid {cc}40;color:{cc};">{ci} {stock["catalyst"]["label"]} · {stock["catalyst"]["date"]}</span>')
    if stock['news']: tags.append('<span class="tag-pill" style="background:rgba(255,215,0,0.15);border:1px solid rgba(255,215,0,0.3);color:#ffd700;">📰 Unusual Activity</span>')
    if stock['volumeChange'] > 100: tags.append(f'<span class="tag-pill" style="background:rgba(255,136,0,0.15);border:1px solid rgba(255,136,0,0.3);color:#ff8800;">📈 Vol +{stock["volumeChange"]:.0f}%</span>')
    if stock['ttmSqueeze']: tags.append(f'<span class="tag-pill" style="background:rgba(206,147,216,0.15);border:1px solid rgba(206,147,216,0.3);color:#ce93d8;">💥 Squeeze ({stock["squeezeBars"]})</span>')
    if stock['floatSmall']: tags.append('<span class="tag-pill" style="background:rgba(0,188,212,0.15);border:1px solid rgba(0,188,212,0.3);color:#00bcd4;">🔁 Small Float</span>')
    vol_bar_pct = min(stock['volumeChange'] / 20, 100)
    rsi_color = '#00ff88' if stock['rsi'] < 40 else ('#ffd700' if stock['rsi'] < 60 else '#ff6b6b')
    return f'''<div class="stock-card"><div class="card-header"><div class="score-gauge" style="background:{sc}10;border:1px solid {sc}30;"><span class="score-label">Explosion Score</span><span class="score-value" style="color:{sc};">{stock['explosionScore']}</span><span class="score-text" style="color:{sc};">{sl}</span></div><div class="ticker-info"><div class="ticker">{stock['ticker']}</div><div class="name">{stock['name']} · {stock['capCategory']} {stock['marketCap']}</div></div></div><div class="tags-row">{''.join(tags)}</div><div class="vol-bar-container"><div class="vol-bar-label">Volume vs Avg ({stock['volumeMultiple']}x)</div><div class="vol-bar-track"><div class="vol-bar-fill" style="width:{vol_bar_pct}%;"></div></div></div><div class="stat-boxes"><div class="stat-box"><div class="sb-label">Price</div><div class="sb-value" style="color:#00ff88;">${stock['price']}</div></div><div class="stat-box"><div class="sb-label">52W Low</div><div class="sb-value">${stock['low52']}</div></div><div class="stat-box"><div class="sb-label">SHORT %</div><div class="sb-value" style="color:#ff4444;">{stock['shortInterest']}%</div></div><div class="stat-box"><div class="sb-label">RSI</div><div class="sb-value" style="color:{rsi_color};">{stock['rsi']}</div></div></div><div class="stat-boxes"><div class="stat-box"><div class="sb-label">Pattern Match</div><div class="sb-value" style="color:{'#00ff88' if stock['historicalMatch']>70 else '#ffd700'};">{stock['historicalMatch']}%</div></div><div class="stat-box"><div class="sb-label">MFI</div><div class="sb-value" style="color:{'#00ff88' if stock['mfi']<30 else '#ffd700'};">{stock['mfi']}</div></div></div></div>'''

def render_explosion_card(stock):
    change = stock['dailyChangePct']; vol_bar_pct = min(stock['volumeChange'] / 20, 100)
    rsi_color = '#ff6b6b' if stock['rsi'] > 70 else '#00ff88'
    return f'''<div class="explosion-card"><div class="card-header"><div class="explosion-pct">+{change:.1f}%</div><div class="ticker-info"><div class="ticker">{stock['ticker']}</div><div class="name">{stock['name']} · {stock['capCategory']}</div></div></div><div class="tags-row">{'<span class="tag-pill" style="background:rgba(255,68,68,0.15);border:1px solid rgba(255,68,68,0.3);color:#ff4444;">🔴 Short Squeeze</span>' if stock['shortInterest']>15 else ''}<span class="tag-pill" style="background:rgba(0,255,136,0.15);border:1px solid rgba(0,255,136,0.3);color:#00ff88;">⚡ Active Explosion</span></div><div class="vol-bar-container"><div class="vol-bar-label">Volume ({stock['volumeMultiple']}x avg)</div><div class="vol-bar-track"><div class="vol-bar-fill" style="width:{vol_bar_pct}%;"></div></div></div><div class="stat-boxes"><div class="stat-box"><div class="sb-label">Price</div><div class="sb-value" style="color:#00ff88;">${stock['price']}</div></div><div class="stat-box"><div class="sb-label">Prev Close</div><div class="sb-value">${stock['prevClose']}</div></div><div class="stat-box"><div class="sb-label">Volume</div><div class="sb-value" style="color:#ff8800;">{format_volume(stock['currentVolume'])}</div></div><div class="stat-box"><div class="sb-label">RSI</div><div class="sb-value" style="color:{rsi_color};">{stock['rsi']}</div></div></div></div>'''

def render_criteria_detail(stock):
    weights = {'shortInterest': ('🔴','Short Interest',18,False), 'catalystEvent': ('📅','Catalyst Event',16,False), 'volumeAnomaly': ('📈','Volume Anomaly',14,False), 'historicalPattern': ('🔄','Historical Pattern',12,False), 'rsiPosition': ('📉','RSI Position',8,False), 'near52WeekLow': ('⬇️','Near 52W Low',6,False), 'newsBreaking': ('📰','News/Activity',4,False), 'optionsGamma': ('🎯','GEX Gamma',5,True), 'darkPoolActivity': ('🌑','Dark Pool',4,True), 'insiderBuying': ('👔','Insider Buying',3,True), 'floatRotation': ('🔁','Float Size',3,True), 'sectorMomentum': ('🏆','Sector Momentum',2,True), 'ttmSqueeze': ('💥','TTM Squeeze',3,True), 'gapFillPotential': ('🕳️','Gap Fill',2,True)}
    total_w = sum(w[2] for w in weights.values()); detailed = stock.get('detailedScores', {})
    html = '<div>'
    for key, (icon, name, weight, is_new) in weights.items():
        score = detailed.get(key, 0); bar_color = '#00ff88' if score > 70 else ('#ffd700' if score > 40 else '#ff6b6b')
        nc = 'new-criteria' if is_new else ''; nb = '<span class="new-badge">NEW</span>' if is_new else ''
        html += f'<div class="criteria-item {nc}"><div class="criteria-header"><span class="criteria-name">{icon} {name} {nb}</span><span class="mono" style="font-size:0.8rem;font-weight:700;color:{bar_color};">{score}</span></div><div class="criteria-bar"><div class="criteria-bar-fill" style="width:{score}%;background:{bar_color};"></div></div><div class="criteria-detail">Weight: {weight}/{total_w} ({weight/total_w*100:.0f}%)</div></div>'
    html += f'<div style="margin-top:8px;padding:8px;border-radius:10px;background:rgba(0,210,190,0.04);border:1px solid rgba(0,210,190,0.12);"><div style="font-size:0.75rem;font-weight:700;color:#00d2be;margin-bottom:4px;">📊 Additional Indicators</div><div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;"><div style="font-size:0.65rem;color:#8892b0;">OBV: <span style="color:{"#00ff88" if "Bullish" in stock["obvTrend"] else "#ffd700"};">{stock["obvTrend"]}</span></div><div style="font-size:0.65rem;color:#8892b0;">MFI: <span style="color:{"#00ff88" if stock["mfi"]<30 else "#ffd700"};">{stock["mfi"]}</span></div><div style="font-size:0.65rem;color:#8892b0;">BB Width: <span style="color:#e6f1ff;">{stock["bbWidth"]}%</span></div><div style="font-size:0.65rem;color:#8892b0;">Short Ratio: <span style="color:{"#ff6b6b" if stock["shortRatio"]>5 else "#ffd700"};">{stock["shortRatio"]}d</span></div></div></div></div>'
    return html


# ============================================================
# MAIN APP
# ============================================================
def main():
    # Header
    st.markdown('<div class="main-header"><div style="font-size:2rem;">🎯</div><h1>Explosion Hunter</h1><div class="subtitle">1,160 Halal Stocks · Auto-Scan Every Hour · Email Alerts</div></div>', unsafe_allow_html=True)

    # Market status
    status, status_detail, status_color = get_market_status()
    dot_class = "live-dot" if status == "OPEN" else "live-dot offline"
    st.markdown(f'''
    <div style="text-align:center;">
        <div class="live-badge">
            <div class="{dot_class}"></div>
            <span style="color:{status_color};">{status}</span>
            <span style="color:#8892b0;">{status_detail}</span>
            <span style="color:#8892b0;">NYSE/NASDAQ</span>
        </div>
    </div>
    ''', unsafe_allow_html=True)

    # Auto-scan status
    email_configured = bool(GMAIL_ADDRESS and GMAIL_APP_PASSWORD)
    if is_market_open():
        auto_msg = f"🔄 Auto-scanning every {SCAN_INTERVAL_MINUTES} min · {'📧 Email alerts ON' if email_configured else '⚠️ Email not configured'}"
        st.markdown(f'<div class="auto-status active">{auto_msg}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="auto-status inactive">⏸️ Market closed — scanner paused · Next scan when market opens</div>', unsafe_allow_html=True)

    # Watchlist config
    with st.expander(f'⚙️ Watchlist ({len(DEFAULT_WATCHLIST)} Halal NYSE stocks)'):
        custom_tickers = st.text_area('Tickers (comma-separated)', value=', '.join(DEFAULT_WATCHLIST), height=150)
        watchlist = [t.strip().upper() for t in custom_tickers.split(',') if t.strip()]
        st.markdown(f'<div style="font-size:0.7rem;color:#8892b0;">Total: {len(watchlist)} stocks · Scan takes ~15-20 min for full list</div>', unsafe_allow_html=True)

    # Email config status
    with st.expander('📧 Email Alert Status'):
        if email_configured:
            st.markdown(f'<div style="font-size:0.8rem;color:#00ff88;">✅ Gmail configured: {GMAIL_ADDRESS}</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:0.8rem;color:#8892b0;">Alert threshold: Score ≥ {ALERT_SCORE_THRESHOLD}</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:0.8rem;color:#8892b0;">Sending to: {ALERT_TO_EMAIL}</div>', unsafe_allow_html=True)
            if st.button('📧 Send Test Email'):
                test_stock = {'ticker': 'TEST', 'name': 'Test Alert', 'capCategory': 'Test', 'price': 10.00, 'shortInterest': 25.0, 'volumeChange': 500, 'rsi': 35.0, 'mfi': 28.0, 'catalyst': {'label': 'Test Event'}, 'historicalMatch': 85, 'explosionScore': 85, 'ttmSqueeze': True, 'squeezeBars': 8}
                if send_email_alert([test_stock]):
                    st.success('✅ Test email sent! Check your inbox.')
                else:
                    st.error('❌ Failed to send. Check your Gmail App Password.')
        else:
            st.markdown('''
            <div style="font-size:0.8rem;color:#ff6b6b;">
                ⚠️ Email not configured. Set these Railway environment variables:<br>
                • <code>GMAIL_ADDRESS</code> — your Gmail address<br>
                • <code>GMAIL_APP_PASSWORD</code> — your Gmail App Password (not regular password)<br>
                • <code>ALERT_TO_EMAIL</code> — email to receive alerts (optional, defaults to GMAIL_ADDRESS)
            </div>
            ''', unsafe_allow_html=True)

    # Fetch data — auto or manual
    should_scan = False
    last_scan = st.session_state.get('last_scan_time', None)

    if st.button('🔄 Scan Now', use_container_width=True):
        should_scan = True

    if not should_scan and last_scan is None:
        should_scan = True
    elif not should_scan and is_market_open() and last_scan:
        elapsed = (datetime.now() - last_scan).total_seconds() / 60
        if elapsed >= SCAN_INTERVAL_MINUTES:
            should_scan = True

    if should_scan:
        stocks_data, failed_tickers = fetch_all_stocks(watchlist)
        st.session_state['stocks_data'] = stocks_data
        st.session_state['failed_tickers'] = failed_tickers
        st.session_state['last_scan_time'] = datetime.now()
        st.session_state['scan_count'] = st.session_state.get('scan_count', 0) + 1

        # Check for alerts and send email
        if email_configured and is_market_open():
            triggered = [s for s in stocks_data if s['explosionScore'] >= ALERT_SCORE_THRESHOLD]
            # Only alert on NEW triggers (not already alerted)
            prev_alerted = st.session_state.get('alerted_tickers', set())
            new_triggers = [s for s in triggered if s['ticker'] not in prev_alerted]
            if new_triggers:
                send_email_alert(new_triggers)
                st.session_state['alerted_tickers'] = prev_alerted | {s['ticker'] for s in new_triggers}
                st.session_state['last_alert_time'] = datetime.now()
                st.session_state['alerts_sent'] = st.session_state.get('alerts_sent', 0) + 1

        st.rerun()

    stocks_data = st.session_state.get('stocks_data', [])
    last_scan = st.session_state.get('last_scan_time', None)
    scan_count = st.session_state.get('scan_count', 0)
    alerts_sent = st.session_state.get('alerts_sent', 0)

    if not stocks_data:
        st.warning('Press Scan Now to start')
        return

    pre_explosion = sorted([s for s in stocks_data if not s['isExploding']], key=lambda x: x['explosionScore'], reverse=True)
    active_explosions = sorted([s for s in stocks_data if s['isExploding']], key=lambda x: x['dailyChangePct'], reverse=True)

    # Stopped early indicator
    failed_tickers = st.session_state.get('failed_tickers', [])
    if st.session_state.get('scan_stopped', False) and len(stocks_data) > 0:
        scanned_count = len(stocks_data) + len([f for f in failed_tickers if f not in [s['ticker'] for s in stocks_data]])
        st.markdown(f'''
        <div style="padding:10px 14px;border-radius:12px;margin-bottom:12px;font-size:0.75rem;text-align:center;
            background:rgba(255,215,0,0.06);border:1px solid rgba(255,215,0,0.15);color:#ffd700;">
            ⏹️ Scan stopped early — showing results from {len(stocks_data)} candidates found so far
        </div>
        ''', unsafe_allow_html=True)

    # Top alert
    if pre_explosion and pre_explosion[0]['explosionScore'] >= 60:
        top = pre_explosion[0]
        st.markdown(f'<div class="alert-banner"><div class="alert-title">🚨 HIGH ALERT — {top["ticker"]}: Volume +{top["volumeChange"]:.0f}%</div><div class="alert-detail">{top["catalyst"]["label"]} · Pattern match {top["historicalMatch"]}%</div></div>', unsafe_allow_html=True)

    # Dashboard stats
    high_alerts = len([s for s in pre_explosion if s['explosionScore'] >= ALERT_SCORE_THRESHOLD])
    catalysts = len([s for s in stocks_data if s['catalyst']['type'] != 'None'])
    last_scan_str = last_scan.strftime('%H:%M:%S') if last_scan else '--:--'
    scan_duration = st.session_state.get('last_scan_duration', '--:--')

    st.markdown(f'''<div class="stats-grid">
        <div class="stat-card" style="border:1px solid rgba(0,210,190,0.12);background:rgba(0,210,190,0.04);">
            <div class="stat-label">Stocks Monitored</div><div class="stat-value" style="color:#00d2be;">{len(stocks_data)}</div>
            <div class="stat-sub">Scan #{scan_count} · {last_scan_str} · ⏱️ {scan_duration}</div></div>
        <div class="stat-card" style="border:1px solid rgba(255,107,107,0.12);background:rgba(255,107,107,0.04);">
            <div class="stat-label">High Alerts (≥{ALERT_SCORE_THRESHOLD})</div><div class="stat-value" style="color:#ff6b6b;">{high_alerts}</div>
            <div class="stat-sub">{alerts_sent} emails sent today</div></div>
        <div class="stat-card" style="border:1px solid rgba(0,255,136,0.12);background:rgba(0,255,136,0.04);">
            <div class="stat-label">Active Explosions</div><div class="stat-value" style="color:#00ff88;">{len(active_explosions)}</div>
            <div class="stat-sub">>15% + High Volume</div></div>
        <div class="stat-card" style="border:1px solid rgba(255,215,0,0.12);background:rgba(255,215,0,0.04);">
            <div class="stat-label">Upcoming Catalysts</div><div class="stat-value" style="color:#ffd700;">{catalysts}</div>
            <div class="stat-sub">FDA · Earnings</div></div>
    </div>''', unsafe_allow_html=True)

    # Failed tickers display
    failed_tickers = st.session_state.get('failed_tickers', [])
    if failed_tickers:
        with st.expander(f'⚠️ Failed Tickers ({len(failed_tickers)} of {len(watchlist)})'):
            st.markdown(f'''
            <div style="font-size:0.75rem;color:#ff6b6b;margin-bottom:8px;">
                These tickers failed to fetch data (yfinance rate limit or invalid ticker).
                They will be retried on the next scan.
            </div>
            <div style="font-size:0.7rem;color:#8892b0;line-height:1.8;word-wrap:break-word;">
                {', '.join(sorted(failed_tickers))}
            </div>
            ''', unsafe_allow_html=True)

    # Tabs
    tab1, tab2 = st.tabs(['🔭 Pre-Explosion', '🚀 Active Explosions'])

    with tab1:
        sector_options = {'all':'All','biotech':'🧬 Biotech','tech':'💻 Tech','fintech':'💰 Fintech'}
        cols = st.columns(len(sector_options))
        if 'sector_filter' not in st.session_state: st.session_state['sector_filter'] = 'all'
        for i, (key, label) in enumerate(sector_options.items()):
            with cols[i]:
                if st.button(label, key=f'sec_{key}', use_container_width=True): st.session_state['sector_filter'] = key
        filtered = pre_explosion
        sf = st.session_state.get('sector_filter', 'all')
        if sf != 'all': filtered = [s for s in filtered if s['sector'] == sf]
        st.markdown(f'<div style="text-align:center;font-size:0.9rem;font-weight:700;color:#e6f1ff;margin:10px 0;">🔭 Pre-Explosion — {len(filtered)} stocks</div>', unsafe_allow_html=True)
        for stock in filtered:
            st.markdown(render_stock_card(stock), unsafe_allow_html=True)
            with st.expander(f'🔍 Criteria Details — {stock["ticker"]}'): st.markdown(render_criteria_detail(stock), unsafe_allow_html=True)

    with tab2:
        if active_explosions:
            st.markdown(f'<div style="text-align:center;font-size:0.9rem;font-weight:700;color:#e6f1ff;margin:10px 0;">🚀 Active Explosions — {len(active_explosions)}</div>', unsafe_allow_html=True)
            for stock in active_explosions: st.markdown(render_explosion_card(stock), unsafe_allow_html=True)
        else:
            st.markdown('<div style="text-align:center;padding:40px;"><div style="font-size:3rem;">🔭</div><div style="color:#8892b0;">No active explosions right now</div><div style="color:#4a5568;font-size:0.75rem;margin-top:6px;">Explosion = >15% gain + >4x avg volume</div></div>', unsafe_allow_html=True)

    # Methodology
    weights_info = {'shortInterest':('🔴 Short Interest',18,False),'catalystEvent':('📅 Catalyst',16,False),'volumeAnomaly':('📈 Volume',14,False),'historicalPattern':('🔄 Pattern',12,False),'rsiPosition':('📉 RSI',8,False),'near52WeekLow':('⬇️ 52W Low',6,False),'newsBreaking':('📰 News',4,False),'optionsGamma':('🎯 GEX',5,True),'darkPoolActivity':('🌑 Dark Pool',4,True),'insiderBuying':('👔 Insider',3,True),'floatRotation':('🔁 Float',3,True),'sectorMomentum':('🏆 Sector',2,True),'ttmSqueeze':('💥 Squeeze',3,True),'gapFillPotential':('🕳️ Gap',2,True)}
    total_w = sum(v[1] for v in weights_info.values())
    mh = '<div class="methodology"><div class="methodology-title">⚙️ Scoring Methodology — 14 Criteria</div><div class="methodology-grid">'
    for key, (label, weight, is_new) in weights_info.items():
        nc = 'new-method' if is_new else ''; badge = '<span class="new-badge">+</span>' if is_new else ''
        mh += f'<div class="method-item {nc}"><span style="color:#8892b0;">{label} {badge}</span><span class="mono" style="color:#e6f1ff;font-weight:700;">{weight/total_w*100:.0f}%</span></div>'
    mh += '</div></div>'
    st.markdown(mh, unsafe_allow_html=True)

    # Disclaimer
    st.markdown('<div class="disclaimer">⚠️ For educational and analytical purposes only. Not financial advice. Trading involves high risk. Do your own research.</div>', unsafe_allow_html=True)

    # AUTO-REFRESH: Rerun page every N minutes during market hours
    if is_market_open():
        time.sleep(2)  # Small delay to let page render
        st.markdown(f'<meta http-equiv="refresh" content="{SCAN_INTERVAL_MINUTES * 60}">', unsafe_allow_html=True)


if __name__ == '__main__':
    main()
