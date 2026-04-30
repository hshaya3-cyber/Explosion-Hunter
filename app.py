"""
🎯 Explosion Hunter v4.0 — Multi-Timeframe Auto Scanner
=========================================================
Schedule:
- 30min scan: every 30 min during market hours
- 1H scan: every 1 hour during market hours  
- 4H scan: every 4 hours during market hours
- Daily scan: once after market close (4:15 PM ET) with full email report
- Separate email alerts per timeframe when Score >= 70
- 1,160 Halal NYSE stocks on all timeframes
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
import os

warnings.filterwarnings('ignore')

import requests

GMAIL_WEBHOOK_URL = os.environ.get('GMAIL_WEBHOOK_URL', '')
ALERT_TO_EMAIL = os.environ.get('ALERT_TO_EMAIL', 'hshaya3@gmail.com')
ALERT_SCORE_THRESHOLD = int(os.environ.get('ALERT_THRESHOLD', '70'))

TIMEFRAMES = {
    '30m': {'label': '30 Min', 'interval': '30m', 'period': '5d', 'scan_every_min': 30, 'icon': '⚡'},
    '1h':  {'label': '1 Hour', 'interval': '60m', 'period': '10d', 'scan_every_min': 60, 'icon': '⏰'},
    '4h':  {'label': '4 Hour', 'interval': '60m', 'period': '30d', 'scan_every_min': 240, 'icon': '📊'},
    '1d':  {'label': 'Daily',  'interval': '1d',  'period': '1y',  'scan_every_min': 0, 'icon': '📅'},
}

st.set_page_config(page_title='Explosion Hunter', page_icon='🎯', layout='centered', initial_sidebar_state='collapsed')

st.markdown('''
<style>
    [data-testid="stSidebar"]{display:none}[data-testid="stSidebarCollapsedControl"]{display:none}.stMainMenu{display:none}header{visibility:hidden}#MainMenu{visibility:hidden}footer{visibility:hidden}
    .stApp{background:linear-gradient(180deg,#060e1a 0%,#0a1628 50%,#0d1b2a 100%);color:#e6f1ff}
    *:not([class*='icon']):not([data-testid*='icon']):not(.material-icons):not([class*='Icon']){font-family:"Segoe UI",-apple-system,BlinkMacSystemFont,sans-serif!important}
    [data-testid='stExpander'] svg{font-family:inherit!important}
    .mono{font-family:"JetBrains Mono","Courier New",monospace!important}
    .block-container{padding:0.5rem 0.8rem 3rem!important;max-width:540px!important}
    .main-header{text-align:center;padding:1rem 0}.main-header h1{font-size:1.6rem;font-weight:900;background:linear-gradient(135deg,#00d2be,#00ff88);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin:0}.main-header .subtitle{font-size:0.75rem;color:#8892b0;margin-top:4px}
    .live-badge{display:inline-flex;align-items:center;gap:8px;margin-top:8px;padding:5px 14px;border-radius:20px;background:rgba(0,210,190,0.08);border:1px solid rgba(0,210,190,0.2);font-size:0.75rem}
    .live-dot{width:8px;height:8px;border-radius:50%;background:#00ff88;box-shadow:0 0 6px #00ff88;animation:pulse 2s infinite}.live-dot.off{background:#ff6b6b;box-shadow:0 0 6px #ff6b6b}
    @keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}
    .stock-card{background:linear-gradient(180deg,rgba(13,27,42,0.95),rgba(10,22,40,0.98));border-radius:18px;border:1px solid rgba(0,210,190,0.12);padding:14px;margin-bottom:12px}
    .card-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px}
    .score-gauge{display:flex;flex-direction:column;align-items:center;padding:6px 12px;border-radius:12px;min-width:80px}
    .score-gauge .score-label{font-size:0.6rem;color:#8892b0}.score-gauge .score-value{font-size:1.6rem;font-weight:800;font-family:"JetBrains Mono",monospace!important;line-height:1}.score-gauge .score-text{font-size:0.6rem;margin-top:2px}
    .ticker-info{text-align:right}.ticker-info .ticker{font-size:1.3rem;font-weight:800;color:#00d2be;font-family:"JetBrains Mono",monospace!important}.ticker-info .name{font-size:0.7rem;color:#8892b0;margin-top:2px}
    .tags-row{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:10px}
    .tag-pill{display:inline-flex;align-items:center;gap:3px;padding:2px 9px;border-radius:14px;font-size:0.68rem;white-space:nowrap}
    .vol-bar-container{margin-bottom:10px}.vol-bar-label{font-size:0.65rem;color:#8892b0;margin-bottom:3px}
    .vol-bar-track{width:100%;height:7px;border-radius:4px;background:rgba(255,255,255,0.05);overflow:hidden}.vol-bar-fill{height:100%;border-radius:4px;background:linear-gradient(90deg,#ff4444,#ff8800,#ffcc00)}
    .stat-boxes{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-bottom:8px}
    .stat-box{padding:8px 10px;border-radius:10px;border:1px solid rgba(255,255,255,0.08);background:rgba(255,255,255,0.02);text-align:center}
    .stat-box .sb-label{font-size:0.62rem;color:#8892b0}.stat-box .sb-value{font-size:1rem;font-weight:700;font-family:"JetBrains Mono",monospace!important}
    .criteria-item{padding:10px;margin-bottom:6px;border-radius:10px;border:1px solid rgba(255,255,255,0.06);background:rgba(255,255,255,0.02)}
    .criteria-item.nc{border-color:rgba(156,39,176,0.2);background:rgba(156,39,176,0.04)}
    .criteria-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}
    .criteria-name{font-size:0.78rem;font-weight:600;color:#e6f1ff}
    .criteria-bar{width:100%;height:3px;border-radius:2px;background:rgba(255,255,255,0.05);margin-bottom:3px}.criteria-bar-fill{height:100%;border-radius:2px}
    .criteria-detail{font-size:0.65rem;color:#8892b0}
    .new-badge{font-size:0.55rem;padding:1px 5px;border-radius:6px;background:rgba(156,39,176,0.3);color:#ce93d8;margin-left:4px}
    .stTabs [data-baseweb="tab-list"]{gap:0;background:rgba(0,210,190,0.05);border-radius:14px;border:1px solid rgba(0,210,190,0.2);padding:3px}
    .stTabs [data-baseweb="tab"]{border-radius:12px;color:#4a5568;font-weight:600;padding:8px 10px;font-size:0.78rem}
    .stTabs [aria-selected="true"]{background:rgba(0,210,190,0.15)!important;color:#00d2be!important}
    .stTabs [data-baseweb="tab-highlight"]{display:none}.stTabs [data-baseweb="tab-border"]{display:none}
    .streamlit-expanderHeader{background:rgba(0,210,190,0.05)!important;border-radius:12px!important;border:1px solid rgba(0,210,190,0.15)!important;color:#00d2be!important;font-weight:600!important}
    .element-container{margin:0!important;padding:0!important}.stMarkdown{margin:0!important}
    div[data-testid="stVerticalBlock"]>div{gap:0.3rem!important}
    .stButton>button{background:rgba(0,210,190,0.1)!important;border:1px solid rgba(0,210,190,0.3)!important;color:#00d2be!important;border-radius:12px!important;font-weight:600!important;width:100%!important}
    .stButton>button:hover{background:rgba(0,210,190,0.2)!important;border-color:rgba(0,210,190,0.5)!important}
    .disclaimer{margin-top:14px;padding:10px;border-radius:12px;background:rgba(255,107,107,0.05);border:1px solid rgba(255,107,107,0.1);font-size:0.62rem;color:#8892b0;text-align:center;line-height:1.6}
</style>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;800&display=swap" rel="stylesheet">
''', unsafe_allow_html=True)

def load_watchlist():
    try:
        p = os.path.join(os.path.dirname(__file__), 'tickers.txt')
        with open(p, 'r') as f: return [t.strip() for t in f.read().split(',') if t.strip()]
    except: return ['HIMS','ZETA','ADBE','TTD','UNH','OSCR','RARE','UP','SMCI','IONQ','PLTR','SOFI']

DEFAULT_WATCHLIST = load_watchlist()

def get_et_now():
    return datetime.now(pytz.timezone('US/Eastern'))

def get_ksa_now():
    return datetime.now(pytz.timezone('Asia/Riyadh'))

def is_market_open():
    n = get_et_now()
    if n.weekday() > 4: return False
    return n.replace(hour=9,minute=30,second=0) <= n <= n.replace(hour=16,minute=0,second=0)

def is_daily_scan_window():
    """Check if we're in the daily auto-scan window: 3:00-3:30 AM KSA (Asia/Riyadh)"""
    n = get_ksa_now()
    # Skip weekends (Sat/Sun in KSA — but US market closes Fri, so daily scan runs Mon-Fri nights)
    # 3:00 AM KSA on a weekday = after US market close the previous day
    return n.replace(hour=3,minute=0,second=0) <= n <= n.replace(hour=3,minute=30,second=0)

