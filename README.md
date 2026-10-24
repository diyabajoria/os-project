# Adaptive Hybrid Disk Scheduling for Mixed Multimedia and Database Workloads

A complete college Operating Systems project: Python discrete-event HDD simulation, Streamlit lab, Matplotlib charts, pandas exports, and pytest correctness tests. It simulates deadline-tagged multimedia requests and independent database page I/O. It does not access physical disks, run a database, or play video. Scheduling uses deterministic rules, with no AI, ML, external APIs, or authentication.

## Setup and launch

Python 3.11 or newer and Streamlit 1.66 or newer are required (verified here with Python 3.14).

```bash
git clone https://github.com/diyabajoria/os-project.git
cd os-project
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501. After a theme configuration change, restart Streamlit with Ctrl+C and `streamlit run app.py` to load the new theme. If the supplied `.venv` already exists, activate it and run Streamlit. Run commands from the project directory. `requirements-lock.txt` records the exact verified environment; use it in place of `requirements.txt` to reproduce those versions on a compatible platform.

## Verify and run experiments

```bash
source .venv/bin/activate
python -m pytest -q
python -m experiments.run --config experiments/smoke.json --output experiments/output/smoke
```

Full research defaults (30 evaluation seeds, 10,000 paired bootstrap resamples; intentionally not run during setup):

```bash
python -m experiments.run --config experiments/research.json --output experiments/output/research
```

The runner writes raw.csv, summary.csv, paired.csv and results.json (including the complete resolved configuration). Results are paired across identical scenario/load/seed traces. A paired difference is algorithm minus AHDS. Sensitivity grids accept lists for `batch_size`, `urgency`, `aging` and `pressure` in `sensitivity`. A saved configuration can specify all `WorkloadConfig`, `DiskConfig` fields. Development and evaluation seeds must be disjoint. Bootstrap can be disabled with `bootstrap_resamples: 0`.

## Demo walkthrough

1. In Workload Builder choose Balanced, seed 42 and 100 requests; generate and freeze. Explore all eight scenarios or import `data/sample.csv`. Disk and AHDS parameters are in the sidebar.
2. Edit rows if desired, then click Validate and freeze edited table. CSV requires id, kind, arrival, track, size and deadline; leave database deadlines blank. Download the ZIP to retain both trace and configuration/seed.
3. In Simulation run AHDS. Reset playback and press Next dispatch to inspect mode, preferred and actual class, slack, database age and selection reason. Playback reads the completed log rather than rerunning simulation.
4. Compare Algorithms runs selected policies on the identical frozen trace. Inspect deadline misses against database response times and head movement. Export the metrics.
5. Experiments runs small paired evaluation grids with a progress indicator. The CLI adds sensitivity and paired confidence intervals. How It Works contains exact rules, definitions and limitations.

## Viva explanation

"A single HDD must balance multimedia deadlines and database waiting time. Our AHDS assigns deterministic batches of request slots using feasible multimedia pressure and the oldest database age. Multimedia uses feasible EDF with best-effort late completion; database I/O uses persistent LOOK with an oldest-overdue override. We compare it with conventional policies, a fixed hybrid and ablations on the same seeded traces. The contribution is this specified combination and a reproducible evaluation framework, rather than a claim of academic novelty. Quotas count requests, not bandwidth, and do not guarantee deadlines or bounded waiting."

At B=5 the controller chooses M M D D D for database protection before considering multimedia pressure, M M M M D for high pressure, otherwise M M M D D. Empty preferred queues borrow without credits. The supplied worked example is verified: M1/M2 slacks are 3/25 ms at t=100, database age is 60 ms, the mode is protection, and M1, M2, D1 complete at 105, 113, 119 ms.

## Source map

- `src/models.py`, `disk.py`: validated requests and configurations; shared service arithmetic.
- `src/simulator.py`: event admission, non-preemptive service, completed dispatch logs.
- `src/policies/`: seven required schedulers and three experiment-only ablations.
- `src/workloads.py`: reproducible generators, strict CSV parser, trace/config ZIP export.
- `src/metrics.py`, `plots.py`: common measurements and charts from actual event data.
- `app.py`, `src/ui.py`, `.streamlit/config.toml`: six-page interactive lab, persistent playback, presentation helpers, and the navy/light theme. Navigation appears above collapsed disk/controller settings; workload creation and result inspection use tabs.
- `experiments/run.py`: paired-seed runner and paired bootstrap intervals.
- `tests/`: arithmetic, policy semantics, generator/export and UI checks.

See [algorithm specification](docs/ALGORITHMS.md), [metric definitions](docs/METRICS.md), and [design limitations](docs/LIMITATIONS.md). APEX is the conceptual base paper, not a reproduced baseline: https://doi.org/10.1007/s00530-005-0189-0. No local research paper was available. This project follows the supplied specification. See [verification record](docs/VERIFICATION.md) for checks performed.

## Contributors

- Diya Bajoria
- Tarshneet Kaur Duggal
