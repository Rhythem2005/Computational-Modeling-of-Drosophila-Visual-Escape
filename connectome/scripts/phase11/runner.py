"""Explicit sequential Phase 11A gates; no held-out execution entry point."""
import argparse
import traceback
from .common import OUT, write, read, sources


def main():
    import os
    from .manual_stop import handlers,Paused
    with handlers(watch_parent=True):
        write(OUT/'worker_ready.json',dict(invocation=os.environ.get('FLY_PHASE11_INVOCATION'),pid=os.getpid()))
        try:
            run()
        except Paused:
            write(OUT/'pause.json',dict(status='PAUSED_CHECKPOINT_COMMITTED',held_out_inference_runs=0))
            raise SystemExit(130)


def run():
    p = argparse.ArgumentParser()
    p.add_argument('--task', required=True)
    args = p.parse_args()
    try:
        if args.task == 'integrity':
            from .integrity import verify
            result = verify()
            print('Gate A PASS:', result['schedule'], flush=True)
        elif args.task == 'engineering':
            if read(OUT/'gate_A.json')['status'] != 'PASS':
                raise ValueError('Gate A required')
            from .engineering import verify
            verify()
        elif args.task=='preflight':
            from .runtime import check
            result=check(read(OUT/'gate_C.json')['conservative_disk_allowance_bytes'])
            print('Live resource preflight:',result['status'],result['blockers'],flush=True)
        elif args.task in ('profile', 'primary', 'secondary', 'freeze','continuous'):
            engineering = read(OUT/'gate_B.json')
            if engineering['status'] != 'PASS' or engineering['phase11_sources_sha256'] != sources():
                raise ValueError('Passing Gate B for current sources required')
            from .resources import profile
            from .jobs import execute, ledger, verify_freeze
            if args.task == 'profile':
                profile()
            else:
                resource_gate=read(OUT/'gate_C.json')
                if resource_gate['status'] != 'PASS' or resource_gate.get('phase11_sources_sha256')!=sources():
                    raise ValueError('Resource Gate C required before benchmark execution')
                from .runtime import check
                if check(resource_gate['conservative_disk_allowance_bytes'])['status']!='PASS':
                    raise ValueError('Current resource preflight failed; no jobs launched')
                if args.task=='continuous':
                    from .manual_stop import boundary
                    for primary,filename in ((True,'gate_D.json'),(False,'gate_E.json')):
                        boundary()
                        existing=read(OUT/filename) if (OUT/filename).exists() else {}
                        if existing.get('status')!='PASS' or existing.get('phase11_sources_sha256')!=sources():
                            write(OUT/filename,dict(execute(primary),phase11_sources_sha256=sources()))
                    finish_freeze()
                    return
                if args.task == 'primary':
                    write(OUT/'gate_D.json', dict(execute(True),phase11_sources_sha256=sources()))
                elif args.task == 'secondary':
                    if read(OUT/'gate_D.json')['status'] != 'PASS':
                        raise ValueError('Gate D required')
                    write(OUT/'gate_E.json', dict(execute(False),phase11_sources_sha256=sources()))
                else:
                    finish_freeze()
        else:
            raise ValueError('Gate not yet implemented')
    except Exception as error:
        write(OUT/f'failure_{args.task}.json', dict(status='FAILED_GATE', task=args.task,
              error=str(error), traceback=traceback.format_exc(), held_out_inference_runs=0))
        raise


def finish_freeze():
    from .jobs import ledger,verify_freeze
    from .common import ROOT
    from .manual_stop import boundary
    rows=ledger()
    if len(rows)!=936 or any(r['status']!='COMPLETE' for r in rows):
        raise ValueError('Incomplete registered training/calibration coverage')
    for row in rows:
        boundary()
        if row['definition']['kind']=='calibration':verify_freeze(ROOT/row['freeze'])
    write(OUT/'gate_F.json',dict(status='PASS',training_trials=120,calibration_conditions=816,held_out_inference_runs=0))


if __name__ == '__main__':
    main()
