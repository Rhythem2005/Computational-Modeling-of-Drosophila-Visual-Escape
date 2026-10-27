"""Exercise the actual parent launcher with a synthetic-only child substitution."""
import argparse
from pathlib import Path
import os
import shutil
import subprocess
import sys
from types import SimpleNamespace
from connectome.scripts.phase11 import launch,manual_stop
from connectome.scripts.phase11.common import ROOT


def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--pause',action='store_true');args=p.parse_args()
    canonical=args.directory/'canonical'
    workspace=args.directory/'copy'
    child_out=workspace/'connectome/Results/phase11/results'
    child_out.mkdir(parents=True,exist_ok=True)
    if canonical.exists():shutil.copytree(canonical,child_out,dirs_exist_ok=True)
    os.environ['PYTHONPATH']=str(ROOT)
    launch.OUT=canonical
    launch.protected=lambda:{}
    launch.snapshot=lambda:(workspace,0)
    original=subprocess.Popen
    def child(command,**kwargs):
        replacement=[sys.executable,'-B','-m','connectome.scripts.phase11.tests.manual_fixture',
                     '--directory',str(child_out/'fixture')]
        if args.pause:replacement+=['--pause','checkpoint_1']
        kwargs['env']=dict(kwargs['env'],FLY_FIXTURE_WORKER_OUT=str(child_out))
        return original(replacement,**kwargs)
    launch.subprocess.Popen=child
    with manual_stop.handlers():launch.run(SimpleNamespace(task='fixture'))


if __name__=='__main__':main()
