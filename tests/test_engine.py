import pytest
from src.models import Request, DiskConfig, AHDSConfig, MM, DB
from src.disk import service_time
from src.simulator import simulate
from src.policies import ALGORITHMS, ABLATIONS

def d(id, track, arrival=0): return Request(id, DB, arrival, track)
def m(id, track, deadline, arrival=0): return Request(id, MM, arrival, track, 64, deadline)
def ids(result): return result.dispatches.id.tolist()

def test_service_and_seek():
    r = simulate([d('A',80)])
    assert service_time(d('A',80),50,DiskConfig()) == 5
    assert r.dispatches.iloc[0].movement == 30
    assert r.dispatches.iloc[0].completion == 5

def test_nonpreemption_future_eligibility_and_idle():
    r = simulate([d('A',199),m('B',50,10,1),d('C',50,100)],'Global EDF')
    assert ids(r) == ['A','B','C']
    assert r.dispatches.iloc[1].start == pytest.approx(16.9)
    assert r.dispatches.iloc[2].start == 100
    assert (r.dispatches.start >= r.dispatches.arrival).all()

def test_exact_completion_admitted_and_deadline_equality():
    r = simulate([d('A',50),d('Z',60),m('B',50,4,2)],'Global EDF')
    assert ids(r) == ['A','B','Z']
    assert not r.dispatches.iloc[1].deadline_miss

@pytest.mark.parametrize('name,expected',[
    ('FCFS',['A','B','C','D']),('SSTF',['A','C','D','B']),
    ('LOOK',['C','D','A','B']),('C-LOOK',['C','D','B','A'])])
def test_conventional_orders(name,expected):
    trace = [d('A',40),d('B',10),d('C',60),d('D',90)]
    assert ids(simulate(trace,name)) == expected

def test_clook_physical_wrap():
    r = simulate([d('A',40),d('B',10),d('C',60),d('D',90)],'C-LOOK')
    assert r.dispatches.movement.tolist() == [10,30,80,30]
    assert r.dispatches.iloc[2].service == 10

@pytest.mark.parametrize('name',ALGORITHMS+ABLATIONS)
def test_completion_once_and_determinism(name):
    from src.workloads import generate, WorkloadConfig
    trace = generate(WorkloadConfig(count=80))
    a,b = simulate(trace,name),simulate(trace,name)
    assert len(a.dispatches) == len(trace) and a.dispatches.id.is_unique
    assert set(a.dispatches.id) == {r.id for r in trace}
    assert a.dispatches.equals(b.dispatches)
    assert (a.dispatches.start.iloc[1:].to_numpy() >= a.dispatches.completion.iloc[:-1].to_numpy()).all()

@pytest.mark.parametrize('name',ALGORITHMS)
def test_ties(name):
    assert ids(simulate([d('Z',50),d('A',50)],name)) == ['A','Z']

def test_missing_class_metrics():
    r = simulate([d('A',50)])
    assert r.metrics()['multimedia_deadline_miss_ratio'] is None
    assert r.metrics()['multimedia_mean_waiting_ms'] is None
    assert simulate([m('A',50,100)]).metrics()['database_p95_response_ms'] is None

def test_metrics_independent_arithmetic():
    result = simulate([d('A',50),m('B',60,4)],'FCFS')
    v = result.metrics()
    assert v['total_head_movement'] == 10
    assert v['makespan_ms'] == 5
    assert v['overall_mean_waiting_ms'] == 1
    assert v['database_p95_response_ms'] == 2
    assert v['multimedia_deadline_miss_ratio'] == 1
    assert v['multimedia_mean_tardiness_ms'] == 1
    assert v['request_throughput_per_ms'] == .4
    assert v['byte_throughput_per_ms'] == 128*1024/5
    assert v['multimedia_disk_time_share'] == .6
    assert v['backlog_at_final_arrival'] == 2

def test_policy_only_receives_arrived_requests(monkeypatch):
    from src.policies import Policy
    original = Policy.select
    seen = []
    def checked(self, pending, now, head):
        assert all(r.arrival <= now+1e-9 for r in pending)
        seen.append((now,tuple(r.id for r in pending)))
        return original(self,pending,now,head)
    monkeypatch.setattr(Policy,'select',checked)
    simulate([d('A',50),d('B',60,1),m('C',50,100,2),d('D',50,100)],'AHDS')
    assert seen[0][1] == ('A',)
    assert set(seen[1][1]) == {'B','C'}

@pytest.mark.parametrize('name,expected',[
    ('LOOK',['A','B','C','D']),('C-LOOK',['A','B','D','C'])])
def test_decreasing_direction(name,expected):
    assert ids(simulate([d('A',40),d('B',10),d('C',60),d('D',90)],name,DiskConfig(direction=-1))) == expected

def test_queue_admits_arrivals_during_service():
    r = simulate([d('A',50),d('B',60,1),d('C',50,2)])
    arrivals = r.queues[r.queues.event == 'arrival']
    assert arrivals.time.tolist() == [0,1,2]
    assert arrivals.database.tolist() == [1,1,2]
    assert r.queues.iloc[-1].database == 0
