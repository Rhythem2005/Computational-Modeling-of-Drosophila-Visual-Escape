"""Causal DNp01 initiation requests. No direction, world or behavior model."""
from collections import deque
from dataclasses import dataclass
import math
from numbers import Real

import numpy as np
import yaml

from connectome.scripts.phase6.encoder import load_mapping
from .evidence import PHASE

VERSION = "1.1.0"


def load_config():
    config = yaml.safe_load((PHASE / "decoder_config.yaml").read_text())
    expected = dict(decoder_version=VERSION, base_protocol_id="fly_open_loop_v1",
        threshold_amendment_id="fly_decoder_thresholds_v1_1", score="bilateral_DNp01_mean",
        dn_body_ids=[10010, 10001], dt_ms=1.0, persistence_ms=20.0, comparison="greater_or_equal",
        persistence_window="closed_inclusive", episode_interval="half_open",
        observation_window_s=[0.2, 1.0], action="escape_initiation_requested",
        event_policy="first_event_latched", steering="unavailable_no_spatial_mapping",
        threshold_candidate_limit=32, threshold_policy="next_float_above_training_negative_quantile",
        demo_candidate="highest_training_negative_quantile", demo_status="provisional_not_validation_selected",
        final_calibration_requires=["feature_only_control", "linear_temporal_control"])
    if config != expected:
        raise ValueError("Decoder config differs from the versioned condition")
    return config


@dataclass(frozen=True)
class Threshold:
    kind: str
    value: float | None

    def __post_init__(self):
        if self.kind not in {"finite", "always_silent"}:
            raise ValueError("Unsupported threshold kind")
        if self.kind == "always_silent":
            if self.value is not None:
                raise ValueError("Silent sentinel has a null threshold, never infinity")
        elif isinstance(self.value, bool) or not isinstance(self.value, (int, float)) or not np.isfinite(self.value) or self.value < 0:
            raise ValueError("Threshold must be finite nonnegative activity")

    def as_dict(self):
        return dict(kind=self.kind, value=self.value)


def validate_series(times_ms, score, duration_ms):
    if isinstance(duration_ms, bool) or not isinstance(duration_ms, (int, float)) or not np.isfinite(duration_ms) or duration_ms <= 0:
        raise ValueError("Explicit finite positive episode duration_ms required")
    if duration_ms != round(duration_ms):
        raise ValueError("Primary decoder requires a duration on the 1 ms grid")
    if not isinstance(times_ms, np.ndarray) or times_ms.dtype != np.float64 or times_ms.ndim != 1 or len(times_ms) == 0:
        raise ValueError("times_ms must be nonempty float64 vector")
    if not np.array_equal(times_ms, np.arange(len(times_ms), dtype=np.float64)):
        raise ValueError("Primary decoder requires regular 1 ms samples beginning at zero")
    if times_ms[-1] >= duration_ms:
        raise ValueError("Decoder samples must exclude the episode endpoint")
    if not isinstance(score, np.ndarray) or score.dtype != np.float64 or score.shape != times_ms.shape or not np.all(np.isfinite(score)) or np.any(score < 0):
        raise ValueError("Score must be finite nonnegative float64 matching time")


class StreamingDecoder:
    """O(T) monotone minimum with O(21) history and a one-shot event latch."""
    def __init__(self, threshold, duration_ms):
        if not isinstance(threshold, Threshold):
            raise ValueError("Expected an explicit finite threshold or silent sentinel")
        if isinstance(duration_ms, bool) or not isinstance(duration_ms, (int, float)) or not np.isfinite(duration_ms) or duration_ms <= 0 or duration_ms != round(duration_ms):
            raise ValueError("Episode duration must be positive integer milliseconds")
        self.threshold = threshold
        self.duration_ms = duration_ms
        self.index = 0
        self.history = deque()
        self.first_event_ms = None

    def update(self, time_ms, score):
        if isinstance(time_ms, bool) or not isinstance(time_ms, Real) or not math.isfinite(time_ms) or time_ms != self.index or time_ms >= self.duration_ms:
            raise ValueError("Streaming times must begin at zero, advance 1 ms, and exclude endpoint")
        if isinstance(score, bool) or not isinstance(score, Real) or not math.isfinite(score) or score < 0:
            raise ValueError("Score must be finite nonnegative scalar activity")
        k = self.index
        # Closed interval [k-20,k]: exactly 20 elapsed ms.
        while self.history and self.history[0][0] < k - 20:
            self.history.popleft()
        while self.history and self.history[-1][1] >= score:
            self.history.pop()
        self.history.append((k, float(score)))
        eligible = k >= 20
        sustained = self.history[0][1] if eligible else 0.0
        impulse = eligible and self.first_event_ms is None and self.threshold.kind == "finite" and sustained >= self.threshold.value
        if impulse:
            self.first_event_ms = float(time_ms)
        self.index += 1
        return dict(sustained_score=sustained, eligible=eligible, escape_event=bool(impulse),
                    escape_requested=self.first_event_ms is not None)


