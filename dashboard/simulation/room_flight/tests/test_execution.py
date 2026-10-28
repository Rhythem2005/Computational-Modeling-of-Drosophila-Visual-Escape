import json
import pytest
from dashboard.simulation.room_flight import execution
from dashboard.simulation.avoidance.contracts import digest
from dashboard.simulation.room_flight.launch import approval

def test_durable_snapshot_is_verified_and_never_overwrites_changed_file(tmp_path,monkeypatch):
    old=tmp_path/'temporary';old.mkdir();(old/'source.py').write_text('immutable test dependency\n')
    root=tmp_path/'workspace';root.mkdir();record=tmp_path/'record.json';record.write_text(json.dumps(dict(path=str(old),files_sha256={'source.py':digest(old/'source.py')})))
    monkeypatch.setattr(execution,'ROOT',root)
    saved=execution.durable_snapshot(record);path=json.loads(saved.read_text())['path']
    from pathlib import Path
    target=Path(path)/'source.py';assert target.read_text()=='immutable test dependency\n'
    target.write_text('changed')
    with pytest.raises(ValueError):execution.durable_snapshot(record)

def test_exact_room_approval_cannot_be_inferred_from_implementation(tmp_path):
    protocol=tmp_path/'protocol.json';protocol.write_text('{}');a=tmp_path/'authorization.json'
    a.write_text(json.dumps(dict(status='APPROVED_IMPLEMENTATION',protocol_sha256=digest(protocol),episode_cap=24,training_authorized=False,held_out_authorized=False)))
    with pytest.raises(ValueError):approval(protocol,a)

def test_continuation_skips_failed_and_unresolved_reservations_without_retries(tmp_path):
    jobs=[dict(id=str(i),model='ordinary_motion',scene=str(i)) for i in range(4)]
    ledger=dict(protocol_sha256='unit',output=str(tmp_path),cap=24,elapsed_seconds=2,
        attempts=[dict(job=j,status=s) for j,s in zip(jobs,('COMPLETE','FAILED','RESERVED'))])
    assert execution.unattempted_jobs(jobs,ledger,'unit',tmp_path)==jobs[3:]
    ledger['attempts'].append(ledger['attempts'][0])
    with pytest.raises(ValueError):execution.unattempted_jobs(jobs,ledger,'unit',tmp_path)

def test_resource_block_preserves_state_without_reserving_or_spawning(tmp_path,monkeypatch,config,scene):
    import sys
    from types import SimpleNamespace
    from dashboard.simulation.room_flight import launch
    root=tmp_path;lock=root/'connectome/Results/phase11/results/manual_worker.lock';lock.parent.mkdir(parents=True);lock.touch()
    (root/'dashboard/runs').mkdir(parents=True)
    protocol=root/'protocol.json';protocol.write_text('{}');snapshot=root/'snapshot.json';snapshot.write_text('{}')
    monkeypatch.setattr(launch,'ROOT',root)
    monkeypatch.setattr(launch,'load_protocol',lambda _: (dict(neural_diagnostic=False,max_output_bytes=1000,max_stage_seconds=10),config(),[scene()]))
    monkeypatch.setattr(launch,'approval',lambda *args: {})
    monkeypatch.setattr(launch,'protected_fingerprints',lambda: {'unit':'unchanged'})
    monkeypatch.setattr(launch,'durable_snapshot',lambda _:snapshot)
    monkeypatch.setattr(launch.time,'sleep',lambda _:None)
    monkeypatch.setitem(sys.modules,'connectome.scripts.phase11.runtime',SimpleNamespace(sample=lambda:{},assess=lambda *args:['UNIT_RESOURCE_BLOCK']))
    def forbidden(*args,**kw):raise AssertionError('No worker may spawn before resource approval')
    monkeypatch.setattr(launch.subprocess,'run',forbidden)
    args=SimpleNamespace(protocol=protocol,authorization=None,snapshot_record=snapshot,live=False,continue_record=None)
    with pytest.raises(RuntimeError,match='UNIT_RESOURCE_BLOCK'):launch.launch(args)
    run=next((root/'dashboard/runs').iterdir())
    assert json.loads((run/'startup_status.json').read_text())['new_reserved_attempts']==0
    assert json.loads((run/'preservation.json').read_text())['scientific_sources_and_checkpoint_pointers_unchanged']
    assert not (root/'dashboard/.runtime/room_budgets').exists()
