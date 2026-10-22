"""Validated simulation inputs. Times are milliseconds; sizes are KiB."""
from dataclasses import dataclass, asdict
import math

EPS = 1e-9
MM = 'multimedia'
DB = 'database'

def finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)

@dataclass(frozen=True)
class Request:
    id: str
    kind: str
    arrival: float
    track: int
    size: float = 64
    deadline: float | None = None

@dataclass(frozen=True)
class DiskConfig:
    tracks: int = 200
    initial_head: int = 50
    direction: int = 1
    overhead: float = 1
    seek: float = 0.1
    rate: float = 64

    def __post_init__(self):
        if not isinstance(self.tracks, int) or self.tracks < 1:
            raise ValueError('Track count must be a positive integer.')
        if not isinstance(self.initial_head, int) or not 0 <= self.initial_head < self.tracks:
            raise ValueError('Initial head must be an integer within disk bounds.')
        if self.direction not in (-1, 1):
            raise ValueError('Direction must be -1 or 1.')
        if any(not finite(x) or x <= 0 for x in (self.overhead, self.seek, self.rate)):
            raise ValueError('Disk overhead, seek cost and transfer rate must be positive and finite.')

@dataclass(frozen=True)
class AHDSConfig:
    batch_size: int = 5
    urgency: float = 10
    aging: float = 50
    pressure: float = 0.6

    def __post_init__(self):
        if not isinstance(self.batch_size, int) or self.batch_size < 2:
            raise ValueError('Batch size must be an integer >= 2.')
        if not finite(self.urgency) or self.urgency < 0 or not finite(self.aging) or self.aging <= 0:
            raise ValueError('Urgency must be nonnegative and aging must be positive.')
        if not finite(self.pressure) or not 0 <= self.pressure <= 1:
            raise ValueError('Pressure threshold must be in [0, 1].')

def validate_requests(requests, disk):
    seen = set()
    for r in requests:
        if not isinstance(r.id, str) or not r.id.strip() or r.id in seen:
            raise ValueError('Request IDs must be nonempty and unique.')
        seen.add(r.id)
        if r.kind not in (MM, DB):
            raise ValueError(f'{r.id}: class must be multimedia or database.')
        if not finite(r.arrival) or r.arrival < 0:
            raise ValueError(f'{r.id}: arrival must be nonnegative and finite.')
        if not isinstance(r.track, int) or not 0 <= r.track < disk.tracks:
            raise ValueError(f'{r.id}: track must be an integer in 0–{disk.tracks-1}.')
        if not finite(r.size) or r.size <= 0:
            raise ValueError(f'{r.id}: size must be positive and finite.')
        if r.kind == MM and (not finite(r.deadline) or r.deadline + EPS < r.arrival):
            raise ValueError(f'{r.id}: multimedia deadline must be finite and >= arrival.')
        if r.kind == DB and r.deadline is not None:
            raise ValueError(f'{r.id}: database deadline must be blank.')
    return list(requests)
