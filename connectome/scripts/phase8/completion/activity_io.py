"""Completed action schema; does not overwrite the provisional checkpoint."""
import json
import platform
import sys
from pathlib import Path
import numpy as np
from connectome.scripts.phase5.config import validate_id
from .evidence import BASE, write_json, file_hash


def save_action(directory, episode_id, decoded, steering, action, provenance, *, overwrite=False):
    validate_id(episode_id)
    directory = Path(directory).resolve()
    if not directory.is_relative_to(BASE.resolve()):
        raise ValueError("Completed action output must remain inside Phase 8 completion")
    paths = [directory / f"{episode_id}{suffix}" for suffix in (".npz", "_action.json", "_metadata.json")]
    if not overwrite and any(p.exists() for p in paths):
        raise FileExistsError("Action exists; overwrite must be explicit")
    directory.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(paths[0], schema_version=np.array("1.2"), decoder_version=np.array("1.2.0"),
                        times_ms=decoded.times_ms, score=decoded.score, sustained_score=decoded.sustained_score,
                        eligible=decoded.eligible, escape_event=decoded.escape_event, escape_requested=decoded.escape_requested,
                        turn_command=steering["turn_command"], raw_dn_imbalance=steering["raw_dn_imbalance"],
                        dn_body_ids=decoded.dn_body_ids, dn_activity=decoded.dn_activity)
    write_json(paths[1], action)
    write_json(paths[2], dict(provenance=provenance, steering={k: v for k, v in steering.items() if not isinstance(v, np.ndarray)},
        action_sha256=file_hash(paths[1]), arrays_sha256=file_hash(paths[0]),
        invocation=[sys.executable, *sys.argv], environment=dict(python=platform.python_version(), numpy=np.__version__)))
    return paths
