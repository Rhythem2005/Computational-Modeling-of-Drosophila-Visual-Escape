"""Complete Phase 8 with locked train/validation calibration and separate spatial fixtures."""
from datetime import datetime, timezone
import json
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from connectome.scripts.phase5.generator import generate_stimulus
from connectome.scripts.phase5.stimulus_io import save_stimulus, array_hash
from connectome.scripts.phase6.encoder import digest
from connectome.scripts.phase7.pipeline import FrozenPipeline
from connectome.scripts.phase8.decoder import InitiationDecoder, Threshold, decode_score
from connectome.scripts.phase8.activity_io import load_activity
from .evidence import ROOT, BASE, OUT, file_hash, write_json, protected_hashes, verify_checkpoint
from .controls import load_config, features_from_encoded, fit_linear, linear_score
from .calibration import MODELS, make_plan, select_final
from .decoder import CalibratedDecoder
from .spatial import assign_fields, simulate_spatial
from .activity_io import save_action
from .regression import run as regression


def stable_json(path, value):
    """Reject changed numerical/configuration evidence on reproduction."""
    if path.exists() and json.loads(path.read_text()) != value:
        raise ValueError(f"Reproduction differs from saved definition or result: {path}")
    write_json(path, value)


def stable_npz(path, arrays):
    if path.exists():
        with np.load(path, allow_pickle=False) as saved:
            if set(saved.files) != set(arrays) or any(saved[k].dtype != v.dtype or not np.array_equal(saved[k], v) for k, v in arrays.items()):
                raise ValueError(f"Numerical reproduction differs: {path}")
        return
    np.savez_compressed(path, **arrays)


def fixture_config(seed, side):
    return dict(stimulus_id=f"spatial_s{seed}_{side}", stimulus_type="looming", width=256, height=256, fps=60,
                duration_ms=1000, initial_position=[64 if side == "left" else 192, 128], initial_radius=10,
                background_intensity=128, object_intensity=64, shape="circle", start_time_ms=200, random_seed=0,
                expansion_params=dict(f_R=500, Z0=50, v=25, t_onset_ms=200, min_distance=1))


def materialize(scenarios, pipeline, reused, stage):
    records, index, metrics = [], [], []
    core = InitiationDecoder(Threshold("always_silent", None))
    encoded_index = {r["scenario_id"]: r for r in json.loads((ROOT / "connectome/phase6/results/encoded_index.json").read_text())}
    for number, row in enumerate(scenarios):
        sid = row["scenario_id"]
        try:
            encoded = pipeline.load_frozen_encoded(sid)
            times, feature, filtered = features_from_encoded(encoded)
            if sid in reused:
                previous = reused[sid]
                path = ROOT / previous["trace_path"]
                if file_hash(path) != previous["trace_sha256"]:
                    raise ValueError("Earlier training trace hash differs")
                with np.load(path, allow_pickle=False) as stored:
                    dn_ids, dn = stored["dn_body_ids"].copy(), stored["dn_activity"].copy()
                    circuit_score = stored["score"].copy()
                    if not np.array_equal(times, stored["times_ms"]):
                        raise ValueError("Reused training trace clock mismatch")
                ids = {int(b): k for k, b in enumerate(dn_ids)}
                np.testing.assert_array_equal(circuit_score, (dn[:, ids[10010]] + dn[:, ids[10001]]) / 2)
                numerical = previous["metrics"]
                reused_hash = previous["trace_sha256"]
            else:
                run = pipeline.run_encoded(encoded, 1000.0)
                decoded = core.decode_run(run)
                dn_ids, dn, circuit_score = decoded.dn_body_ids, decoded.dn_activity, decoded.score
                np.testing.assert_array_equal(times, decoded.times_ms)
                numerical = run.metrics
                reused_hash = None
            if not numerical["finite"] or numerical["activation_clipped_fraction"] != 0 or numerical["direct_dn_input_max"] != 0:
                raise ValueError("Invalid/clipped neural run; do not exclude or replace")
            records.append(dict(scenario_id=sid, group_id=row["group_id"], split=stage, cohort=stage,
                                label=row["label"], role=row["role"], times_ms=times,
                                scores=dict(circuit=circuit_score, feature_only=feature),
                                filtered_features=filtered, dn_body_ids=dn_ids, dn_activity=dn))
            index.append(dict(scenario_id=sid, group_id=row["group_id"], split=stage, cohort=stage, label=row["label"],
                              role=row["role"], encoded_sha256=encoded_index[sid]["sha256"],
                              reused_v1_1_trace_sha256=reused_hash))
            metrics.append(dict(scenario_id=sid, reused_previous_neural_run=sid in reused, metrics=numerical))
        except Exception as error:
            write_json(OUT / "failed_materialization.json", dict(scenario_id=sid, stage=stage, completed=len(records), error=str(error),
                                                               policy="Abort; never omit or replace failed cases"))
            raise
        if (number + 1) % 32 == 0:
            print(f"{stage}: {number + 1}/{len(scenarios)} complete", flush=True)
    return records, index, metrics


