from src.models import MM, DB, EPS

def calculate(result):
    df = result.dispatches
    if df.empty:
        return {'request_count': 0, 'makespan_ms': 0, 'total_head_movement': 0}
    mm, db = df[df.kind == MM], df[df.kind == DB]
    end = float(df.completion.max())
    duration = end-result.origin
    m = dict(request_count=len(df), total_head_movement=int(df.movement.sum()),
             makespan_ms=duration, request_throughput_per_ms=len(df)/duration,
             byte_throughput_per_ms=float(df['size'].sum()*1024/duration),
             backlog_at_final_arrival=int((df.completion > df.arrival.max()+EPS).sum()))
    for label, frame in [('overall', df), (MM, mm), (DB, db)]:
        for metric in ['waiting', 'response']:
            m[f'{label}_mean_{metric}_ms'] = float(frame[metric].mean()) if len(frame) else None
    for metric in ['waiting', 'response']:
        for stat in ['p95', 'max']:
            m[f'database_{stat}_{metric}_ms'] = float(db[metric].quantile(.95) if stat == 'p95' else db[metric].max()) if len(db) else None
    m['database_waiting_threshold_violation_ratio'] = float((db.waiting > result.config.aging+EPS).mean()) if len(db) else None
    m['multimedia_deadline_miss_ratio'] = float(mm.deadline_miss.astype(float).mean()) if len(mm) else None
    m['multimedia_mean_tardiness_ms'] = float(mm.tardiness.mean()) if len(mm) else None
    m['multimedia_p95_tardiness_ms'] = float(mm.tardiness.quantile(.95)) if len(mm) else None
    for label, frame in [(MM, mm), (DB, db)]:
        m[f'{label}_request_share'] = len(frame)/len(df) if len(frame) else None
        m[f'{label}_disk_time_share'] = float(frame.service.sum()/df.service.sum()) if len(frame) else None
    ctrl = result.controller
    for mode in ['balanced', 'database-protection', 'multimedia-pressure']:
        m[f'batches_{mode}'] = int((ctrl['mode'] == mode).sum()) if len(ctrl) else 0
    m['quota_changes'] = int(ctrl.multimedia_quota.diff().dropna().ne(0).sum()) if len(ctrl) else 0
    return m
