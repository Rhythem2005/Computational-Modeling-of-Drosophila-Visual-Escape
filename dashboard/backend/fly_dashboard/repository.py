"""Saved scientific artifacts only. No imports of simulator or training modules."""
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
import csv
import hashlib
import io
import json
import math
import struct
import threading
import zlib
import numpy as np
from .config import Settings

SUPPORTED = {'1.0', 'behavior_1.0', 'collision_threat_1.0', 'collision_threat_2.0', 'multi_object_1.0', 'room_flight_1.0'}
TRACE_KEYS = ('score', 'sustained_score', 'eligible', 'escape_event', 'escape_requested', 'legacy_score',
              'legacy_sustained_score', 'legacy_escape_event', 'legacy_escape_requested', 'rule_state',
              'rule_reason', 'gate_state', 'candidate_epoch', 'retirement_event', 'rearm_event',
              'fallback_event', 'unknown_after_retirement', 'physical_reason', 'current_clear_sustained',
              'current_threat_sustained', 'turn_command')

def read(path):
    with Path(path).open() as stream:
        return json.load(stream)

def digest_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def safe_json(value):
    if isinstance(value, np.ndarray): return safe_json(value.tolist())
    if isinstance(value, np.generic): return safe_json(value.item())
    if isinstance(value, float): return value if math.isfinite(value) else None
    if isinstance(value, dict): return {str(k): safe_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [safe_json(v) for v in value]
    return value

def png_gray(pixels):
    pixels = np.ascontiguousarray(pixels, dtype=np.uint8)
    if pixels.ndim not in (2,3) or (pixels.ndim==3 and pixels.shape[2]!=3):raise ValueError('Expected grayscale or RGB pixels')
    height, width = pixels.shape[:2]
    color_type=0 if pixels.ndim==2 else 2
    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data) & 0xffffffff)
    rows = b''.join(b'\x00' + row.tobytes() for row in pixels)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', width, height, 8, color_type, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(rows, 5)) + chunk(b'IEND', b'')

@dataclass
class Episode:
    id: str
    metadata_path: Path
    arrays_path: Path
    metadata: dict
    public: dict
    stamp: tuple