def save_traces(records, index, linear):
    for row, item in zip(records, index):
        row["scores"]["linear_temporal"] = linear_score(row["filtered_features"], linear)
        path = OUT / "calibration_traces" / f"{row['scenario_id']}.npz"
        arrays = dict(times_ms=row["times_ms"], filtered_features=row["filtered_features"],
                      dn_body_ids=row["dn_body_ids"], dn_activity=row["dn_activity"])
        arrays.update({f"{key}_score": value for key, value in row["scores"].items()})
        stable_npz(path, arrays)
        item.update(trace_path=str(path.relative_to(ROOT)), trace_sha256=file_hash(path))


def save_verified_action(directory, sid, decoded, steering, action, provenance):
    expected = {k: getattr(decoded, k) for k in ("times_ms", "score", "sustained_score", "eligible", "escape_event", "escape_requested", "dn_body_ids", "dn_activity")}
    expected.update({k: steering[k] for k in ("turn_command", "raw_dn_imbalance")})
    path = directory / f"{sid}.npz"
    if path.exists():
        with np.load(path, allow_pickle=False) as saved:
            if any(not np.array_equal(saved[k], v) for k, v in expected.items()):
                raise ValueError("Action traces differ on reproduction")
    paths = save_action(directory, sid, decoded, steering, action, provenance, overwrite=True)
    with np.load(paths[0], allow_pickle=False) as saved:
        if any(saved[k].dtype != v.dtype or not np.array_equal(saved[k], v) for k, v in expected.items()):
            raise ValueError("Action saved-array round trip failed")
    if json.loads(paths[1].read_text()) != action:
        raise ValueError("Action JSON round trip failed")
    return paths


