from dataclasses import dataclass
from pathlib import Path
import json
import os

@dataclass(frozen=True)
class Settings:
    project_root: Path
    origins: tuple[str, ...] = ('http://localhost:5173', 'http://127.0.0.1:5173', 'http://localhost:8000', 'http://127.0.0.1:8000', 'http://localhost:8001', 'http://127.0.0.1:8001')
    ingest_token: str = ''
    extra_sources: tuple[str, ...] = ()

    @classmethod
    def environment(cls):
        root = Path(os.environ.get('FLY_PROJECT_ROOT', str(Path(__file__).resolve().parents[3]))).resolve()
        return cls(root, tuple(os.environ.get('FLY_DASHBOARD_ORIGINS', ','.join(cls.origins)).split(',')),
                   os.environ.get('FLY_DASHBOARD_INGEST_TOKEN', ''),
                   tuple(json.loads(os.environ.get('FLY_DASHBOARD_EXTRA_SOURCES', '[]'))))

    def scientific_path(self, relative: str) -> Path:
        base = (self.project_root / 'connectome/Results').resolve()
        path = (self.project_root / relative).resolve()
        if not path.is_relative_to(base):
            raise ValueError('Source must stay inside connectome/Results')
        return path