def get_market_status():
    n = get_et_now()
    if n.weekday() > 4: return "CLOSED","Weekend","#ff6b6b"
    mo = n.replace(hour=9,minute=30,second=0); mc = n.replace(hour=16,minute=0,second=0)
    if n < mo: d=int((mo-n).total_seconds()/60); return "PRE-MARKET",f"Opens in {d//60}h {d%60}m","#ffd700"
    elif n > mc: return "CLOSED","After hours","#ff6b6b"
    else: d=int((mc-n).total_seconds()/60); return "OPEN",f"Closes in {d//60}h {d%60}m","#00ff88"

def get_next_daily_scan_str():
    """Get a string showing when the next daily auto-scan will run"""
    ksa = get_ksa_now()
    if ksa.hour < 3:
        return f"Today at 3:00 AM KSA ({(3 - ksa.hour - 1)}h {60 - ksa.minute}m)"
    else:
        return "Tomorrow at 3:00 AM KSA"

def should_auto_scan(tf_key):
    # Only daily timeframe auto-scans (at 3:00 AM KSA)
    # All other timeframes (30m, 1h, 4h) are manual only
    if tf_key != '1d':
        return False
    if not is_daily_scan_window():
        return False
    last = st.session_state.get(f'last_scan_{tf_key}')
    if last:
        # Don't scan again if already scanned today (KSA date)
        ksa_now = get_ksa_now()
        last_ksa = last.astimezone(pytz.timezone('Asia/Riyadh'))
        if last_ksa.date() == ksa_now.date():
            return False
    return True

def _send_email(subject, html_body):
    """Send email via Google Apps Script webhook (HTTPS — no SMTP needed)"""
    if not GMAIL_WEBHOOK_URL:
        return False, "Webhook URL not configured"
    try:
        resp = requests.post(
            GMAIL_WEBHOOK_URL,
            json={"to": ALERT_TO_EMAIL, "subject": subject, "html": html_body},
            timeout=30
        )
        result = resp.json()
        if result.get('status') == 'ok':
            return True, "sent"
        else:
            return False, result.get('message', 'Unknown error')[:100]
    except Exception as e:
        return False, str(e)[:100]