@dataclass
class DecodedEpisode:
    times_ms: np.ndarray
    score: np.ndarray
    sustained_score: np.ndarray
    eligible: np.ndarray
    escape_event: np.ndarray
    escape_requested: np.ndarray
    first_event_ms: float | None
    threshold: Threshold
    threshold_status: str
    dn_body_ids: np.ndarray
    dn_activity: np.ndarray

    def action(self):
        return dict(action_type="escape_initiation_requested", requested=self.first_event_ms is not None,
                    first_event_ms=self.first_event_ms,
                    first_event_s=None if self.first_event_ms is None else self.first_event_ms / 1000.0,
                    threshold=self.threshold.as_dict(), threshold_status=self.threshold_status,
                    steering=None, steering_status="unavailable_no_spatial_mapping",
                    semantics="abstract request; no physical movement or success outcome")


def decode_score(times_ms, score, duration_ms, threshold, *, threshold_status="provisional_not_validation_selected"):
    validate_series(times_ms, score, duration_ms)
    if threshold_status not in {"provisional_not_validation_selected", "original_rule_audit", "synthetic_fixture"}:
        raise ValueError("Final calibrated status is unavailable before the control gate")
    stream = StreamingDecoder(threshold, duration_ms)
    length = len(score)
    sustained = np.zeros(length, dtype=np.float64)
    eligible = np.zeros(length, dtype=bool)
    impulse = np.zeros(length, dtype=bool)
    latched = np.zeros(length, dtype=bool)
    for k, (t, s) in enumerate(zip(times_ms, score)):
        output = stream.update(t, s)
        sustained[k] = output["sustained_score"]
        eligible[k] = output["eligible"]
        impulse[k] = output["escape_event"]
        latched[k] = output["escape_requested"]
    return DecodedEpisode(times_ms.copy(), score.copy(), sustained, eligible, impulse, latched,
                          stream.first_event_ms, threshold, threshold_status,
                          np.array([], dtype=np.int64), np.empty((length, 0), dtype=np.float64))


class InitiationDecoder:
    def __init__(self, threshold):
        self.config = load_config()
        self.threshold = threshold
        mapping = load_mapping()
        self.body_ids = np.array(mapping["body_ids"], dtype=np.int64)
        by_id = {bid: k for k, bid in enumerate(self.body_ids)}
        self.primary_indices = [by_id[bid] for bid in self.config["dn_body_ids"]]
        for index, side in zip(self.primary_indices, ("left", "right")):
            node = mapping["nodes"][index]
            if node["type"] != "DNp01" or node["side"] != side or node["population"] != "readout":
                raise ValueError("Primary bilateral DN identity mismatch")
        self.dn_indices = [k for k, n in enumerate(mapping["nodes"]) if n["population"] == "readout"]

    def decode_activity(self, times_ms, states, body_ids, duration_ms, *, threshold_status="provisional_not_validation_selected"):
        if isinstance(duration_ms, bool) or not isinstance(duration_ms, (int, float)) or not np.isfinite(duration_ms) or duration_ms <= 0 or duration_ms != round(duration_ms):
            raise ValueError("Explicit positive duration on the 1 ms grid required")
        if not isinstance(body_ids, np.ndarray) or body_ids.dtype != np.int64 or not np.array_equal(body_ids, self.body_ids):
            raise ValueError("Body IDs must match frozen Circuit v2 CSV ordering")
        if not isinstance(states, np.ndarray) or states.dtype != np.float64 or states.shape != (len(times_ms), 321) or not np.all(np.isfinite(states)) or np.any(states < 0):
            raise ValueError("States must be finite nonnegative float64 (T,321)")
        # Validate the entire state clock, including any diagnostic endpoint.
        if not isinstance(times_ms, np.ndarray) or times_ms.dtype != np.float64 or not np.array_equal(times_ms, np.arange(len(times_ms), dtype=np.float64)):
            raise ValueError("Activity times must begin at zero and advance 1 ms")
        if len(times_ms) == 0 or times_ms[-1] > duration_ms:
            raise ValueError("Activity exceeds explicit episode duration")
        keep = times_ms < duration_ms
        pair = states[keep][:, self.primary_indices]
        score = pair.mean(axis=1)
        result = decode_score(times_ms[keep], score, duration_ms, self.threshold, threshold_status=threshold_status)
        result.dn_body_ids = self.body_ids[self.dn_indices].copy()
        result.dn_activity = states[keep][:, self.dn_indices].copy()
        return result

    def decode_run(self, run, *, threshold_status="provisional_not_validation_selected"):
        return self.decode_activity(run.times_ms, run.states, run.encoded.body_ids,
                                    run.simulation_config["duration"], threshold_status=threshold_status)


def sustained_negative_max(times_ms, score, duration_ms):
    result = decode_score(times_ms, score, duration_ms, Threshold("always_silent", None))
    if not result.eligible.any():
        raise ValueError("Episode too short for any eligible 20 ms window")
    return float(result.sustained_score[result.eligible].max())
