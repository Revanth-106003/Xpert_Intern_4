"""Design system: tokens, typography, component skins and motion.

Streamlit widgets are re-skinned through stable hooks only:
``data-testid`` attributes and ``.st-key-<key>`` classes generated from
widget/container keys. Motion is CSS-only (transform/opacity) and is disabled
for users who prefer reduced motion.
"""
from __future__ import annotations

import streamlit as st

FONTS = (
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&"
    "family=Plus+Jakarta+Sans:wght@600;700;800&family=JetBrains+Mono:wght@500&display=swap"
)

CSS = r"""
@import url('__FONTS__');

:root {
  --navy-900: #0E1830;
  --navy-800: #14213D;
  --navy-700: #1D3557;
  --navy-600: #2B4A73;
  --blue-600: #2563EB;
  --blue-700: #1D4ED8;
  --blue-50:  #EEF3FE;
  --blue-100: #DCE6FD;
  --bg:       #F5F7FB;
  --card:     #FFFFFF;
  --text:     #172033;
  --text-2:   #64748B;
  --text-3:   #94A3B8;
  --border:   #E3E8F0;
  --border-2: #EDF1F7;
  --success:  #16A34A;  --success-bg: #EAF7EF;
  --warning:  #B45309;  --warning-accent: #F59E0B; --warning-bg: #FEF6E7;
  --error:    #DC2626;  --error-bg: #FDEDED;
  --radius-sm: 8px; --radius: 12px; --radius-lg: 16px;
  --shadow-xs: 0 1px 2px rgba(20,33,61,.05);
  --shadow-sm: 0 1px 3px rgba(20,33,61,.06), 0 1px 2px rgba(20,33,61,.04);
  --shadow-md: 0 8px 24px -8px rgba(20,33,61,.14), 0 2px 6px rgba(20,33,61,.05);
  --ease: cubic-bezier(.2,.7,.2,1);
  --font-body: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
  --font-head: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, Consolas, monospace;
}

/* ---------- base ---------- */
html, body, .stApp { background: var(--bg) !important; color: var(--text); font-family: var(--font-body); }
.stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button { font-family: var(--font-body); }
.stApp h1, .stApp h2, .stApp h3, .stApp h4 { font-family: var(--font-head); color: var(--text); letter-spacing: -.01em; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMainBlockContainer"], .block-container {
  padding-top: 2.2rem !important; padding-bottom: 4rem !important; max-width: 1320px;
}
[data-testid="stMain"] [data-testid="stVerticalBlock"] { gap: 1rem; }
#MainMenu, [data-testid="stStatusWidget"] { visibility: hidden; }
a { color: var(--blue-600); }

/* page entrance */
@keyframes tcg-rise { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
@keyframes tcg-fade { from { opacity: 0; } to { opacity: 1; } }
[data-testid="stMainBlockContainer"] > div { animation: tcg-fade .35s var(--ease) both; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, var(--navy-800) 0%, var(--navy-900) 100%) !important;
  border-right: 1px solid rgba(255,255,255,.04);
}
[data-testid="stSidebar"] * { color: #C9D3E6; }
[data-testid="stSidebarHeader"] { padding: 1.25rem 1.25rem .5rem; }
[data-testid="stSidebarHeader"] img { height: 2.4rem !important; max-width: 100%; }
[data-testid="stSidebarNav"] { padding-top: .25rem; }
[data-testid="stSidebarNavItems"] { padding: 0 .75rem; gap: 2px; }
[data-testid="stSidebarNavLink"] {
  border-radius: 10px; padding: .55rem .8rem; margin: 1px 0;
  transition: background-color .2s var(--ease), transform .2s var(--ease);
}
[data-testid="stSidebarNavLink"] span { color: #B8C4DA !important; font-weight: 500; font-size: .92rem; }
[data-testid="stSidebarNavLink"]:hover { background: rgba(255,255,255,.06) !important; transform: translateX(2px); }
[data-testid="stSidebarNavLink"][aria-current="page"] {
  background: rgba(37,99,235,.22) !important; box-shadow: inset 3px 0 0 #5B8CF5;
}
[data-testid="stSidebarNavLink"][aria-current="page"] span { color: #FFFFFF !important; font-weight: 600; }
[data-testid="stSidebarNavSeparator"] { border-color: rgba(255,255,255,.08); }
[data-testid="stNavSectionHeader"], [data-testid="stNavSectionHeader"] * { font-size: .68rem !important; letter-spacing: .12em; text-transform: uppercase; color: #7385A6 !important; font-weight: 600 !important; }
[data-testid="stSidebarCollapseButton"] svg, [data-testid="stSidebarCollapsedControl"] svg { color: #C9D3E6; }
[data-testid="stSidebarUserContent"] { padding: .5rem 1.25rem 1.5rem; }

.sb-section { font-size: .68rem; letter-spacing: .12em; text-transform: uppercase; color: #7385A6 !important;
  font-weight: 600; margin: 1.1rem 0 .55rem; }
.sb-card { background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.07); border-radius: 12px;
  padding: .8rem .9rem; }
.sb-row { display: flex; justify-content: space-between; align-items: center; font-size: .82rem; padding: .2rem 0; }
[data-testid="stSidebar"] .sb-row b { color: #fff !important; font-weight: 600; }
[data-testid="stMain"] .sb-row b { font-weight: 600; text-align: right; word-break: break-word; }
.sb-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: .45rem; }
.sb-dot.ok { background: #34D399; box-shadow: 0 0 0 3px rgba(52,211,153,.18); }
.sb-dot.bad { background: #F87171; box-shadow: 0 0 0 3px rgba(248,113,113,.18); }
.sb-foot { font-size: .72rem; color: #6B7C9C !important; margin-top: 1.2rem; line-height: 1.5; }

/* ---------- page header ---------- */
.tcg-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 1rem;
  margin-bottom: .4rem; animation: tcg-rise .45s var(--ease) both; }
.tcg-eyebrow { display: inline-flex; align-items: center; gap: .4rem; font-size: .72rem; font-weight: 600;
  letter-spacing: .12em; text-transform: uppercase; color: var(--blue-600); margin-bottom: .45rem; }
.stApp h1.tcg-title, .tcg-title { font-family: var(--font-head); font-size: 1.9rem !important; font-weight: 800; color: var(--navy-800);
  line-height: 1.2; margin: 0 !important; padding: 0 !important; letter-spacing: -.02em; }
[data-testid="stHeaderActionElements"], .stApp h1 a[href^="#"] { display: none !important; }
.tcg-subtitle { color: var(--text-2); font-size: .98rem; margin-top: .4rem; max-width: 760px; line-height: 1.55; }

/* ---------- hero ---------- */
.tcg-hero { position: relative; overflow: hidden; border-radius: var(--radius-lg); padding: 2.2rem 2.4rem;
  background: radial-gradient(1200px 400px at 100% 0%, rgba(37,99,235,.35), transparent 60%),
              linear-gradient(135deg, var(--navy-800) 0%, var(--navy-700) 100%);
  color: #E6ECF7; box-shadow: var(--shadow-md); animation: tcg-rise .5s var(--ease) both; }
.tcg-hero::after { content: ""; position: absolute; inset: 0; pointer-events: none;
  background-image: linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px);
  background-size: 28px 28px; mask-image: linear-gradient(90deg, transparent 30%, #000 100%); }
.stApp .tcg-hero h1 { color: #fff !important; font-size: 2.05rem !important; font-weight: 800; margin: .35rem 0 .6rem !important; padding: 0 !important; letter-spacing: -.02em; }
.tcg-hero p { color: #B9C6DE; font-size: 1rem; max-width: 680px; line-height: 1.6; margin: 0; }
.tcg-hero .tcg-eyebrow { color: #8FB0FA; }
.tcg-hero-chips { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: 1.2rem; position: relative; z-index: 1; }
.tcg-hero-chip { font-size: .78rem; padding: .3rem .7rem; border-radius: 999px; color: #DCE5F5;
  background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.1); }

/* ---------- cards ---------- */
.tcg-card, [class*="st-key-card"] {
  background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
  box-shadow: var(--shadow-sm); transition: box-shadow .25s var(--ease), border-color .25s var(--ease), transform .25s var(--ease);
  animation: tcg-rise .45s var(--ease) both;
}
[class*="st-key-card"] { padding: 1.25rem 1.35rem; }
.tcg-card { padding: 1.2rem 1.3rem; }
.tcg-card:hover, [class*="st-key-card"]:hover { box-shadow: var(--shadow-md); border-color: #D3DBE8; }
[class*="st-key-cardhover"]:hover { transform: translateY(-2px); }
.tcg-card-title { font-family: var(--font-head); font-weight: 700; font-size: 1.02rem; color: var(--navy-800);
  display: flex; align-items: center; gap: .5rem; margin: 0 0 .2rem; }
.tcg-card-sub { color: var(--text-2); font-size: .85rem; margin: 0 0 .6rem; }

/* stat cards */
.tcg-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem; margin: .2rem 0 .3rem; }
.tcg-stat { position: relative; background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 1.1rem 1.2rem; box-shadow: var(--shadow-sm); overflow: hidden;
  transition: transform .25s var(--ease), box-shadow .25s var(--ease); animation: tcg-rise .5s var(--ease) both; }
.tcg-stat:hover { transform: translateY(-3px); box-shadow: var(--shadow-md); }
.tcg-stat:nth-child(2) { animation-delay: .05s; } .tcg-stat:nth-child(3) { animation-delay: .1s; }
.tcg-stat:nth-child(4) { animation-delay: .15s; } .tcg-stat:nth-child(5) { animation-delay: .2s; }
.tcg-stat-top { display: flex; align-items: center; justify-content: space-between; }
.tcg-stat-label { font-size: .8rem; font-weight: 600; color: var(--text-2); }
.tcg-stat-icon { width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center;
  background: var(--blue-50); color: var(--blue-600); }
.tcg-stat-icon svg { width: 18px; height: 18px; }
.tcg-stat-value { font-family: var(--font-head); font-size: 2rem; font-weight: 800; color: var(--navy-800);
  margin-top: .55rem; line-height: 1; font-variant-numeric: tabular-nums; }
.tcg-stat-foot { font-size: .78rem; color: var(--text-3); margin-top: .45rem; }
.tcg-stat::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--accent, var(--blue-600)); }

/* animated counter (CSS-only, no JS) */
@property --tcg-n { syntax: '<integer>'; initial-value: 0; inherits: false; }
.tcg-counter { --tcg-n: var(--to); counter-reset: tcgn var(--tcg-n); animation: tcg-count 1.2s var(--ease) both; }
.tcg-counter::after { content: counter(tcgn); }
@keyframes tcg-count { from { --tcg-n: 0; } }

/* ---------- badges ---------- */
.tcg-badge { display: inline-flex; align-items: center; gap: .35rem; font-size: .72rem; font-weight: 600;
  padding: .2rem .6rem; border-radius: 999px; white-space: nowrap; border: 1px solid transparent; line-height: 1.4; }
.tcg-badge::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.tcg-badge.high   { color: #B91C1C; background: var(--error-bg); border-color: #F8D4D4; }
.tcg-badge.medium { color: var(--warning); background: var(--warning-bg); border-color: #FBE3B7; }
.tcg-badge.low    { color: #15803D; background: var(--success-bg); border-color: #CDEBD7; }
.tcg-badge.positive { color: #1D4ED8; background: var(--blue-50); border-color: var(--blue-100); }
.tcg-badge.negative { color: #9A3412; background: #FFF1E8; border-color: #FCDCC6; }
.tcg-badge.edge-case { color: #0F766E; background: #E7F7F4; border-color: #C5EBE4; }
.tcg-badge.neutral { color: var(--text-2); background: #F1F4F9; border-color: var(--border); }
.tcg-badge.neutral::before, .tcg-badge.plain::before { display: none; }
.tcg-code { font-family: var(--font-mono); font-size: .78rem; font-weight: 500; color: var(--navy-700);
  background: #F1F4F9; border: 1px solid var(--border); padding: .15rem .5rem; border-radius: 6px; }

/* ---------- test case card ---------- */
.tc-head { display: flex; align-items: center; gap: .5rem; flex-wrap: wrap; }
.tc-title { font-family: var(--font-head); font-size: 1rem; font-weight: 700; color: var(--navy-800); margin: .6rem 0 .8rem; line-height: 1.4; }
.tc-grid { display: grid; grid-template-columns: 1.35fr 1fr; gap: 1rem 1.5rem; }
@media (max-width: 900px) { .tc-grid { grid-template-columns: 1fr; } }
.tc-label { font-size: .68rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--text-3); margin-bottom: .35rem; }
.tc-steps { margin: 0; padding: 0; list-style: none; counter-reset: s; }
.tc-steps li { counter-increment: s; position: relative; padding: .15rem 0 .35rem 2rem; font-size: .9rem; color: var(--text); line-height: 1.5; }
.tc-steps li::before { content: counter(s); position: absolute; left: 0; top: .2rem; width: 1.35rem; height: 1.35rem;
  border-radius: 50%; background: var(--blue-50); color: var(--blue-700); font-size: .7rem; font-weight: 700;
  display: grid; place-items: center; }
.tc-box { background: #F8FAFD; border: 1px solid var(--border-2); border-radius: var(--radius-sm); padding: .6rem .75rem;
  font-size: .88rem; color: var(--text); line-height: 1.5; margin-bottom: .75rem; word-break: break-word; }
.tc-box.data { font-family: var(--font-mono); font-size: .8rem; }
.tc-box.expected { background: #F2F9F4; border-color: #DDEFE3; }
.tc-assume { display: flex; gap: .5rem; align-items: flex-start; font-size: .82rem; color: #92400E; background: var(--warning-bg);
  border: 1px solid #FBE3B7; border-radius: var(--radius-sm); padding: .5rem .7rem; margin-top: .25rem; }

/* ---------- alerts ---------- */
.tcg-alert { display: flex; gap: .85rem; border-radius: var(--radius); padding: 1rem 1.15rem; border: 1px solid;
  animation: tcg-rise .35s var(--ease) both; }
.tcg-alert svg { flex: 0 0 auto; width: 20px; height: 20px; margin-top: 2px; }
.tcg-alert-title { font-weight: 700; font-size: .95rem; margin-bottom: .15rem; }
.tcg-alert-msg { font-size: .9rem; line-height: 1.5; }
.tcg-alert-hint { font-size: .84rem; margin-top: .4rem; opacity: .9; }
.tcg-alert.error { background: var(--error-bg); border-color: #F6CACA; color: #7F1D1D; }
.tcg-alert.warning { background: var(--warning-bg); border-color: #F8DDA8; color: #78350F; }
.tcg-alert.success { background: var(--success-bg); border-color: #C6E8D2; color: #14532D; }
.tcg-alert.info { background: var(--blue-50); border-color: var(--blue-100); color: #1E3A8A; }

/* ---------- lists / misc ---------- */
.tcg-list { margin: .2rem 0 0; padding-left: 1.1rem; }
.tcg-list li { font-size: .88rem; color: var(--text); margin-bottom: .3rem; line-height: 1.5; }
.tcg-muted { color: var(--text-2); font-size: .88rem; }
.tcg-kv { display: flex; flex-wrap: wrap; gap: .45rem; }
.tcg-divider { height: 1px; background: var(--border); margin: .8rem 0; }
.tcg-section { display: flex; align-items: baseline; justify-content: space-between; margin: .6rem 0 .1rem; }
.tcg-section h3 { font-size: 1.08rem; font-weight: 700; color: var(--navy-800); margin: 0; }
.tcg-section span { font-size: .82rem; color: var(--text-2); }
.tcg-req { font-size: .92rem; line-height: 1.6; color: var(--text); white-space: pre-wrap; background: #F8FAFD;
  border-left: 3px solid var(--blue-600); border-radius: 0 var(--radius-sm) var(--radius-sm) 0; padding: .75rem 1rem; }

/* pipeline */
.tcg-pipe { list-style: none; margin: .4rem 0 0; padding: 0; }
.tcg-pipe li { position: relative; padding: 0 0 1rem 2.4rem; }
.tcg-pipe li:last-child { padding-bottom: 0; }
.tcg-pipe li::before { content: attr(data-n); position: absolute; left: 0; top: 0; width: 1.7rem; height: 1.7rem;
  border-radius: 8px; background: var(--navy-800); color: #fff; font-size: .75rem; font-weight: 700; display: grid; place-items: center; }
.tcg-pipe li::after { content: ""; position: absolute; left: .82rem; top: 1.85rem; bottom: .2rem; width: 1px; background: var(--border); }
.tcg-pipe li:last-child::after { display: none; }
.tcg-pipe b { display: block; font-size: .9rem; color: var(--navy-800); }
.tcg-pipe span { display: block; font-size: .82rem; line-height: 1.45; color: var(--text-2); }

/* empty state */
.tcg-empty { text-align: center; padding: 2.6rem 1.5rem; border: 1.5px dashed #D5DDEA; border-radius: var(--radius-lg);
  background: linear-gradient(180deg, #FFFFFF 0%, #FAFBFE 100%); animation: tcg-rise .45s var(--ease) both; }
.tcg-empty-icon { width: 54px; height: 54px; margin: 0 auto .9rem; border-radius: 14px; display: grid; place-items: center;
  background: var(--blue-50); color: var(--blue-600); }
.tcg-empty-icon svg { width: 26px; height: 26px; }
.tcg-empty h4 { font-family: var(--font-head); font-size: 1.1rem; color: var(--navy-800); margin: 0 0 .35rem; }
.tcg-empty p { color: var(--text-2); font-size: .9rem; margin: 0 auto; max-width: 460px; }

/* AI loader */
.tcg-loader { display: flex; align-items: center; gap: 1rem; padding: 1rem 1.15rem; border-radius: var(--radius);
  background: linear-gradient(135deg, var(--navy-800), var(--navy-700)); color: #E6ECF7; box-shadow: var(--shadow-md);
  animation: tcg-rise .3s var(--ease) both; overflow: hidden; position: relative; }
.tcg-loader::after { content: ""; position: absolute; inset: 0; background: linear-gradient(100deg, transparent 20%, rgba(255,255,255,.07) 50%, transparent 80%);
  transform: translateX(-100%); animation: tcg-shimmer 1.8s infinite; }
@keyframes tcg-shimmer { to { transform: translateX(100%); } }
.tcg-orb { width: 38px; height: 38px; border-radius: 50%; flex: 0 0 auto; position: relative;
  background: conic-gradient(from 0deg, #5B8CF5, #93B4FB, #2563EB, #5B8CF5); animation: tcg-spin 1.4s linear infinite; }
.tcg-orb::after { content: ""; position: absolute; inset: 5px; border-radius: 50%; background: var(--navy-800); }
@keyframes tcg-spin { to { transform: rotate(360deg); } }
.tcg-loader b { color: #fff; font-size: .95rem; }
.tcg-loader small { display: block; color: #A9B8D3; font-size: .82rem; margin-top: .1rem; }
.tcg-dots span { display: inline-block; width: 5px; height: 5px; margin-left: 3px; border-radius: 50%; background: #93B4FB;
  animation: tcg-bounce 1.2s infinite ease-in-out; }
.tcg-dots span:nth-child(2) { animation-delay: .15s; } .tcg-dots span:nth-child(3) { animation-delay: .3s; }
@keyframes tcg-bounce { 0%, 80%, 100% { opacity: .25; transform: translateY(0); } 40% { opacity: 1; transform: translateY(-3px); } }

/* session list item */
.sess { display: flex; justify-content: space-between; gap: 1rem; align-items: flex-start; }
.sess-title { font-family: var(--font-head); font-weight: 700; font-size: 1rem; color: var(--navy-800); margin: 0 0 .25rem; }
.sess-req { font-size: .86rem; color: var(--text-2); line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2;
  -webkit-box-orient: vertical; overflow: hidden; margin-bottom: .55rem; }
.sess-meta { display: flex; flex-wrap: wrap; gap: .4rem; align-items: center; font-size: .78rem; color: var(--text-3); }
.sess-count { text-align: right; flex: 0 0 auto; }
.sess-count b { font-family: var(--font-head); font-size: 1.5rem; color: var(--navy-800); display: block; line-height: 1; }
.sess-count span { font-size: .72rem; color: var(--text-3); text-transform: uppercase; letter-spacing: .08em; }

/* ---------- Streamlit widget skins ---------- */
.stButton > button, .stDownloadButton > button, [data-testid="stPopover"] button {
  border-radius: 10px !important; font-weight: 600 !important; font-size: .88rem !important; min-height: 2.5rem;
  transition: transform .18s var(--ease), box-shadow .18s var(--ease), background-color .18s var(--ease), border-color .18s var(--ease) !important;
}
.stButton > button:hover, .stDownloadButton > button:hover { transform: translateY(-1px); }
.stButton > button:active, .stDownloadButton > button:active { transform: translateY(0); }
[data-testid="stBaseButton-primary"] {
  background: var(--blue-600) !important; border: 1px solid var(--blue-600) !important; color: #fff !important;
  box-shadow: 0 6px 16px -6px rgba(37,99,235,.55) !important;
}
[data-testid="stBaseButton-primary"]:hover { background: var(--blue-700) !important; border-color: var(--blue-700) !important;
  box-shadow: 0 10px 22px -8px rgba(37,99,235,.6) !important; }
[data-testid="stBaseButton-primary"] * { color: #fff !important; }
[data-testid="stBaseButton-secondary"] { background: #fff !important; border: 1px solid var(--border) !important; color: var(--navy-700) !important; box-shadow: var(--shadow-xs); }
[data-testid="stBaseButton-secondary"]:hover { border-color: var(--blue-600) !important; color: var(--blue-600) !important; background: #FBFCFF !important; }
[data-testid="stBaseButton-tertiary"] { color: var(--blue-600) !important; font-weight: 600 !important; }
[class*="st-key-danger"] button { color: var(--error) !important; }
[class*="st-key-danger"] button:hover { border-color: var(--error) !important; background: var(--error-bg) !important; }
[class*="st-key-dangerfill"] button { background: var(--error) !important; border-color: var(--error) !important; color: #fff !important;
  box-shadow: 0 6px 16px -6px rgba(220,38,38,.5) !important; }
[class*="st-key-dangerfill"] button * { color: #fff !important; }
[class*="st-key-dangerfill"] button:hover { background: #B91C1C !important; }

/* hero action buttons (on dark) */
[class*="st-key-hero-actions"] [data-testid="stBaseButton-secondary"] { background: rgba(255,255,255,.08) !important;
  color: #fff !important; border-color: rgba(255,255,255,.2) !important; }

.stTextArea textarea, .stTextInput input, .stNumberInput input {
  border-radius: 10px !important; font-size: .95rem !important; color: var(--text) !important; background: #fff !important;
}
.stTextArea textarea { line-height: 1.6 !important; }
[data-baseweb="textarea"], [data-baseweb="input"], [data-baseweb="select"] > div {
  border-radius: 10px !important; border-color: var(--border) !important; background: #fff !important;
  transition: border-color .2s var(--ease), box-shadow .2s var(--ease);
}
[data-baseweb="textarea"]:focus-within, [data-baseweb="input"]:focus-within, [data-baseweb="select"] > div:focus-within {
  border-color: var(--blue-600) !important; box-shadow: 0 0 0 3px rgba(37,99,235,.15) !important;
}
.stTextArea label p, .stTextInput label p, .stMultiSelect label p, .stSelectbox label p, [data-testid="stWidgetLabel"] p {
  font-weight: 600 !important; color: var(--navy-700) !important; font-size: .85rem !important;
}
[data-baseweb="tag"] { border-radius: 999px !important; background: var(--blue-50) !important; }
[data-baseweb="tag"] span { color: var(--blue-700) !important; font-weight: 600; }

[data-testid="stExpander"] details { border: 1px solid var(--border) !important; border-radius: var(--radius) !important;
  background: var(--card); box-shadow: var(--shadow-xs); }
[data-testid="stExpander"] summary { font-weight: 600; color: var(--navy-800); }
[data-testid="stExpander"] summary:hover { color: var(--blue-600); }

[data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; box-shadow: var(--shadow-xs); }

[data-testid="stToast"] { border-radius: 12px !important; background: var(--navy-800) !important; box-shadow: var(--shadow-md) !important; }
[data-testid="stToast"] * { color: #F1F5FB !important; }

div[role="dialog"] { border-radius: var(--radius-lg) !important; box-shadow: 0 30px 80px -20px rgba(14,24,48,.45) !important;
  animation: tcg-pop .25s var(--ease) both; }
@keyframes tcg-pop { from { opacity: 0; transform: translateY(12px) scale(.98); } to { opacity: 1; transform: none; } }

[data-testid="stProgress"] > div > div > div > div { background: linear-gradient(90deg, var(--blue-600), #5B8CF5) !important; }
[data-testid="stStatusWidget"] { display: none; }
[data-testid="stExpanderDetails"] { font-size: .9rem; }

[data-testid="stButtonGroup"] button { border-radius: 999px !important; font-weight: 600 !important; }
[data-testid="stBaseButton-pillsActive"], [data-testid="stBaseButton-segmented_controlActive"] {
  background: var(--blue-50) !important; border-color: var(--blue-600) !important; color: var(--blue-700) !important; }

/* example chips */
[class*="st-key-examples"] button { border-radius: 999px !important; font-size: .8rem !important; min-height: 2rem !important;
  padding: .2rem .8rem !important; font-weight: 500 !important; background: #F4F7FC !important; }

/* plotly */
.js-plotly-plot .plotly .modebar { display: none !important; }

/* responsive */
@media (max-width: 760px) {
  [data-testid="stMainBlockContainer"], .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }
  .tcg-hero { padding: 1.5rem 1.3rem; } .tcg-hero h1 { font-size: 1.5rem; }
  .tcg-title { font-size: 1.45rem; } .tcg-header { flex-direction: column; align-items: flex-start; }
  .sess { flex-direction: column; } .sess-count { text-align: left; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; }
}
""".replace("__FONTS__", FONTS)


def inject_css() -> None:
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)