def send_email_alert(stocks, tf_key):
    if not GMAIL_WEBHOOK_URL: return False, "not configured"
    tf = TIMEFRAMES[tf_key]
    ksa_str = get_ksa_now().strftime('%I:%M %p KSA')
    et_str = get_et_now().strftime('%I:%M %p ET')
    subj = f"[Explosion Hunter] {tf['label']} Alert: {len(stocks)} Stocks (Score {ALERT_SCORE_THRESHOLD}+) - {ksa_str}"
    body = f'<div style="font-family:Arial;max-width:600px;margin:0 auto;background:#0d1b2a;color:#e6f1ff;padding:20px;border-radius:12px;"><h2 style="color:#00d2be;text-align:center;">{tf["label"]} Scan Results</h2><p style="color:#8892b0;text-align:center;">{ksa_str} ({et_str}) | {len(stocks)} stocks | Score {ALERT_SCORE_THRESHOLD}+</p><hr style="border-color:rgba(0,210,190,0.2);">'
    for i,s in enumerate(stocks,1):
        sc = '#00ff88' if s['explosionScore']>=85 else '#00d2be' if s['explosionScore']>=70 else '#ffd700'
        body += f'<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(0,210,190,0.15);border-radius:12px;padding:14px;margin:10px 0;"><div style="display:flex;justify-content:space-between;align-items:center;"><div><span style="font-size:11px;color:#8892b0;">#{i}</span><span style="font-size:24px;font-weight:800;color:{sc};margin-left:6px;">{s["explosionScore"]}</span></div><div style="text-align:right;"><div style="font-size:20px;font-weight:800;color:#00d2be;">{s["ticker"]}</div><div style="font-size:12px;color:#8892b0;">{s["name"]} · {s["capCategory"]}</div></div></div><div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px;margin-top:10px;"><div style="text-align:center;"><div style="font-size:10px;color:#8892b0;">Price</div><div style="font-size:14px;font-weight:700;color:#00ff88;">${s["price"]}</div></div><div style="text-align:center;"><div style="font-size:10px;color:#8892b0;">Short%</div><div style="font-size:14px;font-weight:700;color:#ff4444;">{s["shortInterest"]}%</div></div><div style="text-align:center;"><div style="font-size:10px;color:#8892b0;">Vol</div><div style="font-size:14px;font-weight:700;color:#ff8800;">+{s["volumeChange"]:.0f}%</div></div><div style="text-align:center;"><div style="font-size:10px;color:#8892b0;">RSI</div><div style="font-size:14px;font-weight:700;">{s["rsi"]}</div></div></div><div style="margin-top:8px;font-size:11px;color:#8892b0;">Pattern:{s["historicalMatch"]}% · MFI:{s["mfi"]}{"· Squeeze("+str(s["squeezeBars"])+")" if s["ttmSqueeze"] else ""}</div></div>'
    body += '<hr style="border-color:rgba(0,210,190,0.2);"><p style="color:#4a5568;font-size:11px;text-align:center;">⚠️ Not financial advice.</p></div>'
    return _send_email(subj, body)

def send_scan_summary(all_stocks, failed_count, tf_key, duration):
    if not GMAIL_WEBHOOK_URL: return False, "not configured"
    tf = TIMEFRAMES[tf_key]
    ksa_str = get_ksa_now().strftime('%I:%M %p KSA')
    et_str = get_et_now().strftime('%I:%M %p ET')
    top_stocks = sorted(all_stocks, key=lambda x: x['explosionScore'], reverse=True)[:20]
    alerts = [s for s in all_stocks if s['explosionScore'] >= ALERT_SCORE_THRESHOLD]
    subj = f"[Explosion Hunter] {tf['label']} Scan Complete - {len(all_stocks)} candidates, {len(alerts)} alerts - {ksa_str}"
    body = f'<div style="font-family:Arial;max-width:600px;margin:0 auto;background:#0d1b2a;color:#e6f1ff;padding:20px;border-radius:12px;"><h2 style="color:#00d2be;text-align:center;">{tf["label"]} Scan Summary</h2><p style="color:#8892b0;text-align:center;">{ksa_str} ({et_str})</p>'
    body += f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin:15px 0;"><div style="text-align:center;padding:10px;border-radius:10px;background:rgba(0,210,190,0.08);"><div style="font-size:11px;color:#8892b0;">Candidates</div><div style="font-size:24px;font-weight:800;color:#00d2be;">{len(all_stocks)}</div></div><div style="text-align:center;padding:10px;border-radius:10px;background:rgba(255,107,107,0.08);"><div style="font-size:11px;color:#8892b0;">Alerts ({ALERT_SCORE_THRESHOLD}+)</div><div style="font-size:24px;font-weight:800;color:#ff6b6b;">{len(alerts)}</div></div><div style="text-align:center;padding:10px;border-radius:10px;background:rgba(255,215,0,0.08);"><div style="font-size:11px;color:#8892b0;">Failed</div><div style="font-size:24px;font-weight:800;color:#ffd700;">{failed_count}</div></div></div>'
    body += f'<div style="font-size:12px;color:#8892b0;text-align:center;margin-bottom:10px;">Duration: {duration}</div><hr style="border-color:rgba(0,210,190,0.2);"><h3 style="color:#00d2be;font-size:14px;margin:10px 0;">Top 20 by Score:</h3>'
    for i,s in enumerate(top_stocks,1):
        sc = '#00ff88' if s['explosionScore']>=85 else '#00d2be' if s['explosionScore']>=70 else '#ffd700' if s['explosionScore']>=55 else '#8892b0'
        body += f'<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 12px;margin:4px 0;border-radius:8px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.05);"><div style="display:flex;align-items:center;gap:8px;"><span style="font-size:11px;color:#4a5568;">#{i}</span><span style="font-size:16px;font-weight:800;color:#00d2be;">{s["ticker"]}</span><span style="font-size:11px;color:#8892b0;">{s["name"]}</span></div><div style="display:flex;align-items:center;gap:12px;"><span style="font-size:11px;color:#8892b0;">${s["price"]} · SI:{s["shortInterest"]}% · RSI:{s["rsi"]}</span><span style="font-size:18px;font-weight:800;color:{sc};">{s["explosionScore"]}</span></div></div>'
    body += '<hr style="border-color:rgba(0,210,190,0.2);"><p style="color:#4a5568;font-size:11px;text-align:center;">⚠️ Not financial advice. Full results at hunter.up.railway.app</p></div>'
    return _send_email(subj, body)

