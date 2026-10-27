"""Post-run saved-file QA and explicit sensory-domain reporting; no inference."""
from pathlib import Path
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
import numpy as np

def read(p):
    return json.loads(p.read_text())

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main(directory):
    directory=Path(directory).resolve()
    plan=read(directory/'manifest.json')
    summary=read(directory/'summary.json')
    assert read(directory/'execution.json')['exit_code']==0
    assert read(directory/'preservation.json')['unchanged']
    assert read(directory/'preservation_before.json')==read(directory/'preservation_after.json')
    assert summary['manifest_sha256']==sha(directory/'manifest.json')
    cases=list(ET.parse(directory/'checks.xml').getroot().iter('testcase'))
    assert len(cases)==30 and not any(c.find('failure') is not None or c.find('error') is not None or c.find('skipped') is not None for c in cases)
    assert len(plan['jobs'])==summary['attempts']==182
    assert len(list((directory/'episodes').glob('*.npz')))==182
    assert len(list((directory/'episodes').glob('*.json')))==182
    unique={}
    for job in plan['jobs']:
        ident=job['episode_id']
        meta=read(directory/'episodes'/f'{ident}.json')
        npz=directory/'episodes'/f'{ident}.npz'
        assert sha(npz)==meta['arrays_sha256']
        with np.load(npz,allow_pickle=False) as f:
            assert f['schema_version'].item()=='behavior_1.0'
            if job['repeat']==1:
                with np.load(directory/'episodes'/f'{ident[:-1]}0.npz',allow_pickle=False) as first:
                    assert set(f.files)==set(first.files)
                    for key in f.files:
                        np.testing.assert_array_equal(f[key],first[key])
                assert meta['metrics']==read(directory/'episodes'/f'{ident[:-1]}0.json')['metrics']
                continue
            frames=f['frames'];time=f['frame_timestamps_s']
            border=np.concatenate((frames[:,0,:],frames[:,-1,:],frames[:,:,0],frames[:,:,-1]),axis=1)
            # Explicit geometric-image clipping uses the known renderer background,
            # distinct from the encoder's modal-background validity decision.
            clipped=np.any(border!=meta['config']['background_uint8'],axis=1)
            cap=np.any(f['channels']>=1,axis=1)
            multi=f['projected_objects']>1
            near=f['near_or_behind']>0
            validity=f['frame_valid']
            first=meta['metrics']['first_request_ms']
            pre=np.ones(len(time),dtype=bool) if first is None else time<=first/1000
            np.testing.assert_equal(float(validity.mean()),meta['metrics']['encoder_valid_fraction'])
            unique[ident]=dict(frame_timestamps_ms=(time*1000).tolist(),
                encoder_valid=validity.tolist(),projected_image_touches_border=clipped.tolist(),
                normalized_channel_at_cap=cap.tolist(),multiple_projected_objects=multi.tolist(),
                near_or_behind=near.tolist(),at_or_before_request=pre.tolist(),
                frame_count=len(time),valid_frames=int(validity.sum()),
                clipped_frames=int(clipped.sum()),capped_frames=int(cap.sum()),
                multiple_projection_frames=int(multi.sum()),near_or_behind_frames=int(near.sum()),
                pre_request_clipped_frames=int(clipped[pre].sum()),
                conditionally_valid_subset_only=not bool(validity.all()))
    assert len(unique)==91
    result=dict(status='PASS_SAVED_FILE_QA',new_simulations=0,new_neural_inference=0,
                episodes_hash_verified=182,exact_repeats_independently_verified=91,
                test_cases_verified=30,manifest_sha256=sha(directory/'manifest.json'),
                protected_files=read(directory/'preservation.json')['files'],
                original_preservation_inventories_equal=True,
                audit_script_sha256=sha(Path(__file__)),unique_episode_sensory_diagnostics=unique,
                note='All episodes remain included. Clipping/capping are diagnostics, never new exclusions or calibration.')
    (directory/'saved_file_audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='unique_episode_sensory_diagnostics'}))

if __name__=='__main__':
    main(sys.argv[1])
