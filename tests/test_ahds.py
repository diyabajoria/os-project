import pytest
from src.models import DiskConfig, AHDSConfig, MM, DB
from src.policies import Policy, ABLATIONS
from src.simulator import simulate
from tests.test_engine import m, d, ids

@pytest.mark.parametrize('trace,mode,quota',[
    ([m('M',50,102),d('D',50,40)],'database-protection',2),
    ([m('M',50,105),d('D',50,99)],'multimedia-pressure',4),
    ([m('M',50,180),d('D',50,99)],'balanced',3)])
def test_controller_modes_and_precedence(trace,mode,quota):
    r = simulate(trace,initial_time=100)
    assert r.controller.iloc[0]['mode'] == mode
    assert r.controller.iloc[0].multimedia_quota == quota

@pytest.mark.parametrize('b',range(2,13))
def test_quota_generalization(b):
    import math
    r = simulate([m('M',50,100)],config=AHDSConfig(batch_size=b))
    assert r.controller.iloc[0].multimedia_quota == max(1,min(b-1,math.floor(.6*b+.5)))

def test_independent_example():
    trace = [m('M1',80,108,90),m('M2',20,130,92),d('D1',60,40),d('D2',30,95)]
    p = Policy('AHDS',DiskConfig(),AHDSConfig())
    assert [p.slack(r,100,50) for r in trace[:2]] == [3,25]
    r = simulate(trace,initial_time=100,initial_head=50)
    assert ids(r)[:3] == ['M1','M2','D1']
    assert r.dispatches.completion.tolist()[:3] == [105,113,119]
    assert r.controller.iloc[0].oldest_database_age == 60
    assert r.controller.iloc[0]['mode'] == 'database-protection'

def test_database_aging_override_preserves_direction():
    p = Policy('AHDS',DiskConfig(),AHDSConfig())
    selected, _ = p.select([d('old',20,0),d('new',60,99)],100,50)
    assert selected.id == 'old' and p.direction == 1
    selected,_ = p.select([d('new',60,99),d('behind',10,99)],102,20)
    assert selected.id == 'new' and p.direction == 1

def test_multimedia_seek_preserves_database_direction():
    p = Policy('AHDS',DiskConfig(),AHDSConfig())
    p.direction = -1
    p.select([m('M',150,200)],0,50)
    assert p.direction == -1
    selected,_ = p.select([d('A',100),d('B',160)],2,150)
    assert selected.id == 'A' and p.direction == -1
    selected,_ = p.select([d('B',160)],4,100)
    assert selected.id == 'B' and p.direction == 1

def test_borrowing_consumes_preferred_slots_and_reserved_database():
    trace = [d(f'D{i}',50) for i in range(6)]
    r = simulate(trace)
    assert r.dispatches.preferred_class.tolist() == [MM,MM,MM,DB,DB,MM]
    assert r.dispatches.slot.tolist() == [1,2,3,4,5,1]
    trace = [m(f'M{i}',50,12) for i in range(9)]+[d('D',50)]
    r = simulate(trace)
    assert r.dispatches.iloc[4].kind == DB
    assert r.dispatches.iloc[4].preferred_class == DB

def test_idle_invalidates_batch():
    r = simulate([d('A',50),d('B',50,100)])
    assert r.dispatches.slot.tolist() == [1,1]
    assert r.dispatches.batch.tolist() == [1,2]

def test_feasible_before_infeasible_and_oldest_fallback():
    r = simulate([m('late',199,1),m('feasible',50,3)])
    assert ids(r) == ['feasible','late']
    r = simulate([m('old',199,2),m('new',50,1,1)],initial_time=10)
    assert ids(r) == ['old','new']
    assert r.metrics()['multimedia_deadline_miss_ratio'] == 1

def test_ablations():
    trace = [m('late',199,1),m('feasible',50,100),d('D',50)]
    assert ids(simulate(trace,ABLATIONS[2]))[0] == 'late'
    assert simulate([m('M',50,5)],ABLATIONS[0]).controller.iloc[0]['mode'] == 'balanced'
    p = Policy(ABLATIONS[1],DiskConfig(),AHDSConfig())
    selected,_ = p.select([d('old',10),d('new',60,99)],100,50)
    assert selected.id == 'new'
    assert p.controller[0]['mode'] == 'database-protection'