class Repository:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.episodes: dict[str, Episode] = {}
        self.diagnostics: list[dict] = []
        self.cache = OrderedDict()
        self.lock = threading.RLock()
        self.graph_cache = None

    def _paths(self):
        root = self.settings.project_root / 'connectome/Results'
        patterns = ('phase9/results/episodes/*_metadata.json', 'behavior_validation/*/episodes/*.json',
                    'collision_threat_v1/prototype/*/episodes/*.json', 'collision_threat_v2/runs/*/episodes/*.json')
        for pattern in patterns:
            yield from root.glob(pattern)
        yield from (self.settings.project_root / 'dashboard/runs').glob('*/episodes/*.json')
        for source in self.settings.extra_sources:
            folder = self.settings.scientific_path(source)
            yield from folder.glob('*.json')

    def _describe(self, path):
        results = (self.settings.project_root / 'connectome/Results').resolve()
        path = path.resolve()
        demo = (self.settings.project_root / 'dashboard/runs').resolve()
        if not (path.is_relative_to(results) or path.is_relative_to(demo)): raise ValueError('Source symlink escapes approved recording roots')
        legacy = path.name.endswith('_metadata.json')
        name = path.name.removesuffix('_metadata.json') if legacy else path.stem
        arrays = path.parent / f'{name}.npz'
        if not arrays.is_file(): return None
        metadata = read(path)
        if legacy:
            config = read(path.parent / f'{name}_config.json')
            metrics = read(path.parent / f'{name}_metrics.json')
            metadata = dict(metadata, config=config['world'], scenario=config['scenario'], metrics=metrics,
                            model='circuit', controller_state_kind='anatomical_neurons_321',
                            threshold=read(path.parent / f'{name}_action.json').get('threshold'))
        if not all(k in metadata for k in ('arrays_sha256', 'config', 'scenario', 'metrics')): return None
        if not isinstance(metadata['arrays_sha256'], str) or len(metadata['arrays_sha256']) != 64:
            raise ValueError('Missing SHA-256 array binding')
        relative = str(path.relative_to(self.settings.project_root))
        identifier = hashlib.sha256(relative.encode()).hexdigest()[:24]
        family = 'phase9' if legacy else 'v2' if 'collision_threat_v2' in relative else 'v1' if 'collision_threat_v1' in relative else 'behavior'
        m = metadata['metrics']
        experiment = str(path.parent.parent.relative_to(results if path.is_relative_to(results) else self.settings.project_root))
        public = dict(id=identifier, name=name, family=family, experiment=experiment,
                      scenario=metadata['scenario']['scenario_id'], model=metadata.get('model', m.get('model', 'circuit')),
                      repeat=1 if name.endswith('_r1') else 0, duration_ms=m.get('end_ms', metadata['config']['duration_ms']),
                      danger=m.get('danger'), escape_success=m.get('escape_success'), false_alarm=m.get('false_alarm'),
                      request_ms=m.get('first_request_ms'), failure=m.get('failure'),
                      mapping=str(metadata.get('mapping', metadata.get('condition', m.get('condition', 'uniform_population')))),
                      mapping_seed=metadata.get('seed', m.get('seed')),
                      source=relative, expected_sha256=metadata['arrays_sha256'], mode='saved_replay')
        stamp = (path.stat().st_mtime_ns, arrays.stat().st_mtime_ns, arrays.stat().st_size)
        return Episode(identifier, path, arrays, metadata, public, stamp)

    def refresh(self):
        found = {}; errors = []
        for path in sorted(set(self._paths())):
            try:
                episode = self._describe(path)
                if episode: found[episode.id] = episode
            except (ValueError, KeyError, OSError, TypeError) as error:
                errors.append(dict(source=str(path.relative_to(self.settings.project_root)), error=str(error)))
        with self.lock:
            self.episodes = found
            self.diagnostics = errors[:30]
            for key in list(self.cache):
                if key not in found or self.cache[key][0] != found[key].stamp: self.cache.pop(key)
        return self.catalog()

    def catalog(self):
        with self.lock:
            rows = [e.public for e in self.episodes.values()]
        rank = {'v2': 0, 'v1': 1, 'behavior': 2, 'phase9': 3}
        rows.sort(key=lambda e: (rank[e['family']], e['repeat'], e['scenario'] != 'world_head_on',
                                e['model'] != 'finite_retirement_gate_v2', e['experiment'], e['name']))
        return dict(episodes=rows, diagnostics=self.diagnostics, source_count=len(rows),
                    policy='Only committed metadata/NPZ pairs; arrays verified when opened; no held-out cohorts scanned')

    def graph(self):
        with self.lock:
            if self.graph_cache is not None: return self.graph_cache
        base = self.settings.project_root / 'connectome/Results/phase3'
        info = read(base / 'circuit_v2.json')
        with (base / 'circuit_v2_nodes.csv').open() as f:
            nodes = [dict(id=int(r['bodyId']), type=r['type'], side=r['side'], population=r['population'], role=r['role']) for r in csv.DictReader(f)]
        with (base / 'circuit_v2_edges.csv').open() as f:
            edges = [dict(source=int(r['bodyId_pre']), target=int(r['bodyId_post']), weight=int(r['weight']),
                          normalized=float(r['weight_normalized']), category=r['edge_class']) for r in csv.DictReader(f)]
        ids = {n['id'] for n in nodes}
        if len(nodes) != info['total_nodes'] or len(edges) != info['total_edges'] or any(e['source'] not in ids or e['target'] not in ids for e in edges):
            raise ValueError('Connectome identity/coverage mismatch')
        payload = dict(nodes=nodes, edges=edges, circuit_id=info['circuit_id'], dataset=info['dataset'],
                       coordinate_semantics='Frontend schematic layout, not anatomical coordinates',
                       sha256=dict(nodes=digest_file(base/'circuit_v2_nodes.csv'), edges=digest_file(base/'circuit_v2_edges.csv')))
        with self.lock: self.graph_cache = payload
        return payload

    def status(self):
        base = self.settings.project_root / 'connectome/Results/phase11/results'
        try:
            ledger = read(base / 'job_ledger.json')
            counts = {kind: sum(r.get('status') == 'COMPLETE' and r['definition']['kind'] == kind for r in ledger) for kind in ('gru_trial', 'calibration')}
            pause = read(base / 'pause.json') if (base / 'pause.json').exists() else None
            training = dict(completed=counts['gru_trial'], planned=120, calibrated=counts['calibration'], calibration_planned=816,
                            saved_pause_record=pause, process_state='not_observed')
        except (OSError, ValueError, KeyError): training = None
        return dict(training=training, execution_policy='No scientific execution endpoints',
                    world='Planar, abstract units; rendered in 3D for observation',
                    limitations=['Known development fixtures only', 'Illustrative fly geometry; no biomechanics',
                                 'Schematic neural positions', 'Finite-body controller uses a fixed object-size prior'])

    def load(self, identifier):
        with self.lock:
            if identifier not in self.episodes: raise KeyError(identifier)
            episode = self.episodes[identifier]
            cached = self.cache.get(identifier)
            if cached and cached[0] == episode.stamp:
                self.cache.move_to_end(identifier); return cached[1]
        if digest_file(episode.arrays_path) != episode.metadata['arrays_sha256']:
            raise ValueError('Recorded NPZ hash does not match metadata; episode rejected')
        if episode.metadata_path.name.endswith('_metadata.json'):
            for name, expected in episode.metadata.get('files_sha256', {}).items():
                if Path(name).name != name or digest_file(episode.metadata_path.parent/name) != expected:
                    raise ValueError('Phase 9 artifact hash mismatch')
        with np.load(episode.arrays_path, allow_pickle=False) as f:
            if str(f['schema_version'].item()) not in SUPPORTED: raise ValueError('Unsupported replay schema')
            a = {k: f[k].copy() for k in f.files}
        for key in ('world_times_ms', 'fly_position', 'obstacle_positions', 'decision_times_ms', 'frames', 'frame_timestamps_s'):
            if key not in a: raise ValueError(f'Missing required replay field: {key}')
        wt = a['world_times_ms']; dt = a['decision_times_ms']; ft = a['frame_timestamps_s']
        if (wt.ndim != 1 or len(wt) < 1 or not np.isfinite(wt).all() or np.any(np.diff(wt) <= 0)
                or dt.ndim != 1 or not len(dt) or not np.isfinite(dt).all() or np.any(np.diff(dt) <= 0) or dt[-1] >= wt[-1]
                or ft.ndim != 1 or not len(ft) or not np.isfinite(ft).all() or np.any(np.diff(ft) <= 0) or ft[-1] > wt[-1]/1000):
            raise ValueError('Invalid/terminal replay clock')
        dimension=episode.metadata['config'].get('world_dimension',2)
        if type(dimension) is not int or dimension not in (2,3):raise ValueError('Unsupported world dimensions')
        if a['fly_position'].shape != (len(wt), dimension) or a['obstacle_positions'].shape != (len(wt), len(episode.metadata['scenario']['obstacles']), dimension):
            raise ValueError('World geometry dimensions differ from the scenario')
        if not np.isfinite(a['fly_position']).all() or not np.isfinite(a['obstacle_positions']).all():
            raise ValueError('Nonfinite world geometry')
        states = a.get('controller_states', a.get('states', np.empty((0, 0))))
        nt = a.get('controller_state_times_ms', a.get('neural_times_ms', np.empty(0)))
        width = states.shape[1] if states.ndim == 2 else 0
        if states.ndim != 2 or len(states) != len(nt) or not np.isfinite(states).all(): raise ValueError('Invalid state clock/values')
        ids = a.get('body_ids', np.empty(0, dtype=int))
        if 'frame_drive' in a and (a['frame_drive'].shape != (len(ft), len(ids)) or not np.isfinite(a['frame_drive']).all()):
            raise ValueError('Encoder drive identity/dimensions invalid')
        kind = 'anatomical' if width == 321 and len(ids) == 321 else 'gru_hidden' if width == 16 else 'unavailable'
        if kind == 'anatomical' and set(ids.tolist()) != {n['id'] for n in self.graph()['nodes']}:
            raise ValueError('Neural identities differ from the connectome')
        frames = a['frames']
        if frames.dtype != np.uint8 or frames.ndim not in (3,4) or (frames.ndim==4 and frames.shape[-1]!=3) or len(frames) != len(ft): raise ValueError('Unsupported camera frame schema')
        h, w = frames.shape[1:3]; columns = min(10, len(frames)); rows = math.ceil(len(frames)/columns)
        atlas = np.full((rows*h, columns*w,*frames.shape[3:]), 128, dtype=np.uint8)
        for i, frame in enumerate(frames): atlas[(i//columns)*h:(i//columns+1)*h, (i%columns)*w:(i%columns+1)*w] = frame
        metrics = episode.metadata['metrics']; events = []
        def event(time, kind, label):
            if time is not None and 0 <= float(time) <= float(wt[-1]): events.append(dict(time_ms=float(time), kind=kind, label=label))
        event(metrics.get('internal_request_ms'), 'internal', 'Circuit initiation')
        event(metrics.get('first_request_ms'), 'request', 'Physical escape request')
        event(metrics.get('scheduled_actuation_ms'), 'actuation', 'Actuation scheduled')
        event(metrics.get('first_motion_ms'), 'motion', 'First recorded displacement')
        for key, event_kind, label in (('retirement_event','retirement','Candidate retired'), ('rearm_event','rearm','Fresh threat re-armed'), ('fallback_event','fallback','Unknown-perception fallback')):
            if key in a:
                for time in dt[np.asarray(a[key], dtype=bool)]: event(time,event_kind,label)
        if metrics.get('failure'): event(metrics['failure']['time_ms'], metrics['failure']['kind'], metrics['failure']['kind'].title())
        events.sort(key=lambda e: (e['time_ms'], e['kind']))
        if 'events' in episode.metadata:events=episode.metadata['events']
        traces = {k: a[k] for k in TRACE_KEYS if k in a and len(a[k]) == len(dt)}
        payload = safe_json(dict(episode=episode.public, config=episode.metadata['config'], scenario=episode.metadata['scenario'],
            metrics=metrics, threshold=episode.metadata.get('threshold'), assumptions=episode.metadata.get('assumptions'),
            integrity=dict(status='sha256_verified', sha256=episode.metadata['arrays_sha256'], schema=str(a['schema_version'].item())),
            world=dict(times_ms=wt, fly=a['fly_position'], quaternion_xyzw=a.get('fly_quaternion_xyzw',[]), obstacles=a['obstacle_positions'], speed=a.get('speed', [])),
            neural=dict(kind=kind, times_ms=nt if kind != 'unavailable' else [], values=states if kind != 'unavailable' else [],
                        ids=ids if kind == 'anatomical' else [f'H{i:02}' for i in range(width)] if kind == 'gru_hidden' else []),
            decision=dict(times_ms=dt, traces=traces),
            encoder=dict(times_ms=ft*1000, channels=a.get('channels', []), drive=a.get('frame_drive', []), ids=ids,
                         valid=(a['frame_valid'] & a.get('frame_frozen_domain_valid',np.ones(len(ft),dtype=bool))) if 'frame_valid' in a else [], decision_frame_indices=a.get('decision_frame_indices', a.get('step_frame_indices', []))),
            measurements=dict(times_ms=a.get('measurement_timestamps_s', np.empty(0))*1000,
                values={k:a[k] for k in a if k.startswith(('measurement_', 'estimate_')) and k != 'measurement_timestamps_s'}),
            camera=dict(times_ms=ft*1000, width=w, height=h, columns=columns, count=len(frames),
                        atlas_url=f'/api/v1/episodes/{identifier}/camera.png',view_ids=[v['id'] for v in episode.metadata['config'].get('camera_rig',[])],mosaic_columns=3 if episode.metadata['config'].get('room_flight') else 1), events=events,
            duration_ms=float(wt[-1]), source_mode='verified_replay'))
        value = dict(payload=payload, camera_png=png_gray(atlas))
        with self.lock:
            self.cache[identifier] = (episode.stamp, value)
            while len(self.cache) > 3: self.cache.popitem(last=False)
        return value
