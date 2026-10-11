"""Evaluator-side dataset integrity; no metadata is passed to the encoder."""
import hashlib
import numpy as np
from connectome.scripts.phase5.loader import load_stimulus


def movie_hash(frames):
    # Include shape to avoid same-byte different-resolution ambiguity.
    h = hashlib.sha256(str(frames.shape).encode()+b"uint8-THW\0")
    h.update(np.ascontiguousarray(frames).tobytes())
    return h.hexdigest()


def check_isolation(records):
    ids,content,families = set(),{},{}
    for r in records:
        sid = r["scenario_id"]
        if sid in ids:
            raise ValueError("Duplicate scenario ID")
        ids.add(sid)
        key = (r["split"],r["cohort"])
        group = r["group_id"]
        if group in families and families[group] != key:
            raise ValueError("Family crosses a split/cohort boundary")
        families[group] = key
        sha = r["movie_sha256"]
        if sha in content:
            raise ValueError(f"Duplicate actual movie: {content[sha]} and {sid}")
        content[sha] = sid
    return dict(records=len(records),families=len(families),duplicate_movies=0,cross_split_families=0)


def encode_saved(encoder,data_dir,stimulus_id):
    frames,timestamps_s,_metadata,_config = load_stimulus(data_dir,stimulus_id)
    return encoder.encode(frames,timestamps_s)
