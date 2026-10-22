"""Small presentation helpers; calculations remain in the simulation modules."""
from html import escape
import math
import pandas as pd
import streamlit as st

STYLE = '''<style>
.block-container {padding:2.4rem 2.8rem 3rem;max-width:1440px;}
[data-testid="stHeader"] {background:transparent;}
h1 {font-size:2.2rem!important;letter-spacing:-.07rem;font-weight:750!important;}
h2 {font-size:1.4rem!important;letter-spacing:-.025rem;}
h3 {font-size:1.12rem!important;}
[data-testid="stCaptionContainer"] {color:#718096;font-size:.8rem;}
[data-testid="stSidebar"] {border-right:1px solid #26364e;}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {gap:.8rem;}
[data-testid="stSidebar"] [data-testid="stRadio"] label {padding:.25rem .15rem;}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {background:#2b3b59;border-radius:7px;}
[data-testid="stSidebar"] [data-testid="stRadio"] p {font-size:.9rem;}
[data-testid="stSidebar"] [data-testid="stExpander"] {border-color:#34445b;}
[data-testid="stMetric"] {background:#fff;border:1px solid #e4e8f0;border-radius:12px;padding:1.05rem 1.2rem;}
[data-testid="stMetricLabel"] p {font-size:.77rem!important;color:#69778e;}
[data-testid="stMetricValue"] {font-size:1.7rem;font-weight:650;letter-spacing:-.04rem;}
[data-testid="stVerticalBlockBorderWrapper"]>div {border-radius:12px!important;}
[data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"]>div {background:#fff;}
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {border-radius:9px;overflow:hidden;}
.stButton>button, .stDownloadButton>button {border-radius:8px;font-weight:550;min-height:2.65rem;}
.stButton>button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] {box-shadow:0 3px 8px #5265db20;}
[data-testid="stForm"] {border:0;padding:0;}
[data-baseweb="tab-list"] {gap:1.4rem;}
[data-testid="stAlert"] {border-radius:10px;}
.brand {display:flex;align-items:center;gap:12px;padding:.25rem 0 1.25rem;color:white;}
.brand-symbol {height:39px;width:39px;background:#6878ed;border-radius:12px;display:grid;place-items:center;font-size:25px;}
.brand strong {font-size:1.25rem;letter-spacing:.08em;}.brand small{display:block;color:#9cacc5;font-size:.72rem;margin-top:2px;}
.eyebrow {font-size:.69rem;font-weight:700;letter-spacing:.16em;color:#79869a;text-transform:uppercase;margin-bottom:.55rem;}
.hero {background:#192a45;border-radius:16px;padding:2.2rem 2.5rem;color:white;margin:.6rem 0 1.35rem;position:relative;overflow:hidden;}
.hero h2 {font-size:2.65rem!important;line-height:1.13;letter-spacing:-.09rem;color:#fff!important;margin:.8rem 0 1rem;max-width:620px;}
.hero p {color:#becbe0;max-width:620px;line-height:1.7;margin-bottom:.2rem;}
.hero .eyebrow {color:#b5c2ff;}.hero-badge{font-size:.7rem;border:1px solid #526580;border-radius:100px;padding:.3rem .7rem;display:inline-block;color:#d8e2f3;}
.hero-orbit {position:absolute;width:290px;height:290px;border:1px solid #526580;border-radius:50%;right:-15px;top:-25px;opacity:.5;}
.hero-orbit:before,.hero-orbit:after{content:'';position:absolute;border:1px solid #526580;border-radius:50%;inset:35px;}
.hero-orbit:after{inset:75px;}.hero-body {position:relative;z-index:1;}
.class-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:7px;}.mm{background:#6377df;}.db{background:#20a38b;}
.legend {font-size:.76rem;color:#6b7890;margin:0 0 .7rem;display:flex;gap:22px;}
.summary-line{font-size:.82rem;line-height:1.85;color:#9db0cb;padding:1rem 0;border-top:1px solid #34445b;}
.section-note {font-size:.83rem;line-height:1.6;color:#718096;}
.mode-row{padding:.85rem 0;border-bottom:1px solid #edf0f5;display:flex;align-items:center;justify-content:space-between;gap:8px;}
.mode-row:last-child{border:0;}.mode-row b{font-size:.85rem;}.mode-row small{display:block;color:#7b879b;margin-top:4px;}
.slots{display:flex;gap:4px;}.slot{width:23px;height:26px;border-radius:5px;text-align:center;padding-top:3px;font:11px monospace;color:white;}
.slot.m{background:#6377df;}.slot.d{background:#20a38b;}
.decision {border-left:3px solid #6377df;background:#f1f3fc;padding:.9rem 1.1rem;border-radius:0 8px 8px 0;margin:.5rem 0 1rem;}
.decision strong{font-size:.9rem;}.decision p{font-size:.83rem;color:#586780;margin:.3rem 0 0;line-height:1.6;}
.empty-state {padding:2.5rem 1.5rem;text-align:center;border:1px dashed #ced6e5;border-radius:12px;margin:1rem 0;background:#fafbfe;}
.empty-state strong{display:block;font-size:1.05rem;margin:.6rem 0;color:#34455f;}.empty-state p{font-size:.87rem;color:#7b879b;}
@media(max-width:850px){.block-container{padding:1.5rem 1rem;}.hero{padding:1.6rem;}.hero h2{font-size:2rem!important;}.hero-orbit{opacity:.15;}}
</style>'''

