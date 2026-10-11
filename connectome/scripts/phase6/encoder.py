"""Frame-only causal engineering proxy, not calibrated fly neural activity."""
from dataclasses import dataclass
from pathlib import Path
import csv
import hashlib
import json
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[3]
PHASE = ROOT / "connectome/phase6"
VERSION = "1.0.0"
CHANNELS = ["LC4_like", "LPLC2_like"]


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()


def load_config():
    return validate_config(yaml.safe_load((PHASE / "encoder_config.yaml").read_text()))


def validate_config(config):
    expected = {"encoder_version","schema_version","min_contrast_uint8","growth_window_s",
                "min_area_growth_px","min_relative_radius_growth","normalization_quantile","output_clip","mapping"}
    if not isinstance(config,dict) or set(config) != expected:
        raise ValueError("Incorrect encoder config fields")
    c = dict(config)
    if c["encoder_version"] != VERSION or c["schema_version"] != "1.0" or c["mapping"] != "uniform_population":
        raise ValueError("Unsupported encoder version/schema/mapping")
    if type(c["min_contrast_uint8"]) is not int or not 1 <= c["min_contrast_uint8"] <= 255:
        raise ValueError("Invalid contrast threshold")
    for key in ("growth_window_s","min_area_growth_px","min_relative_radius_growth","output_clip"):
        if isinstance(c[key],bool) or not np.isfinite(c[key]) or c[key] <= 0:
            raise ValueError(f"Invalid {key}")
    if not 0 < c["normalization_quantile"] <= 1 or c["output_clip"] != 1:
        raise ValueError("Invalid normalization quantile/output cap")
    return c


def validate_arrays(frames,timestamps_s):
    if not isinstance(frames,np.ndarray) or frames.dtype != np.uint8 or frames.ndim != 3 or min(frames.shape) < 1:
        raise ValueError("frames must be nonempty uint8 (T,H,W)")
    validate_time(timestamps_s,frames.shape[0])


def validate_time(timestamps_s,length):
    if not isinstance(timestamps_s,np.ndarray) or timestamps_s.dtype != np.float64 or timestamps_s.shape != (length,) or length < 1:
        raise ValueError("timestamps_s must be nonempty float64 (T,)")
    if not np.all(np.isfinite(timestamps_s)) or timestamps_s[0] < 0 or not np.all(np.diff(timestamps_s) > 0):
        raise ValueError("timestamps_s must be finite nonnegative strictly increasing seconds")


def extract_features(frames,timestamps_s,config):
    """Current frame segmentation and strictly backward-only growth statistics."""
    c = validate_config(config)
    validate_arrays(frames,timestamps_s)
    count = len(frames)
    areas = np.zeros(count,dtype=np.float64)
    contrast = np.zeros(count,dtype=np.float64)
    valid = np.zeros(count,dtype=bool)
    for k,frame in enumerate(frames):
        bins = np.bincount(frame.ravel(),minlength=256)
        bg = int(np.argmax(bins))
        delta = np.abs(frame.astype(np.int16)-bg)
        mask = delta >= c["min_contrast_uint8"]
        areas[k] = np.count_nonzero(mask)
        if areas[k]:
            contrast[k] = delta[mask].mean()/255
            border = mask[0].any() or mask[-1].any() or mask[:,0].any() or mask[:,-1].any()
            valid[k] = bins[bg] > frame.size/2 and not border
    radii = np.sqrt(areas/np.pi)
    # min(k-1, ...) makes the causal dependency explicit even for very small windows.
    anchors = np.minimum(np.arange(count)-1,np.searchsorted(timestamps_s,timestamps_s-c["growth_window_s"]+1e-12,side="right")-1)
    raw = np.zeros((count,2),dtype=np.float64)
    speed = np.zeros(count,dtype=np.float64)
    for k,j in enumerate(anchors):
        if j < 0 or not np.all(valid[j:k+1]):
            continue
        growth = radii[k]-radii[j]
        speed[k] = max(0,growth)/(timestamps_s[k]-timestamps_s[j])
        if areas[k]-areas[j] > c["min_area_growth_px"] and growth/radii[j] > c["min_relative_radius_growth"]:
            raw[k] = [contrast[k]*speed[k],contrast[k]*radii[k]]
    return dict(area_px=areas,radius_px=radii,contrast=contrast,valid=valid,
                anchor_index=anchors,backward_speed_px_s=speed,raw_channels=raw)