def fetch_stock_data(ticker, interval='1d', period='1y', max_retries=2):
    for attempt in range(max_retries+1):
        try:
            time.sleep(0.3)
            stk = yf.Ticker(ticker); info = stk.info or {}
            hist = stk.history(period=period, interval=interval)
            if hist.empty or len(hist)<14:
                if attempt<max_retries: time.sleep(1); continue
                return None
            cp=hist['Close'].iloc[-1]; pc=hist['Close'].iloc[-2] if len(hist)>1 else cp
            dcp=((cp-pc)/pc)*100
            av=hist['Volume'].iloc[-20:].mean() if len(hist)>=20 else hist['Volume'].mean()
            cv=hist['Volume'].iloc[-1]; vr=(cv/av*100)-100 if av>0 else 0
            v3=hist['Volume'].iloc[-3:].mean() if len(hist)>=3 else cv; vtr=v3>av*1.5
            d=hist['Close'].diff(); g=d.where(d>0,0); l=-d.where(d<0,0)
            ag=g.rolling(14).mean(); al=l.rolling(14).mean(); rs=ag/al; rsi=100-(100/(1+rs))
            crsi=rsi.iloc[-1] if not rsi.empty and not np.isnan(rsi.iloc[-1]) else 50
            bl=min(20,len(hist)-1); sm=hist['Close'].rolling(bl).mean(); sd=hist['Close'].rolling(bl).std()
            bu=sm+(2*sd); blo=sm-(2*sd)
            bw=((bu-blo)/sm*100).iloc[-1] if not sm.empty else 10
            bws=(bu-blo)/sm*100; bwm=bws.iloc[-bl:].min() if len(bws)>=bl else bw
            bsq=bw<=bwm*1.1
            tr=pd.DataFrame({'hl':hist['High']-hist['Low'],'hc':abs(hist['High']-hist['Close'].shift(1)),'lc':abs(hist['Low']-hist['Close'].shift(1))}).max(axis=1)
            atr=tr.rolling(bl).mean(); ku=sm+(1.5*atr); kl=sm-(1.5*atr)
            tsq=False; sb=0
            if len(bu)>=bl and len(ku)>=bl:
                for i in range(1,min(21,len(bu))):
                    try:
                        if bu.iloc[-i]<ku.iloc[-i] and blo.iloc[-i]>kl.iloc[-i]: sb+=1; tsq=True
                        else: break
                    except: break
            obv=[0]
            for i in range(1,len(hist)):
                if hist['Close'].iloc[i]>hist['Close'].iloc[i-1]: obv.append(obv[-1]+hist['Volume'].iloc[i])
                elif hist['Close'].iloc[i]<hist['Close'].iloc[i-1]: obv.append(obv[-1]-hist['Volume'].iloc[i])
                else: obv.append(obv[-1])
            os_=pd.Series(obv,index=hist.index); osm=os_.rolling(bl).mean()
            ot='Bullish' if os_.iloc[-1]>osm.iloc[-1] else 'Bearish'
            if os_.iloc[-1]>osm.iloc[-1]*1.1: ot='Strong Bullish'
            tp=(hist['High']+hist['Low']+hist['Close'])/3; mf=tp*hist['Volume']
            pf=mf.where(tp>tp.shift(1),0); nf=mf.where(tp<tp.shift(1),0)
            pmf=pf.rolling(14).sum(); nmf=nf.rolling(14).sum()
            mfi=100-(100/(1+pmf/nmf)); cmfi=mfi.iloc[-1] if not mfi.empty and not np.isnan(mfi.iloc[-1]) else 50
            h52=hist['High'].max(); l52=hist['Low'].min(); pfl=((cp-l52)/l52*100) if l52>0 else 0
            gut=None
            for i in range(len(hist)-2,max(0,len(hist)-60),-1):
                ga=hist['Low'].iloc[i+1]-hist['High'].iloc[i]
                if ga>cp*0.03: gut=hist['High'].iloc[i]; break
            si_=info.get('shortPercentOfFloat',0)
            if si_ is None: si_=0
            si_=si_*100 if si_<1 else si_
            sr=info.get('shortRatio',0) or 0
            fs=info.get('floatShares',0) or 0; fd=f'{fs/1e6:.0f}M' if fs>1e6 else f'{fs/1e3:.0f}K'; fsm=fs<50e6 if fs>0 else False
            mc=info.get('marketCap',0) or 0
            if mc>=10e9: cl,cd='Large Cap',f'${mc/1e9:.1f}B'
            elif mc>=2e9: cl,cd='Mid Cap',f'${mc/1e9:.1f}B'
            elif mc>=300e6: cl,cd='Small Cap',f'${mc/1e6:.0f}M'
            else: cl,cd='Micro Cap',f'${mc/1e6:.0f}M'
            ind=(info.get('industry','') or '').lower(); sr_=(info.get('sector','') or '').lower()
            if any(k in ind for k in ['biotech','pharma','drug','therapeutic','genomic']): sec='biotech'
            elif any(k in ind for k in ['software','semiconductor','computer','internet','ai','quantum']): sec='tech'
            elif any(k in ind for k in ['bank','financial','insurance','fintech','payment']): sec='fintech'
            else: sec='other'
            ie=dcp>15 and vr>300
            ed_=None
            try:
                cal=stk.calendar
                if cal is not None:
                    if isinstance(cal,dict):
                        e=cal.get('Earnings Date',[])
                        if e: ed_=e[0] if isinstance(e,list) else e
                    elif isinstance(cal,pd.DataFrame) and not cal.empty:
                        if 'Earnings Date' in cal.index: ed_=cal.loc['Earnings Date'].iloc[0]
            except: pass
            cty,cla,cda='None','None',''
            if ed_:
                try:
                    e=pd.Timestamp(ed_); du=(e-pd.Timestamp.now()).days
                    if 0<=du<=14: cty,cla,cda='Earnings','Earnings Report',e.strftime('%b %d')
                except: pass
            if sec=='biotech' and cty=='None': cty,cla,cda='FDA','Potential FDA','Upcoming'
            ip=info.get('heldPercentInsiders',0) or 0; ib=1 if ip>0.1 else 0
            return {'ticker':ticker,'name':info.get('shortName',ticker),'exchange':info.get('exchange','N/A'),'sector':sec,'marketCap':cd,'capCategory':cl,'price':round(cp,2),'prevClose':round(pc,2),'dailyChangePct':round(dcp,2),'low52':round(l52,2),'high52':round(h52,2),'pctFromLow':round(pfl,2),'shortInterest':round(si_,1),'shortRatio':round(sr,1),'rsi':round(crsi,1),'mfi':round(cmfi,1),'volumeChange':round(vr,0),'avgVolume':av,'currentVolume':cv,'volumeMultiple':round(cv/av,1) if av>0 else 1,'volTrendRising':vtr,'catalyst':{'type':cty,'label':cla,'date':cda},'news':vtr and vr>200,'ttmSqueeze':tsq,'squeezeBars':sb,'bollingerSqueeze':bsq,'bbWidth':round(bw,2),'obvTrend':ot,'float':fd,'floatShares':fs,'floatSmall':fsm,'gapUpTarget':round(gut,2) if gut else None,'insiderBuys':ib,'insiderPct':round(ip*100,1),'isExploding':ie}
        except:
            if attempt<max_retries: time.sleep(1.5); continue
            return None
    return None

