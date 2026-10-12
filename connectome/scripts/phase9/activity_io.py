"""Independent world episode schema; never overwrite earlier phase artifacts."""
from datetime import datetime, timezone
from pathlib import Path
import json
import platform
import sys
import numpy as np
from connectome.scripts.phase5.config import validate_id
from connectome.scripts.phase6.encoder import digest
from .config import BASE
from .evidence import file_hash, write_json


def save_episode(directory,episode_id,run,*,overwrite=False):
    validate_id(episode_id); directory=Path(directory).resolve()
    if not directory.is_relative_to(BASE.resolve()):
        raise ValueError("World output must stay in Phase 9")
    directory.mkdir(parents=True,exist_ok=True)
    paths=[directory / f"{episode_id}{suffix}" for suffix in (".npz","_config.json","_action.json","_metrics.json","_metadata.json")]
    if any(p.exists() for p in paths) and not overwrite:
        raise FileExistsError("Episode exists; overwrite must be explicit")
    arrays=dict(run["arrays"],schema_version=np.array("1.0"))
    if paths[0].exists():
        with np.load(paths[0],allow_pickle=False) as old:
            if set(old.files) != set(arrays) or any(old[k].dtype != v.dtype or not np.array_equal(old[k],v) for k,v in arrays.items()):
                raise ValueError("World numerical reproduction differs")
    else:
        np.savez_compressed(paths[0],**arrays)
    config=dict(world=run["config"],scenario=run["scenario"],simulation=run["simulation_config"],mapping=run["mapping"],calibration_sha256=run["calibration_sha256"])
    for path,data in zip(paths[1:4],(config,run["action"],run["metrics"])):
        if path.exists() and json.loads(path.read_text()) != data:
            raise ValueError(f"World recorded result changed: {path}")
        write_json(path,data)
    write_json(paths[4],dict(schema_version="1.0",protocol_id=run["config"]["protocol_id"],arrays_sha256=file_hash(paths[0]),
        config_sha256=digest(config),files_sha256={p.name:file_hash(p) for p in paths[:4]},
        units=dict(neural_time="ms",frame_time="s",world_position="abstract world units",speed="world units/s",activity="arbitrary model units",turn="normalized request [-1,1]"),
        endpoint_semantics="No decision after physical termination or at the 1s endpoint; diagnostic neural endpoint only if its full step completed",
        condition=run["metrics"]["condition"],seed=run["metrics"]["seed"],world_calibration_status=run["config"]["calibration_scope"],
        invocation=[sys.executable,*sys.argv],run_time_utc=datetime.now(timezone.utc).isoformat(),
        environment=dict(python=platform.python_version(),numpy=np.__version__)))
    loaded=load_episode(directory,episode_id)
    if any(not np.array_equal(loaded["arrays"][k],v) for k,v in arrays.items()):
        raise ValueError("Episode saved-array round trip differs")
    return paths


def load_episode(directory,episode_id):
    validate_id(episode_id); directory=Path(directory)
    metadata=json.loads((directory / f"{episode_id}_metadata.json").read_text())
    for name,value in metadata["files_sha256"].items():
        if Path(name).name != name or file_hash(directory/name) != value:
            raise ValueError("World artifact hash/path mismatch")
    with np.load(directory / f"{episode_id}.npz",allow_pickle=False) as saved:
        arrays={k:saved[k].copy() for k in saved.files}
    if arrays["schema_version"].item() != "1.0":
        raise ValueError("Unsupported world episode schema")
    return dict(arrays=arrays,metadata=metadata,config=json.loads((directory / f"{episode_id}_config.json").read_text()),
                action=json.loads((directory / f"{episode_id}_action.json").read_text()),metrics=json.loads((directory / f"{episode_id}_metrics.json").read_text()))
