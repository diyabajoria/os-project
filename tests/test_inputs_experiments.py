from dataclasses import asdict
import io
import json
import zipfile
import pandas as pd
import pytest
from src.models import DiskConfig, AHDSConfig, validate_requests, Request, DB
from src.workloads import WorkloadConfig, PRESETS, generate, read_csv, to_frame, trace_bundle
from experiments.run import run, export, paired_intervals

@pytest.mark.parametrize('preset',PRESETS)
def test_seed_and_csv_roundtrip(preset):
    c = WorkloadConfig(preset=preset)
    trace = generate(c)
    assert trace == generate(c)
    restored = read_csv(io.StringIO(to_frame(trace).to_csv(index=False)))
    pd.testing.assert_frame_equal(to_frame(trace),to_frame(restored),check_exact=False)
    with zipfile.ZipFile(io.BytesIO(trace_bundle(trace,{'workload':asdict(c)}))) as z:
        assert len(read_csv(io.BytesIO(z.read('trace.csv')))) == c.count
        assert json.loads(z.read('configuration.json'))['workload']['seed'] == c.seed

@pytest.mark.parametrize('factory,kwargs',[
    (DiskConfig,{'rate':0}),(DiskConfig,{'initial_head':200}),(DiskConfig,{'seek':float('nan')}),
    (AHDSConfig,{'batch_size':1}),(AHDSConfig,{'aging':0}),(AHDSConfig,{'pressure':1.1}),
    (WorkloadConfig,{'count':0}),(WorkloadConfig,{'deadline_min':90,'deadline_max':20}),
    (WorkloadConfig,{'intensity':-1}),(WorkloadConfig,{'streams':0})])
def test_invalid_config(factory,kwargs):
    with pytest.raises(ValueError): factory(**kwargs)

@pytest.mark.parametrize('csv',[
    '', 'id,kind\na,database',
    'id,kind,arrival,track,size,deadline\na,multimedia,0,20,64,',
    'id,kind,arrival,track,size,deadline\na,database,-1,20,64,',
    'id,kind,arrival,track,size,deadline\na,database,0,200,64,',
    'id,kind,arrival,track,size,deadline\na,database,0,20.5,64,',
    'id,kind,arrival,track,size,deadline\na,database,0,20,0,',
    'id,kind,arrival,track,size,deadline\na,multimedia,10,20,64,5',
    'id,kind,arrival,track,size,deadline\na,database,0,20,64,\na,database,0,20,64,',
    'id,kind,arrival,track,size,deadline\na,database,inf,20,64,'])
def test_invalid_csv(csv):
    with pytest.raises(ValueError): read_csv(io.StringIO(csv))

def test_small_experiment_export_and_pairing(tmp_path):
    cfg = dict(scenarios=['Balanced'],loads=[.1],seeds=[1000,1001],algorithms=['FCFS','AHDS'],workload={'count':10},bootstrap_resamples=20)
    raw,summary,paired,resolved = run(cfg)
    assert len(raw) == 4 and len(summary) == 2
    assert paired.pairs.eq(2).all()
    export(tmp_path,raw,summary,paired,resolved)
    assert len(pd.read_csv(tmp_path/'raw.csv')) == 4
    payload = json.loads((tmp_path/'results.json').read_text())
    assert payload['configuration']['seeds'] == cfg['seeds']
    with pytest.raises(ValueError): run(cfg | {'seeds':[0]})

def test_paired_bootstrap_uses_seed_pairs():
    raw = pd.DataFrame([dict(scenario='S',load=.1,parameters='{}',seed=seed,algorithm=algorithm,
                             multimedia_deadline_miss_ratio=value,database_p95_response_ms=value,
                             overall_mean_waiting_ms=value,total_head_movement=value)
                        for seed,base in [(1,10),(2,100)] for algorithm,value in [('AHDS',base),('FCFS',base+3)]])
    paired = paired_intervals(raw,resamples=100)
    assert paired.mean_difference.eq(3).all()
    assert paired.ci_low.eq(3).all() and paired.ci_high.eq(3).all()

def test_csv_preserves_exact_trace_values_and_string_ids():
    trace = generate(WorkloadConfig(count=20))
    assert trace == read_csv(io.StringIO(to_frame(trace).to_csv(index=False)))
    csv = 'id,kind,arrival,track,size,deadline\n001,database,0,20,64,\n'
    assert read_csv(io.StringIO(csv))[0].id == '001'


def test_experiment_summary_retains_absent_class_columns():
    cfg = dict(scenarios=['Database-heavy'],loads=[.1],seeds=[1000],algorithms=['AHDS'],workload={'count':1},bootstrap_resamples=0)
    raw,summary,_,_ = run(cfg)
    assert 'multimedia_deadline_miss_ratio' in summary
    assert 'database_p95_response_ms' in summary
    assert summary[['multimedia_deadline_miss_ratio','database_p95_response_ms']].isna().any(axis=None)


@pytest.mark.parametrize('override',[
    {'loads':[.1,.1]}, {'scenarios':['Balanced','Balanced']},
    {'sensitivity':{'batch_szie':[5]}}, {'sensitivity':{'batch_size':[5,5]}},
])
def test_duplicate_grid_or_misspelled_sensitivity_rejected(override):
    cfg = dict(scenarios=['Balanced'],loads=[.1],seeds=[1000],algorithms=['AHDS'],workload={'count':2},bootstrap_resamples=0)
    with pytest.raises(ValueError): run(cfg | override)