METRIC_LABELS = {
    'total_head_movement': 'Head movement (tracks)', 'makespan_ms': 'Makespan (ms)',
    'overall_mean_waiting_ms': 'Mean waiting (ms)', 'overall_mean_response_ms': 'Mean response (ms)',
    'multimedia_deadline_miss_ratio': 'Multimedia miss ratio',
    'database_p95_response_ms': 'Database p95 response (ms)',
    'database_max_waiting_ms': 'Database max waiting (ms)',
    'database_waiting_threshold_violation_ratio': 'Database wait > W',
}
REQUEST_COLUMNS = {
    'id': 'Request', 'kind': 'Class', 'arrival': 'Arrival (ms)', 'track': 'Track',
    'size': 'Size (KiB)', 'deadline': 'Deadline (ms)', 'start': 'Start (ms)',
    'completion': 'Completion (ms)', 'waiting': 'Waiting (ms)', 'response': 'Response (ms)',
    'batch_mode': 'Batch mode', 'preferred_class': 'Preferred class', 'actual_class': 'Actual class',
    'slack': 'Slack (ms)', 'database_age': 'Database age (ms)',
}

def fmt(value, unit='', percent=False):
    if value is None or pd.isna(value): return 'N/A'
    return f'{value:.1%}' if percent else f'{value:,.1f}{unit}'

def metric_label(name):
    return METRIC_LABELS.get(name, name.replace('_', ' ').capitalize())

def empty(title, description):
    st.markdown(f'<div class="empty-state"><span style="color:#6377df;font-size:1.7rem">◎</span><strong>{escape(title)}</strong><p>{escape(description)}</p></div>', unsafe_allow_html=True)

def legend():
    st.markdown('<div class="legend"><span><i class="class-dot mm"></i>Multimedia</span><span><i class="class-dot db"></i>Database</span></div>', unsafe_allow_html=True)

def result_metrics(result):
    values = result.metrics()
    labels = [('total_head_movement','Head movement',' tracks',False),
              ('overall_mean_waiting_ms','Mean waiting',' ms',False),
              ('multimedia_deadline_miss_ratio','Multimedia deadline misses','',True),
              ('database_p95_response_ms','Database p95 response',' ms',False)]
    for column, (key,label,unit,percent) in zip(st.columns(4), labels):
        column.metric(label, fmt(values.get(key), unit, percent))

def request_table(frame, columns=None):
    frame = frame if columns is None else frame[columns]
    st.dataframe(frame.rename(columns=REQUEST_COLUMNS), hide_index=True, width='stretch',
                 column_config={name:st.column_config.NumberColumn(format='%.2f') for name in REQUEST_COLUMNS.values() if '(ms)' in name})

def mode_cards(config):
    b = config.batch_size
    rows = [('Database protection',f'Oldest database age ≥ {config.aging:g} ms',.4),
            ('Multimedia pressure',f'Otherwise, urgent feasible share ≥ {config.pressure:.0%}',.8),
            ('Balanced','Otherwise, share the dispatch slots',.6)]
    html = ''
    for title, detail, fraction in rows:
        q = max(1,min(b-1,math.floor(fraction*b+.5)))
        # Show counts at large B rather than overflowing the card.
        slots = ''.join(f'<span class="slot {kind.lower()}">{kind}</span>' for kind in ['M']*q+['D']*(b-q)) if b <= 8 else f'{q} M / {b-q} D'
        html += f'<div class="mode-row"><div><b>{title}</b><small>{detail}</small></div><div class="slots">{slots}</div></div>'
    st.markdown(html, unsafe_allow_html=True)
