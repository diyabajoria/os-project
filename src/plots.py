"""Publication-friendly Matplotlib charts derived only from trace/event data."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, PercentFormatter
import pandas as pd
from src.models import MM, DB

COLORS = {MM:'#6377df', DB:'#20a38b'}
plt.rcParams.update({
    'axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,
    'figure.facecolor':'#ffffff','axes.facecolor':'#ffffff','font.size':9,
    'text.color':'#42516a','axes.labelcolor':'#7c879b','xtick.color':'#7c879b',
    'ytick.color':'#7c879b','axes.edgecolor':'#e4e8f0','grid.color':'#edf0f5',
    'axes.titleweight':'bold','axes.titlesize':11,'legend.frameon':False,
    'xtick.major.size':0,'ytick.major.size':0,'axes.labelpad':9,
})

def canvas(size=(10,3.2)):
    fig,ax = plt.subplots(figsize=size)
    ax.set_axisbelow(True)
    ax.grid(axis='y',linewidth=.7)
    return fig,ax


def head_plot(result,limit=None):
    df = result.dispatches if limit is None else result.dispatches.iloc[:limit]
    fig,ax = canvas()
    initial = result.dispatches.iloc[0].head_from if len(result.dispatches) else result.disk.initial_head
    x,y = [result.origin],[initial]
    for r in df.itertuples():
        x.extend([r.start,r.start+result.disk.overhead,r.start+result.disk.overhead+r.movement*result.disk.seek,r.completion])
        y.extend([r.head_from,r.head_from,r.track,r.track])
    for kind in (MM,DB):
        if len(df):
            selected = df[df.kind == kind]
            ax.scatter(selected.completion,selected.track,color=COLORS[kind],s=14,zorder=3)
    ax.plot(x,y,color='#6377df',linewidth=1.4)
    if len(x)>1: ax.fill_between(x,y,alpha=.045,color='#6377df')
    ax.set(xlabel='Simulated time (ms)',ylabel='Head track',ylim=(-1,result.disk.tracks))
    # Fixed axes make playback steps comparable and keep a zero-step view useful.
    end = result.dispatches.completion.max() if len(result.dispatches) else result.origin+1
    ax.set_xlim(result.origin,max(result.origin+1,end))
    fig.tight_layout()
    return fig


def timeline(result,limit=None):
    df = result.dispatches if limit is None else result.dispatches.iloc[:limit]
    fig,ax = canvas((10,2.6))
    for index,kind in enumerate((MM,DB)):
        segments = [(r.start,r.service) for r in df.itertuples() if r.kind == kind]
        ax.broken_barh(segments,(index-.28,.56),facecolors=COLORS[kind],edgecolors='white',linewidth=.3)
    ax.grid(False)
    ax.set(yticks=[0,1],yticklabels=['Multimedia','Database'],xlabel='Simulated time (ms)',ylim=(-.65,1.65))
    end = result.dispatches.completion.max() if len(result.dispatches) else result.origin+1
    ax.set_xlim(result.origin,max(result.origin+1,end))
    fig.tight_layout()
    return fig


def queue_plot(result):
    fig,ax = canvas()
    for kind in (MM,DB):
        if len(result.queues):
            ax.step(result.queues.time,result.queues[kind],where='post',label=kind.capitalize(),color=COLORS[kind],linewidth=1.5)
    ax.set(xlabel='Simulated time (ms)',ylabel='Queued requests')
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    if len(result.queues): ax.legend(loc='upper left',ncol=2)
    fig.tight_layout()
    return fig


def mode_plot(result):
    fig,ax = canvas((10,2.8))
    modes = ['balanced','multimedia-pressure','database-protection']
    if not result.controller.empty:
        x = result.controller.time.tolist()+[result.dispatches.completion.max()]
        y = [modes.index(m) for m in result.controller['mode']]
        ax.step(x,y+[y[-1]],where='post',color='#6377df',marker='.',markersize=5,linewidth=1.5)
    else:
        ax.text(.5,.5,'This policy has no batch controller.',ha='center',va='center',transform=ax.transAxes,color='#7c879b')
    ax.set(yticks=range(3),yticklabels=['Balanced','Multimedia pressure','Database protection'],xlabel='Simulated time (ms)',ylim=(-.3,2.3))
    fig.tight_layout()
    return fig


def comparison(frame,columns,title,ylabel):
    """Missing-class metrics stay N/A and never become a zero-valued bar."""
    from src.ui import metric_label
    fig,ax = canvas((8,3.8))
    values = frame[columns].apply(pd.to_numeric,errors='coerce')
    palette = ['#6377df','#20a38b','#bd8454','#9275c0']
    width = .7/max(1,len(columns))
    for j,column in enumerate(columns):
        positions = [i-.35+width/2+j*width for i in range(len(frame))]
        valid = values[column].notna()
        ax.bar([x for x,ok in zip(positions,valid) if ok],values.loc[valid,column],width=width*.88,
               label=metric_label(column),color=palette[j%len(palette)],zorder=2)
        for x,value in zip(positions,values[column]):
            if pd.isna(value):
                ax.text(x,.025,'N/A',ha='center',va='bottom',fontsize=8,color='#8995a8',transform=ax.get_xaxis_transform())
    ax.set_xticks(range(len(frame)),frame.index,rotation=28,ha='right')
    ax.set_xlim(-.6,max(.6,len(frame)-.4))
    ax.set(title=title,ylabel=ylabel)
    ax.set_ylim(bottom=0)
    if values.isna().all().all(): ax.set_ylim(0,1)
    if all('ratio' in column for column in columns):
        ax.yaxis.set_major_formatter(PercentFormatter(1))
        ax.set_ylim(0,min(1,max(.1,float(values.max().max())*1.2))) if values.notna().any().any() else ax.set_ylim(0,1)
    if len(columns)>1: ax.legend(loc='upper left',fontsize=8)
    fig.tight_layout()
    return fig


def arrival_plot(requests):
    fig,ax = canvas((8,2.65))
    for kind in (MM,DB):
        queue = [r for r in requests if r.kind==kind]
        ax.scatter([r.arrival for r in queue],[r.track for r in queue],s=18,alpha=.8,color=COLORS[kind],edgecolors='none')
    ax.set(xlabel='Arrival time (ms)',ylabel='Requested track')
    fig.tight_layout()
    return fig
