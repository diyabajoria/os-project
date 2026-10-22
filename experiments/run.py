"""Paired trace-level experiments. Run: python -m experiments.run --config ..."""
import argparse
from dataclasses import asdict
from itertools import product
import json
from pathlib import Path
import random
import pandas as pd
from src.models import DiskConfig, AHDSConfig, finite
from src.workloads import WorkloadConfig, generate
from src.simulator import simulate

PAIR_COLUMNS = ['scenario', 'load', 'parameters', 'algorithm', 'reference', 'metric', 'pairs', 'mean_difference', 'ci_low', 'ci_high']

DEFAULT = dict(scenarios=['Balanced', 'Multimedia-heavy', 'Database-heavy'], loads=[.06, .12, .24],
               seeds=list(range(1000, 1030)), development_seeds=list(range(10)),
               algorithms=['FCFS', 'SSTF', 'LOOK', 'C-LOOK', 'Global EDF', 'Fixed Hybrid', 'AHDS'],
               bootstrap_resamples=10000, bootstrap_seed=987, reference='AHDS', workload={'count': 300},
               sensitivity={'batch_size': [5], 'urgency': [10], 'aging': [50], 'pressure': [.6]})

def paired_intervals(raw, reference='AHDS', resamples=10000, seed=987):
    rng = random.Random(seed)
    rows = []
    keys = ['scenario', 'load', 'parameters']
    metrics = ['multimedia_deadline_miss_ratio', 'database_p95_response_ms', 'overall_mean_waiting_ms', 'total_head_movement']
    for group, frame in raw.groupby(keys, sort=True):
        for algorithm in sorted(set(frame.algorithm)-{reference}):
            for metric in metrics:
                pairs = frame[frame.algorithm == algorithm][['seed', metric]].merge(
                    frame[frame.algorithm == reference][['seed', metric]], on='seed', suffixes=('_algorithm', '_reference'), validate='one_to_one').dropna()
                differences = (pairs[f'{metric}_algorithm']-pairs[f'{metric}_reference']).tolist()
                if not differences: continue
                means = [sum(rng.choices(differences, k=len(differences)))/len(differences) for _ in range(resamples)]
                rows.append(dict(zip(keys, group)) | dict(algorithm=algorithm, reference=reference, metric=metric,
                    pairs=len(differences), mean_difference=sum(differences)/len(differences),
                    ci_low=float(pd.Series(means).quantile(.025)) if means else None,
                    ci_high=float(pd.Series(means).quantile(.975)) if means else None))
    return pd.DataFrame(rows, columns=PAIR_COLUMNS)

def run(config, progress=None):
    cfg = DEFAULT | config
    seeds = cfg['seeds']
    if not seeds or len(seeds) != len(set(seeds)):
        raise ValueError('Evaluation seeds must be nonempty and unique.')
    if set(seeds) & set(cfg['development_seeds']):
        raise ValueError('Development and evaluation seeds must be disjoint.')
    if not cfg['algorithms'] or len(cfg['algorithms']) != len(set(cfg['algorithms'])):
        raise ValueError('Select unique algorithms.')
    if not isinstance(cfg['bootstrap_resamples'], int) or cfg['bootstrap_resamples'] < 0:
        raise ValueError('Bootstrap resamples must be a nonnegative integer.')
    if cfg['bootstrap_resamples'] and cfg['reference'] not in cfg['algorithms']:
        raise ValueError('Bootstrap reference must be among selected algorithms.')
    for key in ('scenarios', 'loads'):
        if not cfg[key] or len(cfg[key]) != len(set(cfg[key])):
            raise ValueError(f'{key} must be nonempty and unique to preserve seed pairing.')
    if any(not finite(load) or load <= 0 for load in cfg['loads']):
        raise ValueError('Loads must be positive and finite.')
    supplied = cfg.get('sensitivity', {})
    unknown = set(supplied)-set(asdict(AHDSConfig()))
    if unknown:
        raise ValueError('Unknown sensitivity parameters: ' + ', '.join(sorted(unknown)))
    if any(not values or len(values) != len(set(values)) for values in supplied.values()):
        raise ValueError('Sensitivity values must be nonempty and unique.')
    disk = DiskConfig(**cfg.get('disk', {}))
    sensitivity = {k: cfg.get('sensitivity', {}).get(k, [v]) for k, v in asdict(AHDSConfig()).items()}
    cfg['disk'] = asdict(disk)
    cfg['workload'] = asdict(WorkloadConfig(**cfg['workload']))
    cfg['sensitivity'] = sensitivity
    parameters = [AHDSConfig(**dict(zip(sensitivity, values))) for values in product(*sensitivity.values())]
    if not parameters or not cfg['scenarios'] or not cfg['loads']:
        raise ValueError('Experiment grid must be nonempty.')
    total = len(cfg['scenarios'])*len(cfg['loads'])*len(seeds)*len(parameters)*len(cfg['algorithms'])
    rows = []
    for scenario, load, seed in product(cfg['scenarios'], cfg['loads'], seeds):
        # Generate exactly once per trace, outside the algorithm/parameter loops.
        workload = WorkloadConfig(**(cfg['workload'] | dict(preset=scenario, intensity=load, seed=seed)))
        trace = generate(workload, disk)
        for param, algorithm in product(parameters, cfg['algorithms']):
            result = simulate(trace, algorithm, disk, param)
            rows.append(dict(scenario=scenario, load=load, seed=seed, parameters=json.dumps(asdict(param), sort_keys=True), algorithm=algorithm) | result.metrics())
            if progress: progress(len(rows)/total)
    raw = pd.DataFrame(rows)
    # Keep absent-class metrics as numeric NaN, so summaries retain their columns.
    for column in set(raw.columns)-{'scenario', 'parameters', 'algorithm'}:
        raw[column] = pd.to_numeric(raw[column])
    summary = raw.groupby(['scenario', 'load', 'parameters', 'algorithm']).mean(numeric_only=True).drop(columns='seed').reset_index()
    paired = paired_intervals(raw, cfg['reference'], cfg['bootstrap_resamples'], cfg['bootstrap_seed']) if cfg['bootstrap_resamples'] else pd.DataFrame(columns=PAIR_COLUMNS)
    return raw, summary, paired, cfg

def export(output, raw, summary, paired, config):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for name, frame in [('raw', raw), ('summary', summary), ('paired', paired)]:
        frame.to_csv(output/f'{name}.csv', index=False)
    payload = dict(configuration=config, raw=json.loads(raw.to_json(orient='records')),
                   summary=json.loads(summary.to_json(orient='records')), paired=json.loads(paired.to_json(orient='records')))
    (output/'results.json').write_text(json.dumps(payload, indent=2, allow_nan=False))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--output', type=Path, default=Path('experiments/output'))
    args = parser.parse_args()
    config = json.loads(args.config.read_text()) if args.config else DEFAULT
    raw, summary, paired, resolved = run(config)
    export(args.output, raw, summary, paired, resolved)
    print(f'Wrote {len(raw)} trace-level measurements to {args.output}')

if __name__ == '__main__': main()
