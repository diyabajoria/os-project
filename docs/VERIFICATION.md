# Verification record

Verified on 22 October 2026 with Python 3.14.6. Exact installed versions are recorded in `requirements-lock.txt`.

- `python -m pytest -q`: **84 passed**. Tests cover service arithmetic, eligibility, arrivals during service and exactly at completion, non-preemption, idle advancement, deadline equality, conventional orderings in both directions, C-LOOK physical wrap, AHDS controller precedence and quotas, aging and direction persistence, borrowing and slot consumption, idle batch reset, feasibility and fallback, deterministic ties, missing-class metrics, no lost/duplicate completion, seeded generation, invalid inputs and exact CSV/ZIP round trips.
- The independently supplied AHDS snapshot has slacks 3/25 ms, oldest database age 60 ms, database-protection mode, first dispatches M1/M2/D1, and completions 105/113/119 ms.
- Streamlit's AppTest exercised all six pages, generator submission, simulation, saved-log previous/next playback, all-seven-policy comparison, and the interactive paired experiment form. No application exceptions occurred.
- A separate end-to-end 60-request trace completed under all seven policies. Comparison and per-request CSV files read back; the trace ZIP read back to exactly the same requests with configuration and seed intact.
- The CLI smoke grid completed: two scenarios × two loads × two seeds × five policies = **40 trace-level rows**, 20 summary rows, and 64 paired metric intervals (two seed pairs each, 100 smoke resamples). JSON and all CSV outputs read back successfully. This is functional validation, not evidence of a performance improvement.
- Head movement, service timeline, queue and controller figures were generated from event logs. Head and timeline PNGs were visually inspected. Plot files are in `experiments/output/verification/`.
- Streamlit started successfully on `http://127.0.0.1:8501`. Live Chrome verification was unavailable because computer-use access to Google Chrome was not approved. The interface was checked using Streamlit's own test harness; no claim of browser visual verification is made.

Commands used:

```bash
source .venv/bin/activate
python -m pytest -q
python -m experiments.run --config experiments/smoke.json --output experiments/output/smoke
streamlit run app.py --server.headless true --server.address 127.0.0.1 --browser.gatherUsageStats false
```

The full research grid was intentionally not run. No performance superiority, hard deadline guarantee, or fixed database waiting bound is asserted. Nothing was committed, pushed or deployed.

## Review and interface redesign — 22 October 2026

The follow-up review replaced the documentation-heavy landing page with a workload dashboard, moved navigation above collapsed settings, added grouped generator/editor/import tabs, readable result summaries, chart tabs, a persistent playback cursor, and clear empty states. A local light theme with navy navigation is defined in `.streamlit/config.toml`; restart Streamlit to load theme changes. No additional dependencies were introduced.

Correctness fixes found during review:

- Absent-class comparison metrics render N/A without creating zero-valued bars or raising a plotting error.
- Experiment summaries preserve absent-class numeric metric columns rather than silently dropping them.
- Duplicate scenario/load/sensitivity entries and unknown sensitivity names are rejected, protecting seed pairing. Paired merges explicitly require one row per seed.
- Playback position survives leaving and returning to Simulation; a new trace or disk/controller configuration still invalidates saved runs.
- Head charts honor an explicitly initialized snapshot head and hold the head through idle periods; playback axes remain fixed across steps.
- Arrival snapshots within numerical tolerance cannot produce backwards queue-chart timestamps.
- Chart rendering batches per-class markers and service intervals instead of creating one plotting object per request.

Validation: **95 tests passed** including new regressions for these behaviors. The six-page AppTest walkthrough and a fresh 40-row experiment smoke run passed; all CSV/JSON exports read back successfully. Revised arrival and absent-class charts were visually inspected. The local server health endpoint returned `ok`. Chrome access remains unavailable through computer-use tooling, so live browser visual verification was not performed.
