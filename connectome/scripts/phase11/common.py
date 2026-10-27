"""Phase 11-only atomic I/O and provenance; frozen parents are read-only."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'connectome/Results/phase11'
OUT = BASE / 'results'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def atomic(path, data):
    path = Path(path)
    if not path.resolve().is_relative_to(BASE.resolve()):
        raise ValueError('Phase 11 output escapes Phase 11')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write(path, value, immutable=False):
    data = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
    if immutable and Path(path).exists() and Path(path).read_bytes() != data:
        raise ValueError(f'Immutable Phase 11 artifact changed: {path}')
    atomic(path, data)


def arrays(path, **values):
    import io
    buffer = io.BytesIO()
    np.savez_compressed(buffer, **values)
    atomic(path, buffer.getvalue())


def raw_sources():
    files = list((ROOT/'connectome/scripts/phase11').rglob('*.py'))
    files += [BASE/'training_plan.md', BASE/'README.md']
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(files) if p.is_file()}


def sources():
    """Preserve checkpoint contracts across explicitly audited resource-only edits.

    Raw execution hashes remain in the certificate and resource evidence. No
    training, calibration, dataset or other source changes are interchangeable.
    """
    actual = raw_sources()
    path = BASE/'repairs/battery_power_v1/source_compatibility.json'
    if not path.exists():
        return actual
    certificate = read(path)
    prior = certificate['checkpoint_sources_sha256']
    allowed = {'connectome/scripts/phase11/'+name for name in
               ('common.py', 'runtime.py', 'resources.py', 'launch.py', 'tests/test_manual_resume.py')}
    changed = {k for k in set(actual) | set(prior) if actual.get(k) != prior.get(k)}
    if (digest(prior) != '5d923b56111a97521dedbb09f40ff0ed1eb9ff43eae5aeb4c27a0939bbed7661'
            or actual != certificate['execution_sources_sha256'] or changed != allowed
            or certificate['scope'] != 'USER_AUTHORIZED_RESOURCE_AND_PUBLICATION_REPAIR_ONLY'):
        raise ValueError('Unapproved source change outside audited operational repairs')
    return prior


def protected():
    paths = [p for p in (ROOT/'connectome').rglob('*') if p.is_file()
             and 'phase11' not in p.parts and not {'__pycache__', '.pytest_cache'}.intersection(p.parts)]
    paths += [ROOT/n for n in ('README.md', 'config.yaml', 'requirements.txt', 'STUDY_CHECKPOINT.md') if (ROOT/n).is_file()]
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(paths)}
