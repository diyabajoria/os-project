"""Regression tests for real data visualizations, not style implementation."""
import matplotlib.pyplot as plt
import pandas as pd
import pytest
from src.models import Request, DB
from src.simulator import simulate
from src import plots


def test_missing_class_comparison_keeps_na():
    frame = pd.DataFrame({'multimedia_deadline_miss_ratio':[None,None]},index=['AHDS','FCFS'])
    fig = plots.comparison(frame,list(frame.columns),'Misses','Ratio')
    assert [text.get_text() for text in fig.axes[0].texts] == ['N/A','N/A']
    assert len(fig.axes[0].patches) == 0
    plt.close(fig)


def test_head_plot_uses_snapshot_head_and_holds_during_idle():
    result = simulate([Request('D',DB,20,100)],initial_time=10,initial_head=70)
    fig = plots.head_plot(result)
    line = fig.axes[0].lines[0]
    assert line.get_xdata()[:3].tolist() == [10,20,21]
    assert line.get_ydata()[:3].tolist() == [70,70,70]
    assert line.get_ydata()[-1] == 100
    plt.close(fig)


def test_playback_axes_remain_stable():
    result = simulate([Request('D1',DB,0,60),Request('D2',DB,100,120)])
    for plot in (plots.head_plot,plots.timeline):
        first,complete = plot(result,0),plot(result)
        assert first.axes[0].get_xlim() == complete.axes[0].get_xlim()
        plt.close(first)
        plt.close(complete)


def test_queue_timestamps_within_tolerance_never_run_backwards():
    result = simulate([Request('A',DB,0,50),Request('B',DB,2+5e-10,60)])
    assert result.queues.time.is_monotonic_increasing
