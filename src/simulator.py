from dataclasses import dataclass, asdict
import pandas as pd
from src.models import DiskConfig, AHDSConfig, EPS, MM, DB, finite, validate_requests
from src.disk import service_time
from src.policies import Policy

@dataclass
class Result:
    algorithm: str
    dispatches: pd.DataFrame
    queues: pd.DataFrame
    controller: pd.DataFrame
    disk: DiskConfig
    config: AHDSConfig
    origin: float = 0

    def metrics(self):
        from src.metrics import calculate
        return calculate(self)

def simulate(requests, algorithm='AHDS', disk=None, config=None, *, initial_time=0, initial_head=None):
    """initial_time/head support isolated, arrived-only snapshots in unit tests."""
    disk, config = disk or DiskConfig(), config or AHDSConfig()
    requests = validate_requests(list(requests), disk)
    if not finite(initial_time) or initial_time < 0:
        raise ValueError('Initial time must be nonnegative.')
    head = disk.initial_head if initial_head is None else initial_head
    if not isinstance(head, int) or not 0 <= head < disk.tracks:
        raise ValueError('Initial head outside disk.')
    policy = Policy(algorithm, disk, config)
    future = sorted(requests, key=lambda r: (r.arrival, r.id))
    pending, logs, queues = [], [], []
    i, now = 0, float(initial_time)
    def snapshot(time, event):
        queues.append(dict(time=time, event=event, multimedia=sum(r.kind == MM for r in pending), database=sum(r.kind == DB for r in pending)))
    def admit(until):
        nonlocal i
        while i < len(future) and future[i].arrival <= until + EPS:
            arrival = future[i].arrival
            pending.append(future[i])
            i += 1
            snapshot(max(min(arrival, until), initial_time), 'arrival')
    while i < len(future) or pending:
        admit(now)
        if not pending:
            policy.idle()
            now = max(now, future[i].arrival)
            admit(now)
        r, meta = policy.select(tuple(pending), now, head)
        pending.remove(r)
        snapshot(now, 'dispatch')
        duration = service_time(r, head, disk)
        completion = now + duration
        miss = completion > r.deadline + EPS if r.kind == MM else None
        logs.append(dict(**asdict(r), start=now, completion=completion, waiting=now-r.arrival,
                         response=completion-r.arrival, service=duration, head_from=head,
                         movement=abs(r.track-head), deadline_miss=miss,
                         tardiness=max(0, completion-r.deadline) if r.kind == MM else None, **meta))
        admit(completion)
        head, now = r.track, completion
        snapshot(now, 'completion')
    return Result(algorithm, pd.DataFrame(logs), pd.DataFrame(queues), pd.DataFrame(policy.controller), disk, config, initial_time)
