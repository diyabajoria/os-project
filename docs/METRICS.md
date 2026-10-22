All metrics derive from a completed event log; misses are counted once, at completion.

| Metric | Definition |
|---|---|
| Waiting | start − arrival, in ms |
| Response | completion − arrival, in ms (includes service) |
| Service | positioning overhead + physical seek + transfer time |
| Head movement | Absolute track difference per dispatch, including C-LOOK wraps |
| Deadline miss ratio | Multimedia completions strictly after deadline (tolerance 1e-9) / multimedia count |
| Tardiness | max(0, completion − deadline), for every multimedia request, including on-time zeros |
| Database threshold violation ratio | Fraction of database requests with waiting > W, within tolerance; equality is not a violation |
| p95 / maximum | Per-class 95th percentile / largest observation |
| Makespan | Final completion − observation origin; normal runs start at time 0 |
| Request throughput | Completed request count / makespan, requests/ms |
| Byte throughput | Completed KiB × 1024 / makespan, bytes/ms |
| Actual request share | Class request count / total completed count |
| Actual disk-time share | Class service-time sum / total service time, excluding idle time |
| Backlog at final arrival | Requests arrived but not completed at final arrival; includes in-service request |
| Mode counts | Number of batch decisions in each mode, not number of dispatches |
| Quota changes | Changes in multimedia quota between successive batches; initial allocation is not a change |

Mean waiting and response are reported overall and by class. Database waiting and response include p95 and maximum; multimedia tardiness includes mean and p95. Percentiles use pandas' linear interpolation at index (n−1)q; a single observation has that value as its percentile. Absent-class statistics and shares are represented as null/NaN and shown as **N/A**. They are not zero-performance observations. Empty traces have zero count, movement and makespan and no defined throughput.

Throughput includes all idle time from time 0, including idle before the first arrival. A test snapshot uses its explicit observation origin instead. Queue curves exclude the in-service request. Head curves hold position throughout idle, then show fixed overhead, physical seek, and transfer in that order; this order is a visualization convention consistent with total service time.

Experiments compute each metric per frozen trace, then average trace-level values. Mean p95 across seeds is not a pooled request-level p95. Paired bootstrap samples seed-pair differences with replacement within a scenario/load/parameter group, using a fixed bootstrap seed and percentile 95% intervals. A difference is **algorithm minus reference**; negative values favor that algorithm only for lower-is-better metrics. No statistical conclusion is asserted by the code. Thirty evaluation seeds and 10,000 resamples are the full-run defaults; the smoke configuration is deliberately smaller.