def calc_score(s):
    sc={}
    si=s['shortInterest']; sc['shortInterest']=100 if si>=30 else 85 if si>=20 else 65 if si>=15 else 40 if si>=10 else 20 if si>=5 else 5
    ct=s['catalyst']['type']; sc['catalystEvent']=90 if ct=='FDA' else 80 if ct=='Earnings' else 70 if ct=='Partnership' else 10
    vc=s['volumeChange']; sc['volumeAnomaly']=100 if vc>=1000 else 90 if vc>=500 else 75 if vc>=300 else 60 if vc>=200 else 40 if vc>=100 else 20 if vc>=50 else 5
    ps=(25 if si>15 else 0)+(25 if vc>200 else 0)+(20 if s['rsi']<40 else 0)+(15 if s['ttmSqueeze'] else 0)+(15 if ct in['FDA','Earnings'] else 0); sc['historicalPattern']=min(ps,100)
    r=s['rsi']; sc['rsiPosition']=100 if r<25 else 90 if r<30 else 75 if r<35 else 60 if r<40 else 40 if r<50 else 20 if r<60 else 5
    p=s['pctFromLow']; sc['near52WeekLow']=95 if p<10 else 75 if p<20 else 50 if p<35 else 30 if p<50 else 10
    sc['newsBreaking']=85 if s['news'] else 10
    gs=(35 if si>15 else 0)+(30 if s['floatSmall'] else 0)+(35 if vc>200 else 0); sc['optionsGamma']=min(gs,100)
    sc['darkPoolActivity']=85 if vc>150 and abs(s['dailyChangePct'])<3 else 50 if vc>100 else 15
    sc['insiderBuying']=80 if s['insiderBuys']>0 else 10
    sc['floatRotation']=90 if s['floatSmall'] else 60 if s['floatShares']<100e6 else 30 if s['floatShares']<500e6 else 10
    sc['sectorMomentum']=85 if s['sector']=='biotech' else 70 if s['sector']=='tech' else 40
    sc['ttmSqueeze']=95 if s['ttmSqueeze'] and s['squeezeBars']>6 else 70 if s['ttmSqueeze'] else 45 if s['bollingerSqueeze'] else 10
    sc['gapFillPotential']=80 if s['gapUpTarget'] and s['gapUpTarget']>s['price']*1.1 else 50 if s['gapUpTarget'] else 10
    w={'shortInterest':18,'catalystEvent':16,'volumeAnomaly':14,'historicalPattern':12,'rsiPosition':8,'near52WeekLow':6,'newsBreaking':4,'optionsGamma':5,'darkPoolActivity':4,'insiderBuying':3,'floatRotation':3,'sectorMomentum':2,'ttmSqueeze':3,'gapFillPotential':2}
    tw=sum(w.values()); ws=sum(sc.get(k,0)*v for k,v in w.items())
    return round(ws/tw), sc

def fmt_time(sec):
    m,s=divmod(int(sec),60); return f"{m}:{s:02d}"

def scan_stocks(watchlist, tf_key):
    tf=TIMEFRAMES[tf_key]; results=[]; failed=[]
    t0=time.time(); pb=st.progress(0); tt=st.empty(); st_=st.empty(); stop_c=st.empty()
    total=len(watchlist); done=0; lock=threading.Lock(); stopped=False
    BS=50; batches=[watchlist[i:i+BS] for i in range(0,len(watchlist),BS)]
    for bi,batch in enumerate(batches):
        if stopped: break
        with stop_c:
            if st.button(f'⏹️ Stop {tf["label"]} Scan',key=f'stop_{tf_key}_{bi}',use_container_width=True):
                stopped=True
                sc_t={r['ticker'] for r in results}|set(failed); failed.extend([t for t in watchlist if t not in sc_t])
                st.session_state[f'data_{tf_key}']=results; st.session_state[f'failed_{tf_key}']=failed
                st.session_state[f'last_scan_{tf_key}']=get_et_now(); st.session_state[f'dur_{tf_key}']=fmt_time(time.time()-t0)
                st.session_state[f'stopped_{tf_key}']=True
                st.session_state['scanning_active']=False; st.session_state.pop('scanning_tf',None)
                pb.empty(); tt.empty(); st_.empty(); stop_c.empty(); st.rerun()
        def fetch_one(ticker):
            nonlocal done; d=fetch_stock_data(ticker,interval=tf['interval'],period=tf['period'])
            with lock: done+=1
            return (ticker,d)
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            futs={ex.submit(fetch_one,t):t for t in batch}
            for f in concurrent.futures.as_completed(futs):
                try:
                    tk,d=f.result()
                    if d:
                        score,det=calc_score(d)
                        if score>=40: d['explosionScore']=score; d['detailedScores']=det; d['historicalMatch']=det.get('historicalPattern',0); results.append(d)
                    else: failed.append(tk)
                except: pass
                el=time.time()-t0; pct=done/total; eta=(el/pct-el) if pct>0.05 else 0
                pb.progress(min(pct,1.0))
                tt.markdown(f'<div style="text-align:center;font-size:0.85rem;font-weight:700;color:#00d2be;font-family:JetBrains Mono,monospace;">{tf["icon"]} {tf["label"]} · ⏱️ {fmt_time(el)}{" · ETA "+fmt_time(eta) if eta>0 else ""}</div>',unsafe_allow_html=True)
                st_.markdown(f'<div style="text-align:center;font-size:0.75rem;color:#8892b0;">Scanning {done}/{total} · Batch {bi+1}/{len(batches)} · Found {len(results)}</div>',unsafe_allow_html=True)
        st.session_state[f'data_{tf_key}']=results; st.session_state[f'failed_{tf_key}']=failed
        if bi<len(batches)-1 and not stopped: time.sleep(2)
    dur=fmt_time(time.time()-t0); st.session_state[f'dur_{tf_key}']=dur; st.session_state[f'stopped_{tf_key}']=False
    rl=failed[:20]
    if rl:
        st_.markdown(f'<div style="text-align:center;font-size:0.75rem;color:#ffd700;">Retrying {len(rl)}...</div>',unsafe_allow_html=True)
        for tk in rl:
            time.sleep(0.5)
            try:
                d=fetch_stock_data(tk,interval=tf['interval'],period=tf['period'])
                if d:
                    score,det=calc_score(d)
                    if score>=40: d['explosionScore']=score; d['detailedScores']=det; d['historicalMatch']=det.get('historicalPattern',0); results.append(d); failed.remove(tk)
            except: pass
    tt.markdown(f'<div style="text-align:center;font-size:0.85rem;font-weight:700;color:#00ff88;font-family:JetBrains Mono,monospace;">✅ {tf["label"]} done — {dur} · {len(results)} candidates</div>',unsafe_allow_html=True)
    time.sleep(2); pb.empty(); tt.empty(); st_.empty(); stop_c.empty()
    return results, failed

