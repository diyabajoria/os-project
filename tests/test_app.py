"""Exercise actual Streamlit widgets and saved playback without a browser."""
from pathlib import Path
from streamlit.testing.v1 import AppTest

def button(app, label):
    return next(b for b in app.button if b.label == label)

def test_all_pages_and_interactive_flows():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py', default_timeout=30).run()
    assert not app.exception
    app.sidebar.radio[0].set_value('Workload Builder').run()
    assert not app.exception
    button(app,'Generate and freeze trace').click().run()
    assert not app.exception
    assert len(app.session_state.trace) == 100
    app.sidebar.radio[0].set_value('Simulation').run()
    button(app,'Run simulation').click().run()
    assert not app.exception
    saved = app.session_state.result.dispatches.copy()
    button(app,'Reset playback').click().run()
    assert app.session_state.step == 0
    button(app,'Next dispatch →').click().run()
    assert app.session_state.step == 1
    assert app.session_state.result.dispatches.equals(saved)
    button(app,'← Previous dispatch').click().run()
    assert app.session_state.step == 0
    assert app.session_state.result.dispatches.equals(saved)
    app.sidebar.radio[0].set_value('Compare Algorithms').run()
    button(app,'Run comparison').click().run()
    assert not app.exception
    assert len(app.session_state.comparison) == 7
    app.sidebar.radio[0].set_value('Experiments').run()
    button(app,'Run paired experiments').click().run()
    assert not app.exception
    assert len(app.session_state.experiment[0]) == 12
    app.sidebar.radio[0].set_value('How It Works').run()
    assert not app.exception


def test_playback_survives_navigation():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py', default_timeout=30).run()
    app.sidebar.radio[0].set_value('Simulation').run()
    button(app,'Run simulation').click().run()
    saved = app.session_state.result.dispatches.copy()
    button(app,'Reset playback').click().run()
    button(app,'Next dispatch →').click().run()
    assert app.session_state.playback_position == 1
    app.sidebar.radio[0].set_value('Overview').run()
    app.sidebar.radio[0].set_value('Simulation').run()
    assert not app.exception
    assert app.session_state.step == 1
    assert app.session_state.playback_position == 1
    assert app.session_state.result.dispatches.equals(saved)


def test_database_only_comparison():
    from src.models import Request, DB
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py', default_timeout=30).run()
    app.session_state.trace = [Request('D1',DB,0,20),Request('D2',DB,1,80)]
    app.session_state.trace_revision += 1
    app.sidebar.radio[0].set_value('Compare Algorithms').run()
    button(app,'Run comparison').click().run()
    assert not app.exception
    assert app.session_state.comparison.multimedia_deadline_miss_ratio.isna().all()
