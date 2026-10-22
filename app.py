"""Adaptive Hybrid Disk Scheduling — launch with streamlit run app.py."""
from dataclasses import asdict
from html import escape
import json
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from src.models import DiskConfig, AHDSConfig
from src.workloads import WorkloadConfig, PRESETS, generate, to_frame, from_frame, read_csv, trace_bundle
from src.policies import ALGORITHMS, ABLATIONS
from src.simulator import simulate
import src.plots as plots
import src.ui as ui
from experiments.run import run as run_experiments

ROOT = Path(__file__).resolve().parent
PAGES = ['Overview', 'Workload Builder', 'Simulation', 'Compare Algorithms', 'Experiments', 'How It Works']
st.set_page_config(page_title='AHDS · Disk Scheduling Lab', page_icon='◎', layout='wide')
st.markdown(ui.STYLE, unsafe_allow_html=True)

if 'trace' not in st.session_state:
    c = WorkloadConfig()
    st.session_state.trace = generate(c)
    st.session_state.trace_metadata = {'source': 'generator', 'workload': asdict(c), 'generation_disk': asdict(DiskConfig())}
    st.session_state.trace_revision = 0
    st.session_state.playback_position = 0


def navigate(page):
    st.session_state.nav_page = page


def invalidate_runs():
    for key in ('result', 'comparison'):
        st.session_state.pop(key, None)
    st.session_state.playback_position = 0
    st.session_state.pop('step', None)


def save_trace(trace, metadata):
    if not trace: raise ValueError('Add at least one request before freezing a trace.')
    st.session_state.trace = trace
    st.session_state.trace_metadata = metadata
    st.session_state.trace_revision += 1
    invalidate_runs()
    st.rerun()


def move_playback(position):
    # Permanent position survives Streamlit cleaning up widgets on page changes.
    st.session_state.playback_position = position
    st.session_state.step = position


def slider_changed():
    st.session_state.playback_position = st.session_state.step


def show_plot(fig):
    st.pyplot(fig, width='stretch')
    plt.close(fig)


def current_trace():
    return from_frame(to_frame(st.session_state.trace), disk)


with st.sidebar:
    st.markdown('<div class="brand"><div class="brand-symbol">◎</div><div><strong>AHDS</strong><small>DISK SCHEDULING LAB</small></div></div>', unsafe_allow_html=True)
    page = st.radio('Explore the lab', PAGES, key='nav_page', label_visibility='collapsed')
    st.divider()
    trace = st.session_state.trace
    mm_count = sum(r.kind == 'multimedia' for r in trace)
    st.markdown(f'<div class="eyebrow">Active workload</div><div class="summary-line">{len(trace):,} requests · {mm_count} multimedia<br>{len(trace)-mm_count} database · trace #{st.session_state.trace_revision+1:02d}</div>', unsafe_allow_html=True)
    with st.expander('Disk configuration'):
        tracks = st.number_input('Track count', 2, 100000, 200, key='disk_tracks')
        if st.session_state.get('disk_head', 0) >= tracks:
            st.session_state.disk_head = tracks-1
        head = st.number_input('Initial head', 0, tracks-1, min(50, tracks-1), key='disk_head')
        direction = st.selectbox('LOOK / C-LOOK direction', ['Increasing', 'Decreasing'])
        overhead = st.number_input('Positioning overhead (ms)', .001, 1000., 1.)
        seek = st.number_input('Seek cost (ms / track)', .0001, 100., .1, format='%.4f')
        rate = st.number_input('Transfer rate (KiB / ms)', .001, 100000., 64.)
    with st.expander('AHDS parameters'):
        batch = st.number_input('Batch size B', 2, 100, 5)
        urgency = st.number_input('Urgency horizon U (ms)', 0., 10000., 10.)
        aging = st.number_input('Database threshold W (ms)', .001, 10000., 50.)
        pressure = st.slider('Pressure threshold', 0., 1., .6, .01)
    st.caption('Synthetic HDD model · deterministic rules\n\nNo physical disk access. Quotas count requests, not bandwidth.')

disk = DiskConfig(tracks, head, 1 if direction == 'Increasing' else -1, overhead, seek, rate)
ahds = AHDSConfig(batch, urgency, aging, pressure)
context = json.dumps({'disk': asdict(disk), 'ahds': asdict(ahds), 'trace': st.session_state.trace_revision}, sort_keys=True)
if st.session_state.get('context') != context:
    invalidate_runs()
    st.session_state.context = context