def scol(s):
    if s>=85: return '#00ff88'
    if s>=70: return '#00d2be'
    if s>=55: return '#ffd700'
    return '#ff6b6b'

def slab(s):
    if s>=90: return 'Very High'
    if s>=80: return 'High'
    if s>=65: return 'Med-High'
    if s>=50: return 'Medium'
    return 'Low'

def fvol(v):
    if v>=1e9: return f'{v/1e9:.1f}B'
    if v>=1e6: return f'{v/1e6:.1f}M'
    if v>=1e3: return f'{v/1e3:.0f}K'
    return str(int(v))

def render_card(s):
    sc=scol(s['explosionScore']); sl=slab(s['explosionScore'])
    tags=[]
    if s['shortInterest']>10: tags.append(f'<span class="tag-pill" style="background:rgba(255,68,68,0.15);border:1px solid rgba(255,68,68,0.3);color:#ff4444;">🔴 Short {s["shortInterest"]}%</span>')
    if s['catalyst']['type']!='None':
        cc={'FDA':'#00d2be','Earnings':'#4CAF50','Partnership':'#9C27B0'}.get(s['catalyst']['type'],'#ffd700')
        ci={'FDA':'🔬','Earnings':'📊','Partnership':'🤝'}.get(s['catalyst']['type'],'📅')
        tags.append(f'<span class="tag-pill" style="background:{cc}15;border:1px solid {cc}40;color:{cc};">{ci} {s["catalyst"]["label"]}</span>')
    if s['volumeChange']>100: tags.append(f'<span class="tag-pill" style="background:rgba(255,136,0,0.15);border:1px solid rgba(255,136,0,0.3);color:#ff8800;">📈 +{s["volumeChange"]:.0f}%</span>')
    if s['ttmSqueeze']: tags.append(f'<span class="tag-pill" style="background:rgba(206,147,216,0.15);border:1px solid rgba(206,147,216,0.3);color:#ce93d8;">💥 Squeeze({s["squeezeBars"]})</span>')
    if s['floatSmall']: tags.append('<span class="tag-pill" style="background:rgba(0,188,212,0.15);border:1px solid rgba(0,188,212,0.3);color:#00bcd4;">🔁 Small Float</span>')
    vp=min(s['volumeChange']/20,100); rc='#00ff88' if s['rsi']<40 else '#ffd700' if s['rsi']<60 else '#ff6b6b'
    return f'<div class="stock-card"><div class="card-header"><div class="score-gauge" style="background:{sc}10;border:1px solid {sc}30;"><span class="score-label">Score</span><span class="score-value" style="color:{sc};">{s["explosionScore"]}</span><span class="score-text" style="color:{sc};">{sl}</span></div><div class="ticker-info"><div class="ticker">{s["ticker"]}</div><div class="name">{s["name"]} · {s["capCategory"]} {s["marketCap"]}</div></div></div><div class="tags-row">{"".join(tags)}</div><div class="vol-bar-container"><div class="vol-bar-label">Volume ({s["volumeMultiple"]}x avg)</div><div class="vol-bar-track"><div class="vol-bar-fill" style="width:{vp}%;"></div></div></div><div class="stat-boxes"><div class="stat-box"><div class="sb-label">Price</div><div class="sb-value" style="color:#00ff88;">${s["price"]}</div></div><div class="stat-box"><div class="sb-label">52W Low</div><div class="sb-value">${s["low52"]}</div></div><div class="stat-box"><div class="sb-label">SHORT</div><div class="sb-value" style="color:#ff4444;">{s["shortInterest"]}%</div></div><div class="stat-box"><div class="sb-label">RSI</div><div class="sb-value" style="color:{rc};">{s["rsi"]}</div></div></div><div class="stat-boxes"><div class="stat-box"><div class="sb-label">Pattern</div><div class="sb-value" style="color:{"#00ff88" if s["historicalMatch"]>70 else "#ffd700"};">{s["historicalMatch"]}%</div></div><div class="stat-box"><div class="sb-label">MFI</div><div class="sb-value" style="color:{"#00ff88" if s["mfi"]<30 else "#ffd700"};">{s["mfi"]}</div></div></div></div>'

def render_detail(s):
    ws={'shortInterest':('🔴','Short',18,0),'catalystEvent':('📅','Catalyst',16,0),'volumeAnomaly':('📈','Volume',14,0),'historicalPattern':('🔄','Pattern',12,0),'rsiPosition':('📉','RSI',8,0),'near52WeekLow':('⬇️','52W',6,0),'newsBreaking':('📰','News',4,0),'optionsGamma':('🎯','GEX',5,1),'darkPoolActivity':('🌑','DPool',4,1),'insiderBuying':('👔','Insider',3,1),'floatRotation':('🔁','Float',3,1),'sectorMomentum':('🏆','Sector',2,1),'ttmSqueeze':('💥','Squeeze',3,1),'gapFillPotential':('🕳️','Gap',2,1)}
    tw=sum(w[2] for w in ws.values()); d=s.get('detailedScores',{}); h='<div>'
    for k,(ic,nm,wt,nw) in ws.items():
        sc=d.get(k,0); bc='#00ff88' if sc>70 else '#ffd700' if sc>40 else '#ff6b6b'
        nc='nc' if nw else ''; nb='<span class="new-badge">NEW</span>' if nw else ''
        h+=f'<div class="criteria-item {nc}"><div class="criteria-header"><span class="criteria-name">{ic} {nm} {nb}</span><span class="mono" style="font-size:0.8rem;font-weight:700;color:{bc};">{sc}</span></div><div class="criteria-bar"><div class="criteria-bar-fill" style="width:{sc}%;background:{bc};"></div></div><div class="criteria-detail">Weight: {wt}/{tw} ({wt/tw*100:.0f}%)</div></div>'
    return h+'</div>'

