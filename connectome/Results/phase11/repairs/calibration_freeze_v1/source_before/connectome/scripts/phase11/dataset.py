"""Cache causal frame drives once per mapping, with no test-access option."""
from functools import lru_cache
import hashlib
import numpy as np
from connectome.scripts.phase10.data import TrainingDataset, manifest_rows, hold_spatial_drive, validate_coverage
from connectome.scripts.phase10.common import config
from .common import ROOT, OUT, read, write, arrays, sha, digest


class Dataset:
    def __init__(self, pipeline, mapping):
        if mapping not in ['uniform_population', *config()['mapping_seeds']]:
            raise ValueError('Unregistered mapping')
        self.pipeline = pipeline
        self.mapping = mapping
        self.directory = OUT/'inputs'/str(mapping)
        self.rows = {r['scenario_id']: r for r in manifest_rows()}
        self.loader = TrainingDataset(pipeline)
        self.index = {}
        self.fields = None
        if mapping != 'uniform_population':
            from connectome.scripts.phase8.completion.spatial import assign_fields
            self.fields = assign_fields(pipeline.encoder.mapping['nodes'], mapping)
            write(self.directory/'mapping.json', self.fields, immutable=True)
        self.contract = dict(mapping=mapping, mapping_sha256=digest(self.fields),
             manifest_sha256=sha(ROOT/'connectome/phase5_5/results/benchmark_manifest.json'),
             encoder_lock_sha256=sha(ROOT/'connectome/phase6/results/freeze_lock.json'))
        if (self.directory/'index.json').exists():
            saved = read(self.directory/'index.json')
            if saved['contract'] != self.contract:
                raise ValueError('Input cache contract changed')
            self.index = saved['records']

    def permitted(self, sid):
        row = self.rows.get(sid)
        if row is None or row['split'] not in ('train', 'validation') or row['cohort'] != row['split']:
            raise ValueError('Held-out input is forbidden before file access')
        return row

    def prepare(self):
        from connectome.scripts.phase5.generator import generate_stimulus
        from connectome.scripts.phase6.dataset import movie_hash
        from connectome.scripts.phase8.completion.spatial import frame_drive
        frozen_index = {r['scenario_id']: r for r in read(ROOT/'connectome/phase6/results/encoded_index.json')}
        movies = {r['scenario_id']: r for r in read(ROOT/'connectome/phase6/results/dataset_integrity.json')['records']}
        for sid, row in self.rows.items():
            if row['split'] not in ('train', 'validation'):
                continue
            from .manual_stop import boundary
            boundary()
            self.permitted(sid)
            path = self.directory/f'{sid}.npz'
            if sid in self.index:
                if sha(path) != self.index[sid]['sha256']:
                    raise ValueError(f'Cached input tampered: {sid}')
                continue
            encoded = self.pipeline.load_frozen_encoded(sid)
            oldpath = ROOT/'connectome/phase6'/frozen_index[sid]['path']
            with np.load(oldpath, allow_pickle=False) as old:
                valid = old['valid'].copy()
            drive = encoded.drive
            if self.fields is not None:
                frames, timestamps = generate_stimulus(row['config'])
                if movie_hash(frames) != movies[sid]['movie_sha256'] or hashlib.sha256(timestamps.tobytes()).hexdigest() != movies[sid]['timestamps_sha256']:
                    raise ValueError('Regenerated training/validation movie differs from frozen content')
                global_encoded, drive, _ = frame_drive(self.pipeline.encoder, frames, timestamps, self.fields)
                if not np.array_equal(global_encoded.channels, encoded.channels) or not np.array_equal(global_encoded.drive, encoded.drive):
                    raise ValueError('Spatial global encoder differs from frozen encoding')
                if not np.array_equal(global_encoded.diagnostics['valid'], valid):
                    raise ValueError('Spatial validity differs from frozen encoding')
            hold_spatial_drive(drive, encoded.timestamps_s, encoded.body_ids, self.pipeline)
            arrays(path, drive=drive, timestamps_s=encoded.timestamps_s, body_ids=encoded.body_ids, valid=valid)
            self.index[sid] = dict(sha256=sha(path), source_encoded_sha256=frozen_index[sid]['sha256'],
                 valid_frame_fraction=float(valid.mean()), invalid_frames=int((~valid).sum()),
                 encoder_channel_cap_fraction=float((encoded.channels >= 1).mean()),
                 input_max=float(drive.max()), input_min=float(drive.min()), failed=False)
            write(self.directory/'index.json', dict(contract=self.contract, records=self.index))
        expected = {r['scenario_id'] for r in self.rows.values() if r['split'] in ('train', 'validation')}
        if set(self.index) != expected:
            raise ValueError('Input cache coverage differs from allowed partitions')
        return dict(self.contract, cache_sha256=digest(self.index), clips=len(self.index))

    @lru_cache(maxsize=384)
    def frame_arrays(self, sid):
        self.permitted(sid)
        path = self.directory/f'{sid}.npz'
        if sha(path) != self.index[sid]['sha256']:
            raise ValueError('Cached input changed')
        with np.load(path, allow_pickle=False) as f:
            return f['drive'].copy(), f['timestamps_s'].copy(), f['body_ids'].copy()

    def load(self, sid):
        self.permitted(sid)
        return hold_spatial_drive(*self.frame_arrays(sid), self.pipeline)

    def records(self, split):
        if split not in ('train', 'validation'):
            raise ValueError('Forbidden partition')
        rows = [dict(**{k: r[k] for k in ('scenario_id', 'group_id', 'split', 'cohort', 'label', 'role')},
                     inputs=lambda sid=r['scenario_id']: self.load(sid))
                for r in self.rows.values() if r['cohort'] == split]
        validate_coverage(rows, split)
        return rows
