"""Phase 10 paths, immutable artifact I/O and frozen design access."""
import hashlib
import json
from pathlib import Path
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'connectome/Results/phase10'
OUT = BASE / 'results'
VERSION = '1.0.0'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def write_json(path, value, *, immutable=False):
    path = Path(path)
    if not path.resolve().is_relative_to(BASE.resolve()):
        raise ValueError('Phase 10 output must stay within Phase 10')
    data = json.dumps(value, indent=2, allow_nan=False) + '\n'
    if immutable and path.exists() and path.read_text() != data:
        raise ValueError(f'Recorded definition/artifact changed: {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data)


def save_arrays(path, **arrays):
    path = Path(path)
    if not path.resolve().is_relative_to(BASE.resolve()):
        raise ValueError('Output escapes Phase 10')
    if path.exists():
        with np.load(path, allow_pickle=False) as old:
            if set(old.files) != set(arrays) or any(old[k].dtype != v.dtype or not np.array_equal(old[k], v) for k,v in arrays.items()):
                raise ValueError(f'Numerical reproduction failed: {path}')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **arrays)


def config():
    c = yaml.safe_load((BASE / 'control_config.yaml').read_text())
    design = yaml.safe_load((ROOT / 'connectome/phase5_5/benchmark_design.yaml').read_text())
    e = design['evaluation']
    checks = {'version': VERSION, 'design_seed': design['seed'], 'null_count': e['shuffled_networks_per_control'],
              'hidden_units': e['nn_hidden_units'], 'training_seeds': e['nn_training_seeds'],
              'learning_rates': e['nn_learning_rates'], 'max_epochs': e['nn_max_epochs'],
              'patience': e['nn_early_stopping_patience'], 'gain': e['fixed_gain'],
              'tau_ms': e['fixed_tau_ms'], 'input_scale': e['fixed_input_scale'],
              'target_radius': e['secondary_spectral_radius_target'], 'mapping_seeds': e['input_mapping_seeds']}
    if any(c.get(k) != v for k,v in checks.items()):
        raise ValueError('Phase 10 configuration conflicts with frozen benchmark')
    if c['dt_ms'] != 1 or c['duration_ms'] != 1000 or c['persistence_ms'] != 20 or c['input_dimension'] != 321:
        raise ValueError('Timing/input contract mismatch')
    return c


def sources():
    files = [p for base in (BASE, ROOT / 'connectome/scripts/phase10') for p in base.rglob('*')
             if p.is_file() and 'results' not in p.relative_to(base).parts and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts]
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(files)}