def render_tab(tf_key, wl, manual=False):
    tf=TIMEFRAMES[tf_key]; dk=f'data_{tf_key}'
    has=len(st.session_state.get(dk,[]))>0; was=st.session_state.get(f'stopped_{tf_key}',False)

    # Check if ANY scan is currently running — don't start another one
    any_scanning = st.session_state.get('scanning_active', False)

    do_scan=manual
    # Only auto-scan if interval elapsed AND no other scan is running
    if not do_scan and not was and not any_scanning and should_auto_scan(tf_key):
        do_scan=True

    if do_scan:
        try:
            st.session_state['scanning_active'] = True
            st.session_state['scanning_tf'] = tf_key
            res,fail=scan_stocks(wl,tf_key)
            st.session_state[dk]=res; st.session_state[f'failed_{tf_key}']=fail
            st.session_state[f'last_scan_{tf_key}']=get_et_now()
            st.session_state['scanning_active'] = False
            st.session_state.pop('scanning_tf', None)
            ec=bool(GMAIL_WEBHOOK_URL)
            email_status = ''
            if ec and res:
                try:
                    dur = st.session_state.get(f'dur_{tf_key}', '--:--')
                    failed_count = len(fail)
                    ok1, msg1 = send_scan_summary(res, failed_count, tf_key, dur)
                    if ok1:
                        st.session_state[f'emails_{tf_key}'] = st.session_state.get(f'emails_{tf_key}', 0) + 1
                        email_status = f'sent ({msg1})'
                    else:
                        email_status = f'failed: {msg1}'
                    trig = [s for s in res if s['explosionScore'] >= ALERT_SCORE_THRESHOLD]
                    if trig:
                        ok2, msg2 = send_email_alert(trig, tf_key)
                        if ok2:
                            st.session_state[f'emails_{tf_key}'] = st.session_state.get(f'emails_{tf_key}', 0) + 1
                except Exception as e:
                    email_status = f'crash: {str(e)[:150]}'
            st.session_state[f'email_status_{tf_key}'] = email_status
        except Exception as e:
            st.session_state['scanning_active'] = False
            st.session_state.pop('scanning_tf', None)
            st.session_state[f'scan_error_{tf_key}'] = str(e)[:200]
        st.rerun()

    # Show scan error if any
    scan_err = st.session_state.get(f'scan_error_{tf_key}', '')
    if scan_err:
        st.markdown(f'<div style="padding:10px;border-radius:10px;background:rgba(255,68,68,0.1);border:1px solid rgba(255,68,68,0.3);margin-bottom:8px;font-size:0.75rem;color:#ff6b6b;">❌ Scan Error: {scan_err}</div>',unsafe_allow_html=True)

    # Display results
    stocks=st.session_state.get(dk,[]); failed=st.session_state.get(f'failed_{tf_key}',[])
    ls=st.session_state.get(f'last_scan_{tf_key}'); dur=st.session_state.get(f'dur_{tf_key}','--:--')
    em=st.session_state.get(f'emails_{tf_key}',0)
    ls_str=ls.strftime('%H:%M:%S ET') if ls else 'Never'
    sch='Auto at 3:00 AM KSA' if tf_key=='1d' else 'Manual only'
    # Show if currently scanning another timeframe
    active_tf = st.session_state.get('scanning_tf')
    busy_msg = ''
    if active_tf and active_tf != tf_key:
        busy_msg = f' · <span style="color:#ffd700;">⏳ {TIMEFRAMES[active_tf]["label"]} scan running</span>'
    st.markdown(f'<div style="padding:8px 12px;border-radius:10px;background:rgba(0,210,190,0.04);border:1px solid rgba(0,210,190,0.1);margin-bottom:8px;font-size:0.72rem;"><span style="color:#00d2be;font-weight:700;">{tf["icon"]} {tf["label"]}</span> · Last: {ls_str} · ⏱️{dur} · Emails: {em} · <span style="color:#4a5568;">{sch}</span>{busy_msg}</div>',unsafe_allow_html=True)
    # Show email status
    e_status = st.session_state.get(f'email_status_{tf_key}', '')
    if e_status:
        if 'sent' in e_status:
            st.markdown(f'<div style="font-size:0.7rem;color:#00ff88;text-align:center;margin-bottom:6px;">✅ {e_status}</div>',unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="font-size:0.7rem;color:#ff6b6b;text-align:center;margin-bottom:6px;word-break:break-all;">❌ {e_status}</div>',unsafe_allow_html=True)
    if not stocks: st.markdown(f'<div style="text-align:center;padding:20px;color:#8892b0;">No data yet — press scan or wait for auto-scan</div>',unsafe_allow_html=True); return
    ss=sorted(stocks,key=lambda x:x['explosionScore'],reverse=True); hc=len([s for s in ss if s['explosionScore']>=ALERT_SCORE_THRESHOLD])
    st.markdown(f'<div style="text-align:center;font-size:0.85rem;font-weight:700;color:#e6f1ff;margin:6px 0;">{len(ss)} candidates · {hc} alerts (≥{ALERT_SCORE_THRESHOLD})</div>',unsafe_allow_html=True)
    if failed:
        with st.expander(f'⚠️ Failed ({len(failed)})'): st.markdown(f'<div style="font-size:0.7rem;color:#8892b0;line-height:1.8;">{", ".join(sorted(failed[:100]))}{"..." if len(failed)>100 else ""}</div>',unsafe_allow_html=True)
    for s in ss:
        st.markdown(render_card(s),unsafe_allow_html=True)
        with st.expander(f'🔍 {s["ticker"]}'): st.markdown(render_detail(s),unsafe_allow_html=True)

def main():
    st.markdown('<div class="main-header"><div style="font-size:2rem;">🎯</div><h1>Explosion Hunter</h1><div class="subtitle">Multi-Timeframe · 1,160 Halal Stocks · Auto Daily Scan at 3AM KSA</div></div>',unsafe_allow_html=True)
    status,detail,color=get_market_status(); dc="live-dot" if status=="OPEN" else "live-dot off"
    ksa_str = get_ksa_now().strftime('%I:%M %p KSA')
    et_str = get_et_now().strftime('%I:%M %p ET')
    st.markdown(f'<div style="text-align:center;"><div class="live-badge"><div class="{dc}"></div><span style="color:{color};">{status}</span><span style="color:#8892b0;">{detail}</span><span style="color:#8892b0;">NYSE/NASDAQ</span></div><div style="font-size:0.7rem;color:#4a5568;margin-top:4px;">{ksa_str} · {et_str}</div></div>',unsafe_allow_html=True)
    next_scan = get_next_daily_scan_str()
    st.markdown(f'<div style="padding:10px 14px;border-radius:12px;background:rgba(0,255,136,0.03);border:1px solid rgba(0,255,136,0.1);margin:8px 0;font-size:0.72rem;"><div style="font-weight:700;color:#00ff88;margin-bottom:4px;">📡 Scan Schedule</div><div style="color:#8892b0;">📅 <b>Daily</b> auto-scan at <b>3:00 AM KSA</b> (after US market close)</div><div style="color:#8892b0;margin-top:2px;">⚡ 30min · ⏰ 1H · 📊 4H — <b>manual only</b> (use buttons below)</div><div style="color:#4a5568;font-size:0.65rem;margin-top:4px;">Next daily scan: {next_scan} · Email on Score≥{ALERT_SCORE_THRESHOLD}</div></div>',unsafe_allow_html=True)
    with st.expander(f'⚙️ Watchlist ({len(DEFAULT_WATCHLIST)} stocks)'):
        ct=st.text_area('Tickers',value=', '.join(DEFAULT_WATCHLIST),height=120)
        wl=[t.strip().upper() for t in ct.split(',') if t.strip()]
    ec=bool(GMAIL_WEBHOOK_URL)
    with st.expander('📧 Email'):
        if ec:
            st.markdown(f'<div style="font-size:0.8rem;color:#00ff88;">✅ Webhook configured → {ALERT_TO_EMAIL}</div>',unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:0.75rem;color:#8892b0;margin-top:4px;">Alert threshold: Score ≥ {ALERT_SCORE_THRESHOLD}</div>',unsafe_allow_html=True)
            if st.button('📧 Send Test Email', key='test_email', use_container_width=True):
                test = [{'ticker':'TEST','name':'Test Alert','capCategory':'Test','marketCap':'$0','price':10.0,'shortInterest':25.0,'volumeChange':500,'rsi':35.0,'mfi':28.0,'catalyst':{'type':'FDA','label':'Test Event','date':'Now'},'historicalMatch':85,'explosionScore':85,'ttmSqueeze':True,'squeezeBars':8,'low52':8.0,'high52':15.0,'pctFromLow':25.0,'shortRatio':5.0,'bbWidth':5.0,'obvTrend':'Bullish','float':'10M','floatShares':10e6,'floatSmall':True,'gapUpTarget':None,'insiderBuys':1,'insiderPct':5.0,'isExploding':False,'prevClose':9.5,'dailyChangePct':5.3,'avgVolume':1e6,'currentVolume':6e6,'volumeMultiple':6.0,'volTrendRising':True,'bollingerSqueeze':True,'news':True,'exchange':'TEST','sector':'biotech','detailedScores':{}}]
                ok, msg = send_email_alert(test, '1d')
                if ok:
                    st.success(f'✅ Email sent! Check inbox of {ALERT_TO_EMAIL}')
                else:
                    st.error(f'❌ Failed: {msg}')
        else: st.markdown('<div style="font-size:0.8rem;color:#ff6b6b;">⚠️ Set GMAIL_WEBHOOK_URL in Railway Variables</div>',unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.8rem;font-weight:700;color:#e6f1ff;margin:8px 0;">Manual Scan:</div>',unsafe_allow_html=True)
    c1,c2,c3,c4=st.columns(4); ms={}
    with c1:
        if st.button('⚡ 30m',key='m30',use_container_width=True): st.session_state.pop('stopped_30m',None); ms['30m']=True
    with c2:
        if st.button('⏰ 1H',key='m1h',use_container_width=True): st.session_state.pop('stopped_1h',None); ms['1h']=True
    with c3:
        if st.button('📊 4H',key='m4h',use_container_width=True): st.session_state.pop('stopped_4h',None); ms['4h']=True
    with c4:
        if st.button('📅 Daily',key='m1d',use_container_width=True): st.session_state.pop('stopped_1d',None); ms['1d']=True
    t1,t2,t3,t4=st.tabs(['📅 Daily','⚡ 30min','⏰ 1 Hour','📊 4 Hours'])
    with t1: render_tab('1d',wl,ms.get('1d',False))
    with t2: render_tab('30m',wl,ms.get('30m',False))
    with t3: render_tab('1h',wl,ms.get('1h',False))
    with t4: render_tab('4h',wl,ms.get('4h',False))
    st.markdown('<div class="disclaimer">⚠️ For educational purposes only. Not financial advice. Trading involves high risk.</div>',unsafe_allow_html=True)
    # Auto-refresh every 5 minutes ONLY during the daily scan window (2:55-3:30 AM KSA)
    ksa_h = get_ksa_now().hour
    if ksa_h == 2 and get_ksa_now().minute >= 55 or ksa_h == 3 and get_ksa_now().minute <= 30:
        st.markdown('<meta http-equiv="refresh" content="300">',unsafe_allow_html=True)

if __name__=='__main__': main()