def load_mapping():
    """Read node identity only; never load connectivity/dynamics or simulate."""
    path = ROOT / "connectome/phase3/circuit_v2_nodes.csv"
    with path.open() as handle:
        rows = list(csv.DictReader(handle))
    graph = json.loads((path.parent / "circuit_v2.json").read_text())
    nodes = {int(n["bodyId"]): n for n in graph["nodes"]}
    ids = [int(r["bodyId"]) for r in rows]
    if len(ids) != 321 or len(set(ids)) != 321 or set(ids) != set(nodes):
        raise ValueError("Invalid frozen node identities")
    assigned = []
    for row,bid in zip(rows,ids):
        for key in ("type","side","population"):
            if row[key] != nodes[bid][key]:
                raise ValueError("Node CSV/JSON mapping disagreement")
        channel = {"LC4":0,"LPLC2":1}.get(row["type"],-1)
        if row["population"] != ("visual_input" if channel >= 0 else "readout"):
            raise ValueError("Unexpected population role")
        assigned.append(channel)
    for ntype,total,left,right in (("LC4",126,71,55),("LPLC2",185,94,91)):
        subset = [r for r in rows if r["type"] == ntype]
        if len(subset) != total or sum(r["side"]=="left" for r in subset) != left or sum(r["side"]=="right" for r in subset) != right:
            raise ValueError("Circuit input population mismatch")
    if sum(x == -1 for x in assigned) != 10:
        raise ValueError("Expected ten unassigned descending nodes")
    return dict(schema_version="1.0",body_ids=ids,channel_index=assigned,
        nodes=[dict(bodyId=bid,type=r["type"],side=r["side"],population=r["population"],channel_index=ch) for bid,r,ch in zip(ids,rows,assigned)],
        unassigned_body_ids=[bid for bid,ch in zip(ids,assigned) if ch < 0],
        nodes_csv_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        nodes_json_sha256=hashlib.sha256((path.parent/"circuit_v2.json").read_bytes()).hexdigest(),
        ordering="Circuit v2 node CSV row order; matches Phase 4 loader")


def fit_normalization(training_features,config,training_records):
    c = validate_config(config)
    if not training_records or any(r["split"] != "train" for r in training_records):
        raise ValueError("Normalization accepts training records only")
    if len(training_features) != len(training_records):
        raise ValueError("Training feature/record count mismatch")
    values = np.concatenate(training_features,axis=0)
    if values.ndim != 2 or values.shape[1] != 2 or not np.all(np.isfinite(values)) or np.any(values < 0):
        raise ValueError("Invalid training features")
    scales = []
    for column in values.T:
        positive = column[column > 0]
        if not len(positive):
            raise ValueError("Training channel has no positive values")
        scales.append(float(np.quantile(positive,c["normalization_quantile"])))
    return dict(schema_version="1.0",encoder_version=VERSION,config_sha256=digest(c),
        method="quantile_of_strictly_positive_training_values",quantile=c["normalization_quantile"],
        scales=scales,training_records=training_records,training_records_sha256=digest(training_records))


@dataclass
class Encoded:
    channels: np.ndarray
    drive: np.ndarray
    body_ids: np.ndarray
    timestamps_s: np.ndarray
    diagnostics: dict
    encoder_version: str
    config_sha256: str
    normalization_sha256: str


class CausalEncoder:
    def __init__(self,config,normalization,mapping=None):
        self.config = validate_config(config)
        self.normalization = json.loads(json.dumps(normalization,allow_nan=False))
        if normalization.get("encoder_version") != VERSION or normalization.get("schema_version") != "1.0" or normalization.get("config_sha256") != digest(self.config):
            raise ValueError("Normalization version/config mismatch")
        self.scales = np.asarray(normalization["scales"],dtype=np.float64)
        if self.scales.shape != (2,) or not np.all(np.isfinite(self.scales)) or np.any(self.scales <= 0):
            raise ValueError("Invalid normalization scales")
        actual = load_mapping()
        if mapping is not None and digest(mapping) != digest(actual):
            raise ValueError("Mapping differs from frozen Circuit v2")
        self.mapping = actual

    def encode(self,frames,timestamps_s):
        features = extract_features(frames,timestamps_s,self.config)
        channels = np.clip(features["raw_channels"]/self.scales,0,self.config["output_clip"])
        drive = np.zeros((len(frames),len(self.mapping["body_ids"])),dtype=np.float64)
        assigned = np.asarray(self.mapping["channel_index"])
        drive[:,assigned >= 0] = channels[:,assigned[assigned >= 0]]
        return Encoded(channels,drive,np.array(self.mapping["body_ids"],dtype=np.int64),timestamps_s.copy(),
            features,VERSION,digest(self.config),digest(self.normalization))


def causal_hold(values,timestamps_s,query_s):
    validate_time(timestamps_s,len(values))
    if not isinstance(values,np.ndarray) or values.ndim < 1 or not np.all(np.isfinite(values)):
        raise ValueError("Invalid hold values")
    query = np.asarray(query_s,dtype=np.float64)
    if query.ndim != 1 or not np.all(np.isfinite(query)):
        raise ValueError("Queries must be finite one-dimensional seconds")
    indices = np.searchsorted(timestamps_s,query,side="right")-1
    output = np.zeros((len(query),)+values.shape[1:],dtype=values.dtype)
    available = indices >= 0
    output[available] = values[indices[available]]
    return output