metadata = st.session_state.trace_metadata
source_name = metadata.get('workload', {}).get('preset', metadata.get('source', 'Custom trace'))
seed = metadata.get('workload', {}).get('seed')
st.caption(f'OPERATING SYSTEMS  /  {page.upper()}')
TITLES = {'Overview': ('Disk scheduling, in focus.', 'Adaptive Hybrid Disk Scheduling for Mixed Multimedia and Database Workloads'),
          'Workload Builder': ('Shape your workload.', 'Generate, import, or edit a trace. Freeze it once, then compare fairly.'),
          'Simulation': ('Inside every dispatch.', 'Follow the head, inspect each decision, and replay a completed simulation.'),
          'Compare Algorithms': ('Explore the trade-offs.', 'Identical requests. Identical disk. Seven different scheduling decisions.'),
          'Experiments': ('Test beyond a single trace.', 'Paired evaluation seeds across scenarios and loads. Keep the raw evidence.'),
          'How It Works': ('The rules behind the results.', 'Algorithm specifications, metric definitions, and model assumptions.')}
st.title(TITLES[page][0])
st.markdown(f'<p class="section-note">{TITLES[page][1]}</p>', unsafe_allow_html=True)

if page == 'Overview':
    st.markdown('''<div class="hero"><div class="hero-orbit"></div><div class="hero-body"><span class="hero-badge">DETERMINISTIC HDD SIMULATOR</span><h2>One disk.<br>Two competing priorities.</h2><p>Meet multimedia deadlines while keeping database requests moving. Explore how an adaptive controller balances both, one dispatch at a time.</p></div></div>''', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric('Requests in frozen trace', f'{len(trace):,}')
    c2.metric('Multimedia / database', f'{mm_count} / {len(trace)-mm_count}')
    c3.metric('Disk tracks', f'{disk.tracks:,}')
    c4.metric('Trace duration', f'{max(r.arrival for r in trace)-min(r.arrival for r in trace):,.1f} ms')
    st.write('')
    left,right = st.columns([1.45,1], gap='large')
    with left, st.container(border=True):
        st.subheader('Your active workload')
        st.caption(f'{source_name}' + (f' · seed {seed}' if seed is not None else '') + ' · arrival times from the frozen trace')
        ui.legend()
        show_plot(plots.arrival_plot(trace))
        st.button('Edit workload →', on_click=navigate, args=('Workload Builder',), width='stretch')
    with right, st.container(border=True):
        st.subheader('Three modes. One controller.')
        st.caption('Evaluated in this order at each batch boundary.')
        ui.mode_cards(ahds)
        st.caption('M = multimedia · D = database. Empty preferred queues borrow the other class; every dispatch consumes a slot.')
    st.write('')
    a,b,c = st.columns(3)
    for col, number, title, description, target in [
        (a,'01','Build a trace','Choose a scenario, load and seed.','Workload Builder'),
        (b,'02','Replay decisions','See why each request was selected.','Simulation'),
        (c,'03','Compare the outcome','Measure deadlines, waiting and seek cost.','Compare Algorithms')]:
        with col, st.container(border=True):
            st.caption(number + ' / EXPLORE')
            st.subheader(title)
            st.caption(description)
            st.button('Open '+target+' →', on_click=navigate, args=(target,), width='stretch')
    with st.expander('Project scope & research context'):
        st.write('Multimedia requests have soft playback deadlines; database requests represent independent page I/O without deadlines. AHDS combines feasible multimedia EDF, persistent database LOOK, aging, and adaptive request quotas. Fixed Hybrid and experiment-only ablations isolate individual mechanisms.')
        st.write('This is an HDD simulation. It does not run a real database or emulate video playback. It offers no hard deadline or fixed maximum waiting-time guarantee.')
        st.markdown('APEX is the conceptual base paper, not an implemented baseline. [Base paper DOI](https://doi.org/10.1007/s00530-005-0189-0). No world-first academic novelty is claimed.')

elif page == 'Workload Builder':
    generator,manual,imports = st.tabs(['Generate a trace', 'Edit requests', 'Import CSV'])
    with generator, st.container(border=True):
        st.subheader('Seeded workload generator')
        with st.form('generator'):
            a,b,c = st.columns([2,1,1])
            preset = a.selectbox('Scenario', PRESETS)
            seed_input = b.number_input('Random seed', 0, 2**31-1, 42)
            count = c.number_input('Request count', 1, 10000, 100)
            a,b,c = st.columns(3)
            intensity = a.number_input('Arrivals per ms', .001, 10., .12, format='%.3f')
            distribution = b.selectbox('Track distribution', ['locality', 'uniform'])
            phase = c.number_input('Phase boundary / burst period (ms)', 1., 100000., 100.)
            a,b = st.columns(2)
            size_profile = a.selectbox('Size profile', ['64 / 64 KiB', '256 / 16 KiB', 'Custom'])
            deadline_profile = b.selectbox('Relative deadlines', ['Default 20–80 ms', 'Tight 5–20 ms', 'Relaxed 80–200 ms', 'Custom'])
            with st.expander('Custom sizes, deadlines & stream locality'):
                a,b = st.columns(2)
                mm_size = a.number_input('Custom multimedia size (KiB)', 1., 100000., 64.)
                db_size = b.number_input('Custom database size (KiB)', 1., 100000., 64.)
                low = a.number_input('Custom minimum deadline (ms)', .001, 100000., 20.)
                high = b.number_input('Custom maximum deadline (ms)', .001, 100000., 80.)
                streams = a.number_input('Multimedia streams', 1, 1000, 4)
                step_size = b.number_input('Stream track step', 1, 100000, 3)
                st.caption('Custom sizes and deadlines apply only when the corresponding profile is Custom.')
            submitted = st.form_submit_button('Generate and freeze trace', type='primary', width='stretch')
        if submitted:
            try:
                sizes = {'64 / 64 KiB':(64,64),'256 / 16 KiB':(256,16),'Custom':(mm_size,db_size)}[size_profile]
                deadlines = {'Default 20–80 ms':(20,80),'Tight 5–20 ms':(5,20),'Relaxed 80–200 ms':(80,200),'Custom':(low,high)}[deadline_profile]
                wc = WorkloadConfig(preset,seed_input,count,intensity,distribution,*sizes,*deadlines,streams,step_size,phase)
                save_trace(generate(wc,disk), {'source':'generator','workload':asdict(wc),'generation_disk':asdict(disk)})
            except ValueError as exc: st.error(str(exc))
        st.caption('Transitions use simulated time. Bursts alternate by period. Stream tracks wrap modulo disk size, which can cause long seeks. Overload uses 3× the configured arrival rate.')
    with manual:
        st.caption('Changes take effect only after validation. Database deadlines must be blank.')
        edited = st.data_editor(to_frame(trace), num_rows='dynamic', hide_index=True, key=f'editor_{st.session_state.trace_revision}', width='stretch',
            column_config={'kind':st.column_config.SelectboxColumn('Class', options=['multimedia','database'],required=True),
                           'id':'Request ID','arrival':'Arrival (ms)','track':'Track','size':'Size (KiB)','deadline':'Deadline (ms)'})
        if st.button('Validate and freeze edited table', type='primary'):
            try:
                save_trace(from_frame(edited,disk), {'source':'manual editor','parent':metadata})
            except ValueError as exc: st.error(str(exc))
    with imports, st.container(border=True):
        st.subheader('Bring your own requests')
        uploaded = st.file_uploader('Import request CSV', type=['csv'])
        st.code('id,kind,arrival,track,size,deadline\nM1,multimedia,0,80,64,30\nD1,database,0,60,64,', language='csv')
        if uploaded is not None and st.button('Validate and freeze imported CSV',type='primary'):
            try: save_trace(read_csv(uploaded,disk), {'source':'CSV import','filename':uploaded.name})
            except ValueError as exc: st.error(str(exc))
        st.download_button('Download sample CSV', (ROOT/'data/sample.csv').read_bytes(), 'sample.csv','text/csv')
    st.write('')
    with st.container(border=True):
        a,b = st.columns([3,2])
        a.subheader('Frozen trace')
        a.caption(f'{source_name} · {len(trace):,} requests · all comparisons use these exact rows')
        export_metadata = metadata | {'disk':asdict(disk),'ahds':asdict(ahds)}
        b.download_button('Trace + configuration ↓', trace_bundle(trace,export_metadata), 'trace_bundle.zip','application/zip',width='stretch')
        ui.request_table(to_frame(trace))
        a,b = st.columns(2)
        a.download_button('Download trace CSV',to_frame(trace).to_csv(index=False),'trace.csv','text/csv')
        b.button('Continue to simulation →',on_click=navigate,args=('Simulation',),type='primary',width='stretch')
        with st.expander('Trace provenance & complete configuration'): st.json(export_metadata)

elif page == 'Simulation':
    with st.container(border=True):
        a,b,c = st.columns([3,1,1])
        algorithm = a.selectbox('Scheduling algorithm',ALGORITHMS,index=6,label_visibility='collapsed')
        if b.button('Run simulation',type='primary',width='stretch'):
            try:
                st.session_state.result = simulate(current_trace(),algorithm,disk,ahds)
                move_playback(len(st.session_state.result.dispatches))
            except ValueError as exc: st.error(str(exc))
        c.button('Reset playback',on_click=move_playback,args=(0,),width='stretch')
    result = st.session_state.get('result')
    if result is None:
        ui.empty('Ready when you are.','Choose a policy and run the frozen trace to inspect its dispatch decisions.')
    else:
        st.caption(f'SAVED RUN / {result.algorithm} · {len(result.dispatches)} requests · full-run metrics below')
        if algorithm != result.algorithm: st.info(f'You are viewing {result.algorithm}. Run simulation to apply {algorithm}.')
        ui.result_metrics(result)
        st.write('')
        n = len(result.dispatches)
        shown = min(n,st.session_state.playback_position)
        with st.container(border=True):
            st.subheader('Dispatch playback')
            a,b,c = st.columns(3)
            a.button('← Previous dispatch',on_click=move_playback,args=(max(0,shown-1),),disabled=shown==0,width='stretch')
            b.button('Next dispatch →',on_click=move_playback,args=(min(n,shown+1),),disabled=shown==n,width='stretch')
            c.button('Show complete run',on_click=move_playback,args=(n,),width='stretch')
            if 'step' not in st.session_state: st.session_state.step = shown
            st.slider('Completed dispatches',0,n,key='step',on_change=slider_changed)
            shown = st.session_state.playback_position
            if shown:
                last = result.dispatches.iloc[shown-1]
                mode = last['batch_mode'] or result.algorithm
                st.markdown(f'<div class="decision"><strong>{escape(str(last["id"]))} · {escape(str(mode).replace("-"," ").title())}</strong><p>{escape(last["reason"])}</p></div>',unsafe_allow_html=True)
                ui.request_table(result.dispatches.iloc[[shown-1]],['id','start','completion','preferred_class','actual_class','slack','database_age'])
            else: st.caption('At the initial head position. Advance one dispatch to start playback.')
            head_tab,timeline_tab,queue_tab,mode_tab = st.tabs(['Head movement','Service timeline','Queue lengths','Controller modes'])
            with head_tab: show_plot(plots.head_plot(result,shown))
            with timeline_tab:
                ui.legend()
                show_plot(plots.timeline(result,shown))
            with queue_tab:
                st.caption('Complete run · queued requests exclude the request in service.')
                show_plot(plots.queue_plot(result))
            with mode_tab:
                st.caption('Complete run · controller decisions at batch boundaries.')
                show_plot(plots.mode_plot(result))
        with st.expander(f'Dispatch table · {shown} of {n} completions'):
            ui.request_table(result.dispatches.iloc[:shown])
            st.download_button('Download full dispatch log',result.dispatches.to_csv(index=False),'dispatches.csv','text/csv')
        with st.expander('All metrics & controller decisions'):
            values = result.metrics()
            st.dataframe(pd.DataFrame({'Metric':[ui.metric_label(k) for k in values],'Value':[ui.fmt(v) for v in values.values()]}),hide_index=True,width='stretch')
            st.dataframe(result.controller,hide_index=True,width='stretch')

elif page == 'Compare Algorithms':
    with st.container(border=True):
        selected = st.multiselect('Policies to compare',ALGORITHMS,default=ALGORITHMS)
        if st.button('Run comparison',type='primary'):
            try:
                frozen = current_trace()
                if not selected: raise ValueError('Choose at least one algorithm.')
                results = [simulate(frozen,name,disk,ahds) for name in selected]
                st.session_state.comparison = pd.DataFrame({r.algorithm:r.metrics() for r in results}).T.rename_axis('algorithm')
            except ValueError as exc: st.error(str(exc))
    frame = st.session_state.get('comparison')
    if frame is None:
        ui.empty('A fair comparison starts here.','Run your selected policies on the exact same frozen trace.')
    else:
        st.caption('SAVED COMPARISON / '+ ' · '.join(frame.index))
        overview,charts,details = st.tabs(['Key results','Comparison charts','All metrics & export'])
        with overview:
            keys = ['total_head_movement','overall_mean_waiting_ms','multimedia_deadline_miss_ratio','database_p95_response_ms']
            readable = frame[keys].apply(pd.to_numeric,errors='coerce').rename(columns=ui.METRIC_LABELS)
            st.dataframe(readable.style.format({ui.metric_label(k):'{:.1%}' if 'ratio' in k else '{:,.1f}' for k in keys},na_rep='N/A'),width='stretch')
            a,b = st.columns(2)
            with a,st.container(border=True):
                show_plot(plots.comparison(frame,['multimedia_deadline_miss_ratio'],'Multimedia deadline misses','Fraction of multimedia requests'))
            with b,st.container(border=True):
                show_plot(plots.comparison(frame,['database_p95_response_ms'],'Database p95 response','ms'))
            st.caption('Lower values are better for these metrics, but seek efficiency and class delays can trade off. No policy is universally best. N/A means the workload contains no requests of that class.')
        with charts:
            with st.container(border=True): show_plot(plots.comparison(frame,['overall_mean_waiting_ms','overall_mean_response_ms'],'Waiting & response time','ms'))
            with st.container(border=True): show_plot(plots.comparison(frame,['total_head_movement'],'Total physical head movement','Tracks'))
        with details:
            st.dataframe(frame.T.rename(index=ui.metric_label).style.format('{:,.3f}',na_rep='N/A'),width='stretch')
            st.download_button('Download comparison CSV',frame.to_csv(),'comparison.csv','text/csv')
        st.caption('Global EDF assigns database requests infinite deadlines; strict multimedia priority may delay database I/O.')

elif page == 'Experiments':
    with st.container(border=True),st.form('experiments'):
        scenarios = st.multiselect('Scenarios',PRESETS,default=['Balanced'])
        algorithms = st.multiselect('Policies and experiment-only ablations',ALGORITHMS+ABLATIONS,default=['Fixed Hybrid','AHDS'])
        a,b,c = st.columns(3)
        seed_count = a.number_input('Evaluation seed count',1,20,3)
        start_seed = b.number_input('First evaluation seed (0–9 reserved for development)',10,1000000,1000)
        requests = c.number_input('Requests per trace',10,1000,100)
        loads_text = st.text_input('Arrival intensities (comma-separated)','0.08, 0.16')
        st.caption('Each seed generates one frozen trace per scenario and load, shared across policies. UI runs omit confidence intervals; use the CLI for full research runs and sensitivity grids.')
        run = st.form_submit_button('Run paired experiments',type='primary')
    if run:
        progress = st.progress(0.,text='Running finite trace simulations…')
        try:
            cfg = dict(scenarios=scenarios,algorithms=algorithms,seeds=list(range(start_seed,start_seed+seed_count)),
                loads=[float(x.strip()) for x in loads_text.split(',')],workload={'count':requests},disk=asdict(disk),
                sensitivity={k:[v] for k,v in asdict(ahds).items()},bootstrap_resamples=0)
            st.session_state.experiment = run_experiments(cfg,lambda fraction:progress.progress(fraction,text=f'{fraction:.0%} complete'))
        except (ValueError,TypeError) as exc: st.error(str(exc))
    if 'experiment' not in st.session_state:
        ui.empty('Look for patterns across traces.','Start a small paired experiment, then inspect the results by scenario and load.')
    else:
        raw,summary,paired,cfg = st.session_state.experiment
        st.caption(f'SAVED EXPERIMENT / {len(raw)} trace-level runs · seeds {min(cfg["seeds"])}–{max(cfg["seeds"])} · settings recorded below')
        result_tab,export_tab = st.tabs(['Results by scenario & load','Configuration & downloads'])
        with result_tab:
            view = summary[['scenario','load','algorithm','overall_mean_waiting_ms','multimedia_deadline_miss_ratio','database_p95_response_ms']].copy()
            st.dataframe(view.rename(columns=ui.METRIC_LABELS).style.format({ui.metric_label('overall_mean_waiting_ms'):'{:,.1f}',ui.metric_label('multimedia_deadline_miss_ratio'):'{:.1%}',ui.metric_label('database_p95_response_ms'):'{:,.1f}','load':'{:.3f}'},na_rep='N/A'),hide_index=True,width='stretch')
            st.caption('Summary values average per-trace metrics, including per-trace p95 values; they are not pooled request percentiles.')
        with export_tab:
            a,b,c = st.columns(3)
            a.download_button('Raw trace-level CSV',raw.to_csv(index=False),'experiment_raw.csv','text/csv',width='stretch')
            b.download_button('Summary CSV',summary.to_csv(index=False),'experiment_summary.csv','text/csv',width='stretch')
            c.download_button('Experiment configuration',json.dumps(cfg,indent=2),'experiment_config.json','application/json',width='stretch')
            st.json(cfg,expanded=False)
else:
    algorithms_tab,metrics_tab,limits_tab = st.tabs(['Scheduling rules','Metric definitions','Assumptions & limitations'])
    with algorithms_tab: st.markdown((ROOT/'docs/ALGORITHMS.md').read_text())
    with metrics_tab: st.markdown((ROOT/'docs/METRICS.md').read_text())
    with limits_tab: st.markdown((ROOT/'docs/LIMITATIONS.md').read_text())
