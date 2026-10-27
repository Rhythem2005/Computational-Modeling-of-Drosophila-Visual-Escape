"""Local evidence I/O and explicit limits for the authorized engineering study."""
import hashlib
import json
import os
from pathlib import Path
import resource
import time

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = 'fly_behavior_neutral_fixture_v1'
MAX_EPISODES = 182
MAX_BYTES = 2 * 1024**3
MAX_RSS = 4 * 1024**3

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def read(path):
    return json.loads(Path(path).read_text())

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()

def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name+'.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    os.replace(tmp, path)

def sources():
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(Path(__file__).parent.rglob('*.py'))}

def inventory(root):
    result = {}
    for base in ('connectome/Results', 'connectome/scripts'):
        for p in (root/base).rglob('*'):
            if (p.is_file() and 'behavior_validation' not in p.relative_to(root/base).parts
                    and not {'__pycache__', '.pytest_cache'}.intersection(p.parts)):
                result[str(p.relative_to(root))] = sha(p)
    for name in ('README.md', 'config.yaml', 'requirements.txt', 'STUDY_CHECKPOINT.md'):
        if (root/name).exists():
            result[name] = sha(root/name)
    return result

def rss():
    # macOS ru_maxrss is bytes; Linux reports KiB.
    import sys
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == 'darwin' else value*1024)

def size(path):
    return sum(p.stat().st_size for p in Path(path).rglob('*') if p.is_file())

class Budget:
    def __init__(self, output, seconds):
        self.output = Path(output)
        self.started = time.monotonic()
        self.seconds = seconds
        self.attempts = 0
        self.last_disk_check = -float('inf')

    def check(self):
        if time.monotonic()-self.started > self.seconds:
            raise RuntimeError('WALL_TIME_BUDGET_EXCEEDED')
        if rss() > MAX_RSS:
            raise RuntimeError('RSS_BUDGET_EXCEEDED')
        if time.monotonic()-self.last_disk_check >= 1:
            if size(self.output) + size(ROOT) > MAX_BYTES:
                raise RuntimeError('ARTIFACT_AND_SNAPSHOT_BUDGET_EXCEEDED')
            self.last_disk_check = time.monotonic()

    def begin_episode(self):
        self.check()
        if self.attempts >= MAX_EPISODES:
            raise RuntimeError('EPISODE_BUDGET_EXCEEDED')
        self.attempts += 1
