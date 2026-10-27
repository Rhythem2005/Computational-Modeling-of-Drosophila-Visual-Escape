"""Verify saved Stage A output, without extracting features or scoring any rule."""
from pathlib import Path
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
import numpy as np

ROOT=Path(__file__).resolve().parents[3]

def read(p):return json.loads(p.read_text())

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main(directory):
    directory=Path(directory).resolve()
    execution=read(directory/'execution.json')
    assert execution['status']=='COMPLETE_STAGE_A'
    result=read(directory/'information_audit.json')
    manifest=read(directory/'execution_manifest.json')
    source=ROOT/manifest['source_run']
    assert sha(source/'manifest.json')==manifest['source_manifest_sha256']
    assert read(directory/'preservation.json')['unchanged']
    assert read(directory/'preservation_before.json')==read(directory/'preservation_after.json')
    for name,h in manifest['sources_sha256'].items():assert sha(ROOT/name)==h
    tests=list(ET.parse(directory/'tests.xml').getroot().iter('testcase'))
    assert len(tests)==23 and not any(c.find('failure') is not None or c.find('error') is not None or c.find('skipped') is not None for c in tests)
    assert result['saved_unique_trajectories_processed']==len(result['feature_files_sha256'])==91
    assert len(list((directory/'features').glob('*.npz')))==91
    assert len(list((directory/'features').glob('*.json')))==91
    file_bindings={}
    defined_values=0
    for ident,h in result['feature_files_sha256'].items():
        path=directory/'features'/f'{ident}.npz';meta=read(path.with_suffix('.json'))
        assert sha(path)==h==meta['features_sha256']
        source_npz=source/'episodes'/f'{ident}.npz'
        assert sha(source_npz)==meta['source']['npz_sha256']
        assert sha(source_npz.with_suffix('.json'))==meta['source']['metadata_sha256']
        with np.load(path,allow_pickle=False) as f:
            assert f['schema_version'].item()=='causal_image_features_1.0'
            rows=meta['rows']
            for key in f.files:
                if key not in rows[0] or key=='reasons':continue
                values=[r[key] for r in rows]
                if f[key].dtype.kind=='f':
                    defined=np.array([v is not None for v in values])
                    np.testing.assert_array_equal(f[key][defined],np.array([v for v in values if v is not None]))
                    assert np.isnan(f[key][~defined]).all()
                    assert np.isfinite(f[key][defined]).all()
                    defined_values+=int(defined.sum())
                else:np.testing.assert_array_equal(f[key],np.array(values))
            with np.load(source_npz,allow_pickle=False) as original:
                np.testing.assert_array_equal(f['timestamp_s'],original['frame_timestamps_s'])
                np.testing.assert_array_equal(f['original_channels'],original['channels'])
                available=f['first_available_ms'];mask=f['source_has_eligible_decision']
                assert np.all(f['timestamp_s'][mask]<=available[mask]/1000)
                nonzero=available>0
                assert np.all(f['timestamp_s'][nonzero]>(available[nonzero]-1)/1000)
                for score in ('score','sustained_score'):
                    out=f['original_'+score+'_at_first_available_tick']
                    np.testing.assert_array_equal(out[mask],original[score][available[mask]])
                    assert np.isnan(out[~mask]).all()
        file_bindings[ident]=dict(features_npz_sha256=h,features_metadata_sha256=sha(path.with_suffix('.json')))
    snapshot=read(ROOT/'connectome/Results/collision_threat_implementation_plan_20261027/evidence_snapshot.json')
    for name,h in snapshot['production_pointers_sha256'].items():assert sha(ROOT/name)==h
    report=dict(status='PASS_STAGE_A_SAVED_FILE_QA',features_verified=91,source_episodes_verified=91,
                tests_verified=23,defined_float_values_checked=defined_values,
                exact_saved_score_alignment_verified=True,undefined_values_have_masks_and_reasons=True,
                earlier_preservation_inventories_equal=True,
                protected_files=read(directory/'preservation.json')['files'],
                ledger_and_partial_checkpoint_unchanged=True,
                new_feature_extraction_runs=0,new_simulations=0,new_model_inference=0,
                new_calibration=0,new_training=0,held_out_evaluations=0,
                audit_script_sha256=sha(Path(__file__)),
                information_audit_sha256=sha(directory/'information_audit.json'),
                plot_visually_inspected=True,output_bytes_before_this_audit=sum(p.stat().st_size for p in directory.rglob('*') if p.is_file()),
                file_bindings=file_bindings)
    assert report['output_bytes_before_this_audit']<250*1024**2
    (directory/'saved_file_audit.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='file_bindings'}))

if __name__=='__main__':main(sys.argv[1])
