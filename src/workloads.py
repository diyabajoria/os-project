"""Seeded synthetic traces and lossless CSV + JSON configuration bundles."""
from dataclasses import dataclass, asdict
import io
import json
import random
import zipfile
import pandas as pd
from src.models import Request, DiskConfig, MM, DB, finite, validate_requests

PRESETS = ['Balanced', 'Multimedia-heavy', 'Database-heavy', 'Database-to-multimedia transition',
           'Multimedia-to-database transition', 'Multimedia bursts', 'Adversarial locality', 'Overload stress test']
COLUMNS = ['id', 'kind', 'arrival', 'track', 'size', 'deadline']

@dataclass(frozen=True)
class WorkloadConfig:
    preset: str = 'Balanced'
    seed: int = 42
    count: int = 100
    intensity: float = .12
    distribution: str = 'locality'
    mm_size: float = 64
    db_size: float = 64
    deadline_min: float = 20
    deadline_max: float = 80
    streams: int = 4
    stream_step: int = 3
    phase_ms: float = 100

    def __post_init__(self):
        if self.preset not in PRESETS or self.distribution not in ('uniform', 'locality'):
            raise ValueError('Unknown workload preset or track distribution.')
        if not isinstance(self.seed, int) or not isinstance(self.count, int) or self.count < 1:
            raise ValueError('Seed must be an integer; request count must be a positive integer.')
        for key in ('intensity', 'mm_size', 'db_size', 'deadline_min', 'deadline_max', 'phase_ms'):
            if not finite(getattr(self, key)) or getattr(self, key) <= 0:
                raise ValueError(f'{key} must be positive and finite.')
        if self.deadline_max < self.deadline_min:
            raise ValueError('Maximum relative deadline must be >= minimum.')
        if not isinstance(self.streams, int) or self.streams < 1 or not isinstance(self.stream_step, int) or self.stream_step < 1:
            raise ValueError('Stream count and step must be positive integers.')

def generate(config=None, disk=None):
    c, disk = config or WorkloadConfig(), disk or DiskConfig()
    rng = random.Random(c.seed)
    positions = [rng.randrange(disk.tracks) for _ in range(c.streams)]
    requests, now = [], 0.0
    for i in range(c.count):
        rate = c.intensity * (3 if c.preset == 'Overload stress test' else 1)
        now += rng.expovariate(rate)
        p = .5
        if c.preset == 'Multimedia-heavy': p = .8
        elif c.preset == 'Database-heavy': p = .2
        elif c.preset == 'Database-to-multimedia transition': p = .2 if now < c.phase_ms else .8
        elif c.preset == 'Multimedia-to-database transition': p = .8 if now < c.phase_ms else .2
        elif c.preset == 'Multimedia bursts': p = .9 if int(now/c.phase_ms) % 2 else .1
        kind = MM if rng.random() < p else DB
        if c.preset == 'Adversarial locality':
            track = rng.randrange(max(1, disk.tracks//10))
            if kind == MM: track = disk.tracks-1-track
        elif c.distribution == 'uniform':
            track = rng.randrange(disk.tracks)
        elif kind == MM:
            stream = rng.randrange(c.streams)
            track = positions[stream]
            positions[stream] = (track+c.stream_step) % disk.tracks
        else:
            center = disk.tracks//4 if rng.random() < .8 else 3*disk.tracks//4
            track = min(disk.tracks-1, max(0, int(rng.gauss(center, max(1, disk.tracks/30)))))
        requests.append(Request(f'R{i+1:05d}', kind, now, track, c.mm_size if kind == MM else c.db_size,
                                now+rng.uniform(c.deadline_min, c.deadline_max) if kind == MM else None))
    return validate_requests(requests, disk)

def to_frame(requests):
    frame = pd.DataFrame([asdict(r) for r in requests], columns=COLUMNS)
    return frame.astype({'arrival': float, 'track': int, 'size': float, 'deadline': float})

def from_frame(frame, disk=None):
    missing = set(COLUMNS)-set(frame.columns)
    if missing:
        raise ValueError('Missing CSV columns: ' + ', '.join(sorted(missing)))
    requests = []
    for index, row in frame.iterrows():
        try:
            track = float(row['track'])
            if not track.is_integer(): raise ValueError('track must be an integer')
            requests.append(Request(str(row['id']).strip() if pd.notna(row['id']) else '',
                                    str(row['kind']).strip(), float(row['arrival']), int(track),
                                    float(row['size']), None if pd.isna(row['deadline']) or row['deadline'] == '' else float(row['deadline'])))
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError(f'Row {index}: {exc}') from exc
    return validate_requests(requests, disk or DiskConfig())

def read_csv(source, disk=None):
    try:
        return from_frame(pd.read_csv(source, dtype=str, keep_default_na=False), disk)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        raise ValueError(f'Invalid CSV: {exc}') from exc

def trace_bundle(requests, metadata):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('trace.csv', to_frame(requests).to_csv(index=False))
        archive.writestr('configuration.json', json.dumps(metadata, indent=2, allow_nan=False))
    return buffer.getvalue()
