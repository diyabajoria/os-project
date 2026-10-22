"""Policies see only pending requests; no access to the future event stream."""
import math
from src.models import MM, DB, EPS
from src.disk import service_time

ALGORITHMS = ['FCFS', 'SSTF', 'LOOK', 'C-LOOK', 'Global EDF', 'Fixed Hybrid', 'AHDS']
ABLATIONS = ['Ablation: no adaptation', 'Ablation: no dispatch aging', 'Ablation: no feasibility handling']

def oldest(r):
    return r.arrival, r.id

class Policy:
    def __init__(self, name, disk, config):
        if name not in ALGORITHMS + ABLATIONS:
            raise ValueError(f'Unknown algorithm: {name}')
        self.name, self.disk, self.config = name, disk, config
        self.direction = disk.direction
        self.slot = 0
        self.batch = 0
        self.mode = None
        self.quota = None
        self.controller = []

    def idle(self):
        self.slot = 0
        self.mode = None

    def slack(self, r, now, head):
        return r.deadline - now - service_time(r, head, self.disk)

    def look(self, queue, head, circular=False):
        candidates = [r for r in queue if (r.track - head) * self.direction >= 0]
        if not candidates:
            if circular:
                extreme = min(r.track for r in queue) if self.direction == 1 else max(r.track for r in queue)
                return min((r for r in queue if r.track == extreme), key=oldest)
            self.direction *= -1
            candidates = list(queue)
        return min(candidates, key=lambda r: (abs(r.track-head), *oldest(r)))

    def select(self, pending, now, head):
        name = self.name
        meta = dict(batch_mode=None, preferred_class=None, batch=None, slot=None,
                    multimedia_quota=None, pressure=None, oldest_database_age=None)
        if name == 'FCFS':
            r, reason = min(pending, key=oldest), 'Oldest arrival, then ID'
        elif name == 'SSTF':
            r = min(pending, key=lambda r: (abs(r.track-head), *oldest(r)))
            reason = 'Nearest track, then arrival and ID'
        elif name in ('LOOK', 'C-LOOK'):
            r = self.look(pending, head, name == 'C-LOOK')
            reason = f'{name} in stored direction {self.direction:+d}; physical seek counted'
        elif name == 'Global EDF':
            r = min(pending, key=lambda r: (r.deadline if r.kind == MM else math.inf, *oldest(r)))
            reason = 'Global earliest deadline; database deadline is infinity'
        else:
            mm = [r for r in pending if r.kind == MM]
            db = [r for r in pending if r.kind == DB]
            no_feasibility = name == ABLATIONS[2]
            if self.mode is None or self.slot == 0:
                feasible = mm if no_feasibility else [r for r in mm if self.slack(r, now, head) >= -EPS]
                pressure = sum(self.slack(r, now, head) <= self.config.urgency + EPS for r in feasible) / max(1, len(feasible))
                age = max((now-r.arrival for r in db), default=0)
                fixed = name in ('Fixed Hybrid', ABLATIONS[0])
                self.mode = 'balanced' if fixed else ('database-protection' if age + EPS >= self.config.aging else 'multimedia-pressure' if pressure + EPS >= self.config.pressure else 'balanced')
                b = 5 if name == 'Fixed Hybrid' else self.config.batch_size
                fraction = {'balanced': .6, 'database-protection': .4, 'multimedia-pressure': .8}[self.mode]
                self.quota = max(1, min(b-1, math.floor(fraction*b+.5)))
                self.batch += 1
                self.controller.append(dict(time=now, batch=self.batch, mode=self.mode, multimedia_quota=self.quota, database_quota=b-self.quota, pressure=pressure, oldest_database_age=age))
            b = 5 if name == 'Fixed Hybrid' else self.config.batch_size
            preferred = MM if self.slot < self.quota else DB
            actual = preferred if (mm if preferred == MM else db) else (DB if preferred == MM else MM)
            if actual == MM:
                feasible = mm if no_feasibility else [r for r in mm if self.slack(r, now, head) >= -EPS]
                r = min(feasible, key=lambda r: (r.deadline, *oldest(r))) if feasible else min(mm, key=oldest)
                reason = 'EDF over ' + ('all multimedia' if no_feasibility else 'feasible multimedia') if feasible else 'No feasible multimedia; oldest best-effort request'
            else:
                overdue = [r for r in db if now-r.arrival + EPS >= self.config.aging]
                if overdue and name != ABLATIONS[1]:
                    r, reason = min(overdue, key=oldest), 'Oldest database request at aging threshold'
                else:
                    r = self.look(db, head)
                    reason = f'Database LOOK in stored direction {self.direction:+d}'
            if actual != preferred:
                reason += '; borrowed empty preferred class slot'
            c = self.controller[-1]
            meta.update(batch_mode=self.mode, preferred_class=preferred, batch=self.batch, slot=self.slot+1,
                        multimedia_quota=self.quota, pressure=c['pressure'], oldest_database_age=c['oldest_database_age'])
            self.slot = (self.slot+1) % b
        meta.update(reason=reason, actual_class=r.kind,
                    slack=self.slack(r, now, head) if r.kind == MM else None,
                    database_age=now-r.arrival if r.kind == DB else None)
        return r, meta
