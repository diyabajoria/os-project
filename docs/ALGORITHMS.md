All policies share one non-preemptive discrete-event engine. Only arrived requests are passed to a policy. Arrivals during service and at completion are admitted before the next selection. Empty queues advance the clock to the next arrival and invalidate a hybrid batch. Every late request is retained and completed.

Service time (ms) = overhead + seek_cost × |track − head| + size_KiB / transfer_rate.

The absolute numerical tolerance is **1e-9 ms** for arrival admission, deadline equality, slack feasibility, urgency, age and pressure threshold comparisons. Track ordering is exact integer ordering. Arrival times and IDs give deterministic ordering; IDs sort lexicographically.

| Policy | Dispatch rule |
|---|---|
| FCFS | Arrival time, then ID |
| SSTF | Track distance, arrival, ID |
| LOOK | Nearest track in a persistent direction; reverse only with no candidate |
| C-LOOK | Same configured direction; wrap to opposite pending extreme; physical wrap distance and time are charged |
| Global EDF | Deadline, arrival, ID; database deadline is infinity |
| Fixed Hybrid | Exactly five slots: M M M D D, with AHDS within-class rules |
| AHDS | Adaptive quotas, feasible multimedia EDF, database aging + persistent LOOK |

Global EDF can delay database I/O with strict multimedia priority. LOOK does not move to an unnecessary disk boundary. For a head-position tie, both directions include requests at the current head; equal tracks use arrival and ID.

At a batch boundary, compute slack for each queued multimedia request as deadline − now − immediate service time. Feasible means slack ≥ 0 within tolerance. Urgent means feasible and slack ≤ U. Pressure is urgent feasible count / max(1, feasible count). Oldest database age is max(now − arrival), or zero if absent.

| Ordered condition | Mode | B=5 slots | General multimedia quota |
|---|---|---|---|
| Oldest database age ≥ W | Database protection | M M D D D | floor(0.4B + 0.5) |
| Otherwise pressure ≥ threshold | Multimedia pressure | M M M M D | floor(0.8B + 0.5) |
| Otherwise | Balanced | M M M D D | floor(0.6B + 0.5) |

Clamp the multimedia quota to [1, B−1]; the rest are database slots. B must be at least 2. Quotas count **requests**, not bytes, disk time, or bandwidth. Parameters default to B=5, U=10 ms, W=50 ms, pressure=0.60. Fixed Hybrid deliberately stays at B=5; use the no-adaptation ablation for a fixed balanced quota at another B.

```text
when both queues empty:
    invalidate batch; jump to next arrival
at each batch boundary:
    if oldest database age >= W: choose protection quota
    else if multimedia pressure >= threshold: choose pressure quota
    else: choose balanced quota
for each preferred slot (all M slots, then all D slots):
    if preferred queue empty: borrow from other class
    if actual class is M:
        recompute slack
        choose earliest deadline among feasible requests (arrival, ID ties)
        if none feasible: choose oldest multimedia request
    if actual class is D:
        if any age >= W: choose oldest overdue request
        else: use persistent database LOOK
    consume preferred slot even when borrowed
    run selected request to completion; admit arrivals; update head
```

Multimedia seeks and database aging overrides move the physical head but never change stored database LOOK direction. Ordinary database LOOK reverses only when its current direction has no candidate. Reserved database slots cannot be overridden by urgent multimedia. No borrowing credits or debts carry over.

Experiment-only ablations:

- **No adaptation:** balanced quotas at configurable B; same within-class rules.
- **No dispatch aging:** adaptive controller still considers database age, but database selection always uses LOOK.
- **No feasibility handling:** pressure uses all queued multimedia, including negative slack as urgent; multimedia dispatch is EDF over all requests.

These are ablations, not conventional schedulers. The negative-slack requests in the main algorithm remain queued for best effort. Under this linear service model, intervening service cannot restore negative slack: the triangle inequality prevents reducing total seek distance, and each service adds positive overhead and transfer time.
