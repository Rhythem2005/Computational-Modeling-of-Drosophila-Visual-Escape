"""Fresh-process synthetic pause fixture; cannot load registered benchmark inputs."""
import argparse
from pathlib import Path
import time
import numpy as np
from connectome.scripts.phase11 import training,jobs,manual_stop
from connectome.scripts.phase11.common import write,read


def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--pause');p.add_argument('--early',action='store_true');args=p.parse_args()
    directory=args.directory;directory.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(184)
    from connectome.scripts.phase6.encoder import load_mapping
    dn=np.array(load_mapping()['channel_index'])<0;sets=[]
    for split in ('train','validation'):
        rows=[]
        for k in range(20):
            x=rng.uniform(0,.2,(24,321));x[:,dn]=0
            rows.append(dict(scenario_id=f'fixture_{split}_{k}',group_id=f'fixture_{split}_{k}',split=split,cohort=split,
                             label=k%2,role='looming' if k%2 else 'static_initial',inputs=x))
        sets.append(rows)
    path=directory/'ledger.json'
    rows=read(path) if path.exists() else [dict(definition=dict(job_id='fixture_'+str(rate),kind='gru_trial',
        mapping='uniform_population',seed=55100,rate=rate),status='NOT_STARTED') for rate in (.0003,.001)]
    write(path,rows)
    events=read(directory/'events.json') if (directory/'events.json').exists() else []
    def event(kind,job):
        events.append(dict(kind=kind,job_id=job));write(directory/'events.json',events)
    def wait(point):
        if args.pause!=point:return
        write(directory/'ready.json',dict(point=point))
        while not manual_stop.requested:time.sleep(.005)
    old_save=training.save_state;calls=0
    def save(*a,**kw):
        nonlocal calls
        old_save(*a,**kw);calls+=1;wait('checkpoint_'+str(calls))
    training.save_state=save
    old_train=training.train_trial;old_complete=jobs.completed_trial
    def train(train,val,seed,rate,folder,inputs):
        event('TRAIN_OR_RESUME_CALLED',folder.name)
        return old_train(train,val,seed,rate,folder,inputs,smoke=True,smoke_epochs=30 if args.early else 3,smoke_start=8)
    jobs.train_trial=train
    jobs.completed_trial=lambda *a,**kw:old_complete(*a,**kw,smoke=True)
    jobs.OUT=directory
    def update(items,job_id,status,**details):
        if status=='COMPLETE' and job_id==rows[0]['definition']['job_id']:
            wait('before_registration');manual_stop.boundary()
        row=next(r for r in items if r['definition']['job_id']==job_id)
        row.update(status=status,**details);write(path,items);event(status,job_id)
        if status=='COMPLETE' and job_id==rows[0]['definition']['job_id']:
            wait('between_trials');manual_stop.boundary()
    jobs.update=update
    if args.early:
        from connectome.scripts.phase10.gru import GRU
        original=GRU.loss
        GRU.loss=lambda self,x,y,window_start=200,gradient=False:original(self,x,y,window_start,gradient) if gradient else 1.
    with manual_stop.handlers():
        import os
        if os.environ.get('FLY_FIXTURE_WORKER_OUT'):
            write(Path(os.environ['FLY_FIXTURE_WORKER_OUT'])/'worker_ready.json',
                  dict(invocation=os.environ.get('FLY_PHASE11_INVOCATION'),pid=os.getpid()))
        try:jobs.selected_gru('uniform_population',55100,*sets,dict(mapping='synthetic_fixture'),rows)
        except manual_stop.Paused:
            write(directory/'paused.json',dict(status='PAUSED_CHECKPOINT_COMMITTED'))
            raise SystemExit(130)
    write(directory/'done.json',dict(status='COMPLETE_SYNTHETIC_FIXTURE_ONLY'))


if __name__=='__main__':main()