def plot_results(training, selections, primary, spatial, mappings):
    paths = []
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    sample = next(r for r in training if r["scenario_id"] == "train_f0000_looming")
    for ax, model in zip(axes, MODELS):
        result = decode_score(sample["times_ms"], sample["scores"][model], 1000.0, Threshold(**selections[model]["threshold"]))
        ax.plot(result.times_ms / 1000, result.score, label="score")
        ax.plot(result.times_ms / 1000, result.sustained_score, "--", label="20 ms minimum")
        ax.axvline(.2, color="gray", linestyle=":")
        if result.first_event_ms is not None:
            ax.axvline(result.first_event_ms / 1000, color="tab:red", linestyle=":", label=f"request {result.first_event_ms:g} ms")
        ax.set_ylabel(f"{model}\nmodel units"); ax.legend(fontsize=8); ax.grid(alpha=.2)
    axes[-1].set_xlabel("Time (s); endpoint excluded")
    fig.suptitle("Training integration example with frozen validation-selected thresholds")
    fig.tight_layout(); paths.append(OUT / "plots/calibrated_scores.png"); fig.savefig(paths[-1], dpi=140); plt.close(fig)
    fig, axes = plt.subplots(1, 5, figsize=(15, 4), sharex=True, sharey=True)
    for ax, mapping in zip(axes, mappings):
        for side, color in (("left", "tab:blue"), ("right", "tab:orange")):
            fields = [f for f in mapping["fields"] if f["side"] == side]
            ax.scatter([f["center_x"] for f in fields], [f["center_y"] for f in fields], s=5, color=color, alpha=.6)
        ax.set_title(f"seed {mapping['seed']}"); ax.set_xlim(-1, 1); ax.set_ylim(-1, 1); ax.set_xlabel("Image x")
    axes[0].set_ylabel("Image y (up)"); fig.suptitle("Independent synthetic fields; assumed side convention, not measured retinotopy")
    fig.tight_layout(); paths.append(OUT / "plots/synthetic_fields.png"); fig.savefig(paths[-1], dpi=140); plt.close(fig)
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    for ax, side in zip(axes, ("left", "right")):
        for row in spatial:
            if row["side"] == side:
                ax.step(row["times_ms"] / 1000, row["turn"], where="post", label=f"seed {row['seed']}")
        ax.set_ylabel(f"{side} fixture\nturn request"); ax.set_ylim(-1.05, 1.05); ax.axhline(0, color="gray", linewidth=.8)
        ax.axvline(.2, color="gray", linestyle=":"); ax.legend(fontsize=8); ax.grid(alpha=.2)
    axes[-1].set_xlabel("Time (s); positive = engineered rightward request")
    fig.suptitle("All five synthetic mappings; primary uniform condition stays at zero")
    fig.tight_layout(); paths.append(OUT / "plots/synthetic_turn_requests.png"); fig.savefig(paths[-1], dpi=140); plt.close(fig)
    return paths


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ("calibration_traces", "selections", "candidate_plans", "mappings", "spatial_activity", "spatial_stimuli", "plots", "primary_actions", "spatial_actions"):
        (OUT / name).mkdir(exist_ok=True)
    before = json.loads((OUT / "preservation_before.json").read_text())
    if before != protected_hashes():
        raise ValueError("Earlier files changed since completion before snapshot")
    baseline = json.loads((OUT / "regression/before/summary.json").read_text())
    if baseline["status"] != "PASS":
        raise ValueError("Baseline tests failed")
    previous = verify_checkpoint()
    config = load_config()
    sources = {str(p.relative_to(ROOT)): file_hash(p) for base in (BASE, ROOT / "connectome/scripts/phase8/completion")
               for p in sorted(base.rglob("*")) if p.is_file() and "results" not in p.parts and "__pycache__" not in p.parts}
    definition = dict(version="1.2.0", sources_sha256=sources, completion_config_sha256=digest(config), parent_evidence=previous,
                      authorization="User: Fully complete the phase 8; approved versioned next-float improvement",
                      outcome_order="Definition and mappings -> controls tests/train-only fitting -> candidate plans -> validation -> freeze -> spatial fixtures",
                      held_out_test_neural_or_decision_runs=0)
    stable_json(OUT / "definition_lock.json", definition)
    # Every field assignment is saved before any new outcome is materialized.
    pipeline = FrozenPipeline()
    mappings = [assign_fields(pipeline.encoder.mapping["nodes"], seed) for seed in config["spatial_seeds"]]
    for mapping in mappings:
        stable_json(OUT / "mappings" / f"seed_{mapping['seed']}.json", mapping)
    command = [sys.executable, "-m", "pytest", "connectome/phase8/completion/tests/", "-q", f"--junitxml={OUT / 'tests.xml'}"]
    tests = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    (OUT / "tests.log").write_text(tests.stdout + tests.stderr)
    counts = {k: sum(int(s.attrib.get(k, 0)) for s in ET.parse(OUT / "tests.xml").getroot().iter("testsuite"))
              for k in ("tests", "failures", "errors", "skipped")}
    if tests.returncode or any(counts[k] for k in ("failures", "errors", "skipped")):
        raise RuntimeError("Completion tests failed; calibration not authorized by passing prerequisites")
    after_regression = regression("after")
    if after_regression["status"] != "PASS" or after_regression["tests"] != baseline["tests"] or after_regression["phase4_assertions"] != baseline["phase4_assertions"]:
        raise RuntimeError("Earlier regression changed")
    manifest = json.loads((ROOT / "connectome/phase5_5/results/benchmark_manifest.json").read_text())
    cohorts = {stage: [r for r in manifest["scenarios"] if r["split"] == stage and r["cohort"] == stage] for stage in ("train", "validation")}
    if len(cohorts["train"]) != 256 or len(cohorts["validation"]) != 128 or any(sum(r["label"] == 1 for r in cohorts[s]) != n for s, n in (("train", 64), ("validation", 32))):
        raise ValueError("Calibration cohort completeness mismatch")
    if {r["group_id"] for r in cohorts["train"]} & {r["group_id"] for r in cohorts["validation"]}:
        raise ValueError("Training/validation families overlap")
    reused = {r["scenario_id"]: r for r in json.loads((ROOT / "connectome/phase8/results/training_negative_records.json").read_text())}
    if set(reused) != {r["scenario_id"] for r in cohorts["train"] if r["label"] == 0}:
        raise ValueError("Historical training negative completeness mismatch")
    training, train_index, train_metrics = materialize(cohorts["train"], pipeline, reused, "train")
    linear = fit_linear(training)
    stable_json(OUT / "linear_model.json", linear)
    gains = []
    positive = [r for r in training if r["label"] == 1]
    for bid in (10228, 10584):
        gains.append(float(np.mean([r["dn_activity"][:, list(r["dn_body_ids"]).index(bid)].max() for r in positive])))
    if not np.all(np.isfinite(gains)) or min(gains) <= 0:
        raise ValueError("Training-only steering normalizer is missing/nonpositive")
    normalization = dict(body_ids=[10228, 10584], gains=gains, training_ids=[r["scenario_id"] for r in positive],
                         method="mean uniform training-positive peak per DNp06 side; no spatial outcomes or directional targets")
    stable_json(OUT / "steering_normalization.json", normalization)
    save_traces(training, train_index, linear)
    stable_json(OUT / "training_trace_index.json", train_index)
    control_gate = dict(status="PASS", integrated_models=["feature_only", "linear_temporal"], same_encoded_input_verified=True,
                        full_encoded_dimension=321, direct_dn_input=0, input_scale=.4, temporal_dt_ms=1, temporal_tau_ms=10,
                        feature_only_trainable_parameters=0, linear_trainable_parameters=2, training_ids=[r["scenario_id"] for r in training],
                        test_counts=counts, tests_source_sha256=file_hash(BASE / "tests/test_completion.py"),
                        training_trace_index_sha256=file_hash(OUT / "training_trace_index.json"), linear_model_sha256=file_hash(OUT / "linear_model.json"),
                        ordering="Both controls integrated/tested and trained before validation threshold selection")
    stable_json(OUT / "controls_integration.json", control_gate)
    plans = {model: make_plan(training, model) for model in MODELS}
    for model, plan in plans.items():
        plan["final_calibration_status"] = "training_candidates_saved_before_validation_selection"
        stable_json(OUT / "candidate_plans" / f"{model}.json", plan)
    validation, val_index, val_metrics = materialize(cohorts["validation"], pipeline, {}, "validation")
    save_traces(validation, val_index, linear)
    stable_json(OUT / "validation_trace_index.json", val_index)
    selections = {model: select_final(plans[model], validation, model, control_gate) for model in MODELS}
    for model, selected in selections.items():
        stable_json(OUT / "selections" / f"{model}.json", selected)
    prerequisites = [OUT / name for name in ("definition_lock.json", "linear_model.json", "steering_normalization.json", "controls_integration.json", "training_trace_index.json", "validation_trace_index.json")]
    for directory in ("candidate_plans", "selections", "calibration_traces", "mappings"):
        prerequisites.extend(sorted((OUT / directory).iterdir()))
    freeze = dict(version="1.2.0", status="calibrated_frozen", completion_config_sha256=digest(config), sources_sha256=sources,
                  prerequisite_artifacts_sha256={str(p.relative_to(ROOT)): file_hash(p) for p in prerequisites},
                  parent_evidence=previous, control_gate=control_gate, linear_model=linear, steering_normalization=normalization,
                  models={model: {k: s[k] for k in ("threshold", "selected_candidate_id", "selected_assessment", "rule")} for model, s in selections.items()},
                  training_ids=[r["scenario_id"] for r in training], validation_ids=[r["scenario_id"] for r in validation], test_ids_used=[],
                  primary_mapping="uniform_population", spatial_calibration_status="primary threshold reused; separate spatial condition not validation-calibrated")
    freeze["payload_sha256"] = digest(freeze)
    stable_json(OUT / "calibration_freeze.json", freeze)
    decoder = CalibratedDecoder()
    primary, spatial, summaries = [], [], []
    for sid in pipeline.pipeline_config["validation_sample_ids"]:
        times, states, ids, duration, source = load_activity(ROOT / "connectome/phase7/results/activity", sid)
        decoded, steering, action = decoder.decode_activity(times, states, ids, duration)
        repeated, repeat_steering, repeat_action = decoder.decode_activity(times, states, ids, duration)
        if action != repeat_action or not np.array_equal(steering["turn_command"], repeat_steering["turn_command"]) or not np.array_equal(decoded.escape_event, repeated.escape_event):
            raise ValueError("Primary action reproduction differs")
        if np.any(steering["turn_command"] != 0):
            raise ValueError("Uniform primary acquired inferred direction")
        save_verified_action(OUT / "primary_actions", sid, decoded, steering, action, source)
        primary.append(dict(scenario_id=sid, action=action))
    cli_command = [sys.executable, "-m", "connectome.scripts.phase8.completion.run_decoder", "--activity-dir",
                   "connectome/phase7/results/activity", "--stimulus-id", "train_f0000_looming", "--overwrite"]
    cli = subprocess.run(cli_command, cwd=ROOT, capture_output=True, text=True)
    (OUT / "cli.log").write_text(cli.stdout + cli.stderr)
    if cli.returncode:
        raise RuntimeError("Completed primary CLI failed")
    with np.load(OUT / "cli_actions/train_f0000_looming.npz", allow_pickle=False) as a, np.load(OUT / "primary_actions/train_f0000_looming.npz", allow_pickle=False) as b:
        if set(a.files) != set(b.files) or any(not np.array_equal(a[k], b[k]) for k in a.files):
            raise ValueError("CLI arrays differ from integrated primary decoder")
    if json.loads((OUT / "cli_actions/train_f0000_looming_action.json").read_text()) != json.loads((OUT / "primary_actions/train_f0000_looming_action.json").read_text()):
        raise ValueError("CLI action differs from integrated decoder")
    write_json(OUT / "cli_verification.json", dict(status="PASS", command=cli_command, exit_code=cli.returncode, array_and_action_equality=True))
    for mapping in mappings:
        for side in ("left", "right"):
            fixture = fixture_config(mapping["seed"], side)
            sid = fixture["stimulus_id"]
            frames, timestamps = generate_stimulus(fixture)
            save_stimulus(OUT / "spatial_stimuli", fixture, frames, timestamps, overwrite=True)
            run = simulate_spatial(pipeline, frames, timestamps, 1000, mapping)
            repeated = simulate_spatial(pipeline, frames, timestamps, 1000, mapping)
            if not all(np.array_equal(run[k], repeated[k]) for k in ("states", "frame_drive", "centroids")):
                raise ValueError("Synthetic simulation is not bitwise reproducible")
            decoded, steering, action = decoder.decode_activity(run["times_ms"], run["states"], run["body_ids"], 1000,
                                                                condition=mapping["condition_id"], spatial_mapping=mapping)
            turn = steering["turn_command"]
            if np.any(np.abs(turn) > 1) or run["activation_clipped_fraction"] != 0 or np.any(run["frame_drive"][:, np.array(pipeline.encoder.mapping["channel_index"]) < 0] != 0):
                raise ValueError("Spatial numeric/steering contract failed")
            path = OUT / "spatial_activity" / f"{sid}.npz"
            stable_npz(path, {k: run[k] for k in ("times_ms", "states", "body_ids", "frame_drive", "frame_timestamps_s", "centroids", "global_channels")})
            provenance = dict(mapping_sha256=digest(mapping), config_sha256=digest(fixture), activity_sha256=file_hash(path),
                              frames_sha256=array_hash(frames), timestamps_sha256=array_hash(timestamps),
                              simulation_config=run["simulation_config"], normalization_sha256=digest(pipeline.normalization),
                              calibration_sha256=freeze["payload_sha256"], seed=mapping["seed"], bitwise_repeat=True)
            save_verified_action(OUT / "spatial_actions", sid, decoded, steering, action, provenance)
            spatial.append(dict(seed=mapping["seed"], side=side, times_ms=decoded.times_ms, turn=turn))
            summaries.append(dict(scenario_id=sid, seed=mapping["seed"], fixture_side=side, action=action,
                                  activation_clipped_fraction=run["activation_clipped_fraction"], repeat_bitwise=True))
            print(f"{sid}: request={action['first_event_ms']} ms; engineered turn={action['steering']:.6g}", flush=True)
    stable_json(OUT / "primary_episode_results.json", primary)
    stable_json(OUT / "spatial_episode_results.json", summaries)
    plots = plot_results(training, selections, primary, spatial, mappings)
    after = protected_hashes()
    write_json(OUT / "preservation_after.json", after)
    if before != after:
        raise ValueError("Earlier phase/checkpoint files changed")
    write_json(OUT / "run_metrics.json", dict(training=train_metrics, validation=val_metrics))
    report = dict(status="PASS", completion_status="COMPLETE_ENGINEERING", version="1.2.0",
                  run_time_utc=datetime.now(timezone.utc).isoformat(), invocation=[sys.executable, *sys.argv], tests_command=command,
                  completion_tests=counts, earlier_regression=after_regression, protected_files=len(before), protected_files_unchanged=True,
                  training_clips=256, reused_v1_1_negative_neural_traces=192, fresh_training_positive_neural_runs=64,
                  fresh_validation_neural_runs=128, validation_positives=32, validation_negatives=96, held_out_test_neural_or_decision_runs=0,
                  thresholds={model: selections[model]["threshold"] for model in MODELS},
                  calibration_assessments={model: selections[model]["selected_assessment"] for model in MODELS},
                  calibration_freeze_sha256=freeze["payload_sha256"], prerequisite_controls="integrated before final selection",
                  primary_cli_status="PASS; arrays and action equal integrated decoder", saved_action_round_trips=True,
                  primary_steering="neutral uniform input", synthetic_mappings=5, spatial_fixtures=10, spatial_repeat_runs=10,
                  spatial_calibration="uncalibrated spatial fixtures reuse primary frozen initiation threshold", biological_mapping_validated=False,
                  plots={str(p.relative_to(ROOT)): file_hash(p) for p in plots}, failed_gates=[],
                  environment=dict(python=platform.python_version(), numpy=np.__version__, matplotlib=matplotlib.__version__))
    write_json(OUT / "validation_results.json", report)
    calibration_table = "\n".join(f"| {model} | {selections[model]['threshold']} | {selections[model]['selected_assessment']['timely_tpr']:.6g} | {selections[model]['selected_assessment']['full_episode_fpr']:.6g} |" for model in MODELS)
    spatial_table = "\n".join(f"| {r['seed']} | {r['fixture_side']} | {r['action']['first_event_ms']} | {r['action']['steering']:.6g} |" for r in summaries)
    (OUT / "completion_report.md").write_text(f"""# Phase 8 completion validation — v1.2.0

Status: **PASS / COMPLETE_ENGINEERING**. UTC: {report['run_time_utc']}. Current implementation: `connectome/scripts/phase8/completion/`. Historical v1.1 partial checkpoint and parent protocol files remain unchanged. The separate amendment and condition definition were saved before new validation/spatial outcomes.

## Completed deliverables

Primary bilateral DNp01 initiation is now validation-selected and frozen after integrating the required feature-only and linear temporal controls. The zero-threshold amendment uses `nextafter(negative quantile,+infinity)` and retains the causal 20 ms `>=` rule. The optimized bounded-history decoder, first-event latch and endpoint exclusion remain unchanged. Primary uniform input has an explicit neutral turn command. The separately named synthetic spatial condition supplies all five independent field mappings and a DNp06 gain-normalized, bounded, latched turn request. It is an engineered motor convention; no measured retinotopy or physiological steering claim is made.

## Evidence actually run

- Verified prior saved phase/protocol/encoder/pipeline locks and v1.1 checkpoint before relying on them. All earlier encoded-file hashes were checked read-only; no earlier validator regenerated outputs.
- Completion tests: **{counts['tests']} passed**, zero failures/errors/skips. Earlier regressions before and after: **{after_regression['tests']['tests']} tests and {after_regression['phase4_assertions']['passed']} Phase 4 integration assertions passed**, unchanged counts. Logs/XML and exact commands are saved here.
- Reused 192 verified v1.1 train-negative neural traces; these were not fresh neural simulations in this session. Newly simulated all 64 training positives and all 128 validation scenarios with frozen Phase 7/4/6 interfaces. Every model received the same full 321-neuron encoded vectors; DN direct input remained zero. All neural calibration runs were finite with no activation clipping; no scenario failed or was excluded.
- Linear weights fitted once on the 256 training clips only: `{linear['weights']}`; zero bias, two coefficients, fixed ridge 1e-6, no hyperparameter search. Temporal Euler filter uses dt=1 ms, tau=10 ms, scale=0.4 and zero initial state. Feature-only channel mean is fixed, with no trained coefficients. These are minimal calibration prerequisites; comprehensive fair-control experiments remain later work.
- Generated training-negative candidate plans for all three models before validation selection. All 128 validation clips were used only for the specified threshold ranking, with 32 positives and 96 negatives. First events before 200 ms are retained as early decisions, not reset; negative FPR uses the full episode. No test-ID/OOD neural or decision run occurred.
- Saved/froze thresholds, weights, train/validation identities, all 384 score/DN traces, full candidate assessments/predictions, control proof and source/config/parent/artifact hashes. Replayed eight saved Phase 7 training examples into final primary action schema 1.2, with bitwise repeat checks and neutral steering. Ran the completed CLI on `train_f0000_looming`; its arrays/action equal the integrated decoder. All saved action arrays/dtypes and JSON round-trip exactly.
- Saved every synthetic field assignment before outcomes. Ran both predefined spatial looming fixtures for each of five seeds, then repeated all ten simulations bitwise. Saved stimuli/configs, full activity/drive/centroid arrays, actions and metadata. All spatial runs were finite, unclipped, DN input zero and turn requests bounded. No seed, width or directional rule was selected from results.
- **{len(before)} earlier phase/checkpoint files have identical before/after SHA-256 hashes.** No dependency install, commit, push, environment physics or Phase 9 implementation.

## Validation calibration results

| Model | Frozen threshold | Timely validation TPR | Full-episode negative FPR |
| --- | --- | --- | --- |
{calibration_table}

These are threshold-selection metrics on validation data, not untouched-test results or evidence of a circuit advantage. All negative sustained maxima were zero; finite candidates collapse to a one-float margin above silence. This is not noise-robust calibration. Spontaneous activity/noise would require a new documented condition and appropriate calibration.

## Synthetic steering integration results

DNp06 bodies 10228/10584 use train-only mean positive-peak normalizers `{gains}`. At initiation, positive normalized left-minus-right imbalance requests a rightward turn. Primary uniform input stays at zero. Spatial initiation reuses the primary frozen threshold solely as an explicitly uncalibrated integration-fixture value; it is not a separately calibrated spatial model.

| Mapping seed | Fixture side | First request (ms) | Latched normalized turn |
| --- | --- | --- | --- |
{spatial_table}

These outputs demonstrate implemented commands under independent synthetic sensory/motor assumptions. They do not measure useful escape, anatomical directional fidelity or biological superiority. Both positions reuse the same stimulus geometry across seeds intentionally, to vary mapping alone. No motor plant, heading, collision, speed or success evaluator is present.

## Reproduction and remaining scientific issues

Run `MPLCONFIGDIR=/tmp/fly-phase8-completion-mpl ./venv/bin/python -m connectome.scripts.phase8.completion.validate_completion`. Saved source/config/evidence changes are rejected. Reproduction checks numerical arrays, selections, linear weights, steering scales and freeze against saved results; runtime/date evidence may vary. The CLI in the completion README decodes existing Phase 7 activity and verifies the freeze before inference. Plots are under `plots/`: calibrated scores, all field assignments and all turn traces.

Unresolved scientific issues: biological retinotopy and DN motor interpretation are assumed; tiny silence thresholds lack noise robustness; spatial condition lacks its own final validation calibration; no useful-behavior, held-out-test or fair wiring advantage result is established. Later phases must address behavior, richer controls and repeated experiments. Historical missing Phase 0 evidence/progress PDF and previously documented specification conflicts remain unresolved; this completion does not revise them. The engineering deliverables of Phase 8 are complete within the separately documented v1.2 condition. No later phase was started.
""")
    print(f"PASS / COMPLETE_ENGINEERING: {counts['tests']} completion tests; {after_regression['tests']['tests']} earlier tests; {len(before)} files unchanged", flush=True)


if __name__ == "__main__":
    main()
