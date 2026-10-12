"""Integration validation. Writes Phase 7 only; uses fixed training samples."""
from copy import deepcopy
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
from connectome.scripts.phase6.dataset import movie_hash
from connectome.scripts.phase6.encoder import digest
from .evidence import ROOT, OUT, PHASE, protected_hashes, write_json, file_hash
from .pipeline import FrozenPipeline, save_run
from .regression import run as regression


def plot_family(pipeline, runs, group_id):
    selected = [row for row in runs if row["group_id"] == group_id]
    fig, axes = plt.subplots(4, 1, figsize=(10, 11), sharex=True)
    styles = dict(looming="-", static_initial="--", static_terminal=":", translating_initial="-.")
    for row in selected:
        run = row["run"]
        role = row["role"]
        for ch, color in ((0, "tab:blue"), (1, "tab:orange")):
            t = np.append(run.encoded.timestamps_s, run.times_ms[-1] / 1000)
            y = np.append(run.encoded.channels[:, ch], run.encoded.channels[-1, ch])
            axes[0].step(t, y, where="post", linestyle=styles[role], color=color,
                         label=f"{role}: {'LC4' if ch == 0 else 'LPLC2'} drive", alpha=0.8)
        for ntype, color in (("LC4", "tab:blue"), ("LPLC2", "tab:orange")):
            ids = pipeline.circuit.get_population_indices(ntype)
            axes[1].plot(run.times_ms / 1000, run.states[:, ids].mean(axis=1), color=color, linestyle=styles[role], label=f"{role}: {ntype}")
        for side, color in (("left", "tab:green"), ("right", "tab:red")):
            bid = next(bid for bid in pipeline.circuit.body_ids if pipeline.circuit.type_map[bid] == "DNp01" and pipeline.circuit.side_map[bid] == side)
            axes[2].plot(run.times_ms / 1000, run.states[:, pipeline.circuit.id_to_idx[bid]], color=color,
                         linestyle=styles[role], label=f"{role}: DNp01 {side}")
        for ntype in ("DNp01", "DNp04", "DNp02", "DNp11", "DNp06"):
            ids = pipeline.circuit.get_population_indices(ntype)
            axes[3].plot(run.times_ms / 1000, run.states[:, ids].mean(axis=1), linestyle=styles[role],
                         label=f"{role}: {ntype}" if role == "looming" else None, alpha=1 if role == "looming" else 0.3)
    labels = ["Encoded drive [0,1]", "Visual mean activity", "DNp01 activity", "Bilateral DN mean activity"]
    for ax, label in zip(axes, labels):
        ax.set_ylabel(label)
        ax.axvline(0.2, color="gray", linestyle="--", linewidth=0.8)
        ax.grid(alpha=0.2)
        ax.legend(fontsize=7, ncol=2)
    axes[-1].set_xlabel("Time (s); states include diagnostic endpoint")
    fig.suptitle(f"{group_id}: modeled activity in arbitrary units; no behavioral interpretation")
    fig.tight_layout()
    path = OUT / "plots" / f"{group_id}_activity.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ("stimuli", "activity", "plots"):
        (OUT / name).mkdir(exist_ok=True)
    before = json.loads((OUT / "preservation_before.json").read_text())
    if before != protected_hashes():
        raise RuntimeError("Earlier artifacts changed since before snapshot; do not overwrite or silently proceed")
    prior_regression = json.loads((OUT / "regression/before/summary.json").read_text())
    if prior_regression["status"] != "PASS":
        raise RuntimeError("Before regression failed")
    pipeline = FrozenPipeline()
    write_json(OUT / "resolved_pipeline_config.json", pipeline.pipeline_config)
    write_json(OUT / "resolved_simulation_defaults.json", pipeline.simulation_config)
    sources = {str(p.relative_to(ROOT)): file_hash(p)
               for base in (ROOT / "connectome/phase7", ROOT / "connectome/scripts/phase7")
               for p in sorted(base.rglob("*")) if p.is_file() and "results" not in p.parts and "__pycache__" not in p.parts}
    write_json(OUT / "run_configuration.json", dict(sources_sha256=sources, phase6=pipeline.freeze_evidence,
               input_ids=pipeline.pipeline_config["validation_sample_ids"], fitting_trials=0,
               held_out_neural_simulations=0, configuration_saved_before_sample_activity=True))
    command = [sys.executable, "-m", "pytest", "connectome/phase7/tests/", "-q", f"--junitxml={OUT / 'tests.xml'}"]
    tests = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    (OUT / "tests.log").write_text(tests.stdout + tests.stderr)
    suites = list(ET.parse(OUT / "tests.xml").getroot().iter("testsuite"))
    totals = {key: sum(int(s.attrib.get(key, 0)) for s in suites) for key in ("tests", "failures", "errors", "skipped")}
    after_regression = regression("after")
    gates = []
    def gate(name, passed, detail):
        gates.append(dict(name=name, passed=bool(passed), detail=detail))
    gate("phase7_tests", tests.returncode == 0 and totals["failures"] == 0 and totals["errors"] == 0 and totals["skipped"] == 0, totals)
    gate("prior_behavior_before_after", after_regression["status"] == "PASS" and
         after_regression["unit_test_counts"] == prior_regression["unit_test_counts"] and
         after_regression["phase4_assertions"] == prior_regression["phase4_assertions"], after_regression)
    manifest = json.loads((ROOT / "connectome/phase5_5/results/benchmark_manifest.json").read_text())
    scenarios = {r["scenario_id"]: r for r in manifest["scenarios"]}
    integrity = {r["scenario_id"]: r for r in json.loads((PHASE / "results/dataset_integrity.json").read_text())["records"]}
    results, plot_runs = [], []
    for sid in pipeline.pipeline_config["validation_sample_ids"]:
        row = scenarios[sid]
        if row["cohort"] != "train" or row["split"] != "train":
            raise ValueError("Held-out sample requested by validation configuration")
        frames, ts = generate_stimulus(row["config"])
        gate(sid + ":frame_integrity", movie_hash(frames) == integrity[sid]["movie_sha256"] and
             array_hash(ts) == integrity[sid]["timestamps_sha256"], "Regenerated Phase 5 content matches Phase 6 integrity record")
        save_stimulus(OUT / "stimuli", row["config"], frames, ts, overwrite=True)
        run = pipeline.run_saved(OUT / "stimuli", sid)
        frozen = pipeline.load_frozen_encoded(sid)
        replay = pipeline.run_encoded(frozen, row["config"]["duration_ms"])
        repeated = pipeline.run_saved(OUT / "stimuli", sid)
        gate(sid + ":fresh_vs_frozen", np.array_equal(run.encoded.drive, frozen.drive) and
             np.array_equal(run.encoded.channels, frozen.channels) and np.array_equal(run.encoded.body_ids, frozen.body_ids) and
             np.array_equal(run.encoded.timestamps_s, frozen.timestamps_s) and np.array_equal(run.states, replay.states), "Bitwise encoded and state equality")
        gate(sid + ":determinism", np.array_equal(run.states, repeated.states), "Fresh episode resets state; bitwise identical rerun")
        gate(sid + ":numeric_contract", run.states.shape == (1001, 321) and run.step_input_scaled.shape == (1000, 321) and
             run.metrics["finite"] and run.metrics["activity_min"] >= 0 and run.metrics["direct_dn_input_max"] == 0 and
             run.metrics["activation_clipped_fraction"] == 0 and np.array_equal(run.step_input_scaled, 0.4 * run.step_drive_unscaled), run.metrics)
        gate(sid + ":control_sanity", np.max(run.states) > 0 if row["role"] == "looming" else np.all(run.states == 0), "Nonzero loom; silent matched negatives; engineered integration sanity only")
        paths = save_run(OUT / "activity", sid, run, overwrite=True)
        with np.load(paths[0], allow_pickle=False) as stored:
            fields = dict(times_ms=run.times_ms, states=run.states, body_ids=run.encoded.body_ids,
                          frame_timestamps_s=run.encoded.timestamps_s, channels=run.encoded.channels,
                          frame_drive=run.encoded.drive, step_times_ms=run.step_times_ms,
                          step_frame_indices=run.step_frame_indices, step_drive_unscaled=run.step_drive_unscaled,
                          step_input_scaled=run.step_input_scaled)
            gate(sid + ":saved_roundtrip", stored["schema_version"].item() == "1.0" and all(
                 stored[k].dtype == v.dtype and np.array_equal(stored[k], v) for k, v in fields.items()), "All saved arrays and dtypes match in-memory data")
        results.append(dict(scenario_id=sid, group_id=row["group_id"], role=row["role"], cohort="train", metrics=run.metrics,
                            provenance=run.provenance, artifacts={str(p.relative_to(ROOT)): file_hash(p) for p in paths}))
        plot_runs.append(dict(group_id=row["group_id"], role=row["role"], run=run))
        print(f"{sid}: peak activity={run.metrics['activity_max']:.6g}; clipped={run.metrics['activation_clipped_fraction']}", flush=True)
    plots = [plot_family(pipeline, plot_runs, group) for group in sorted({r["group_id"] for r in results})]
    loom = plot_runs[0]["run"]
    fig, ax = plt.subplots(figsize=(10, 5))
    image = ax.imshow(loom.states.T, aspect="auto", origin="lower", extent=[0, 1, -0.5, 320.5], cmap="viridis")
    ax.set_xlabel("Time (s); includes diagnostic endpoint")
    ax.set_ylabel("Neuron index in frozen CSV order")
    ax.set_title("train_f0000_looming: all 321 modeled neuron traces")
    fig.colorbar(image, ax=ax, label="Activity (arbitrary units)")
    fig.tight_layout()
    heatmap = OUT / "plots/train_f0000_looming_heatmap.png"
    fig.savefig(heatmap, dpi=140)
    plt.close(fig)
    plots.append(heatmap)
    after = protected_hashes()
    write_json(OUT / "preservation_after.json", after)
    gate("earlier_artifact_preservation", before == after, dict(files=len(before), changed=[p for p in set(before) | set(after) if before.get(p) != after.get(p)]))
    write_json(OUT / "episode_results.json", results)
    failures = [g["name"] for g in gates if not g["passed"]]
    report = dict(status="PASS" if not failures else "FAIL", run_time_utc=datetime.now(timezone.utc).isoformat(),
                  invocation=[sys.executable, *sys.argv], tests_command=command, tests=totals,
                  sample_episodes=len(results), held_out_neural_simulations=0, fitting_trials=0,
                  protected_files=len(before), protected_files_unchanged=before == after,
                  gates=gates, failed_gates=failures, plots={str(p.relative_to(ROOT)): file_hash(p) for p in plots},
                  environment=dict(python=platform.python_version(), numpy=np.__version__, matplotlib=matplotlib.__version__),
                  prior_frozen_evidence=pipeline.freeze_evidence)
    write_json(OUT / "validation_results.json", report)
    table = "\n".join(f"| {r['scenario_id']} | {r['metrics']['activity_max']:.6g} | {r['metrics']['input_scaled_max']:.6g} | {r['metrics']['activation_clipped_fraction']:.6g} | {r['metrics']['runtime_s']:.6g} |" for r in results)
    (OUT / "validation_report.md").write_text(f"""# Phase 7 validation report

Session validation UTC: {report['run_time_utc']}. Overall status: **{report['status']}**. {len(gates)-len(failures)}/{len(gates)} checks passed; failed checks: {failures}.

Phase 5 schema-1.0 stimuli → frozen Phase 6 encoder → unchanged Phase 4 simulator → frozen Circuit v2. No actions, behavioral metrics, baselines or later-phase implementation. All activity units are arbitrary model units.

## Evidence actually run

- Read-only Phase 1 verification: 33/33 checks. Phase 2: 8/8. Circuit v2 raw-source verification: 48/48. Independent audit: 12/12. Logs and exact commands: `regression/before/summary.json` and `command_1.log` through `command_4.log`. These verify earlier implementations in this session; they are not new biological evidence.
- Earlier unit suites before and after: 49 Phase 4, 114 Phase 5, 44 Phase 5.5 and 52 Phase 6 tests (259 total). Phase 4 integration assertions separately: 159/159 on both runs. All passed. Read-only regression writes solely to Phase 7.
- Phase 7 tests: {totals['tests']}, failures {totals['failures']}, errors {totals['errors']}, skipped {totals['skipped']}. Covers exact node order, mapping, matrix direction, dimensions, units, input scaling, irregular/fractional/60 Hz hold, step/state timing against an independent Euler calculation, explicit duration/end boundary, future causality, metadata exclusion, zero contrast, controls and invalid-input rejection. Logs/XML are saved.
- Frozen locks verified: {pipeline.freeze_evidence['checked_locked_files']} unique locked files; all 1,024 encoded artifact file hashes and manifest identity checked. Dataset isolation summary rechecked against recorded hashes. Full Phase 6 benchmark response gates were **not rerun**; their locked saved evidence was reviewed. Saved normalization retained exactly; no fitting.
- {len(results)} fixed training clips: regenerated actual movie/time hashes match frozen Phase 6 records. Fresh encoding and frozen-encoding replay yield bitwise-identical drive and activity. Independent repeated runs reset state and are bitwise identical. All saved arrays reload exactly with the declared dtypes. Held-out neural simulations: 0.
- {len(before)} protected earlier files have identical before/after SHA-256 hashes. Inventories include Phase 1–6 artifacts/scripts, Phase 5.5, root README/config/requirements and Phase 1 data alias. Caches excluded. No prior validators that overwrite frozen outputs were invoked.

## Timing, scaling and observed samples

Run duration is explicitly 1,000 ms; the earlier default 500 ms is preserved in its own file. All other simulator settings stay unchanged: gain 0.5, tau 10 ms, Euler dt 1 ms, input_scale 0.4, clip_max 50, zero bias/state/noise, no warmup. Encoder scales remain {pipeline.normalization['scales']}.

Drive is `(60,321)` and state is `(1001,321)`. Step-start inputs are `(1000,321)`. Input is selected at the latest frame timestamp <= simulator time / 1,000. Frame 1 first enters at 17 ms, not 16 ms. Each input updates the following state; the 1 s endpoint is diagnostic only. The final frame is held through the last 999 ms step. Phase 4 applies 0.4 once; DN direct input is exactly zero. No sub-frame sensory or calibrated biological latency claim follows.

| Training sample | Peak activity | Peak scaled input | Activation clipped fraction | Simulator runtime (s) |
| --- | --- | --- | --- | --- |
{table}

Runtime covers Phase 4 simulation/readout computation only, not loading/encoding/diagnostics. Clipping counts preclip activations above 50 over all step×neuron samples, not just states near the cap; encoder channel caps are recorded separately in `episode_results.json`. Static initial, static terminal and matched translation remain exactly silent; this follows from the engineered encoder plus zero initial state. Nonzero looming activity is an integration result, not evidence of useful escape behavior or a wiring advantage.

## Reproducibility artifacts

Exact invocations, versions and hashes are saved in `validation_results.json`, `run_configuration.json`, resolved configs, episode metadata, tests logs/XML and regression summaries. `stimuli/` holds complete Phase 5 schema file sets and configs; `activity/` holds full states, frame drive, causal step inputs, body IDs, resolved configs and provenance. Two family activity plots and one all-neuron heatmap are in `plots/`. Numerical reruns compare arrays bitwise; timestamps/runtime in metadata are expected to vary.

Run from repository root:

```bash
MPLCONFIGDIR=/tmp/fly-phase7-mpl ./venv/bin/python -m connectome.scripts.phase7.validate_phase7
```

## Conflicts and unresolved issues

Preserved documentation conflicts: root README still describes v1 and outdated hemisphere counts; Phase 3 handoff misidentifies the weight-172 edge as intra-LPLC2 while CSV has LC4 81112 → DNp04 531898; Phase 3 confidence range omits low-confidence DNp01 values; Phase 4 specification describes dictionary input while actual simulator requires the callback used here. The 500 ms default versus 1 s benchmark is resolved solely by explicit episode duration. See `../specification.md` for details; no protocol change was made.

Historical Phase 0 has no separate completion evidence. The referenced progress PDF is missing from this checkout and was not reviewed. Phase 7 does not independently repeat full Phase 6 cohort response evaluation; it verifies frozen evidence, all artifact hashes and selected training replay. No calibrated neural units, biological signs/latencies, receptive fields, general-scene encoder, useful behavioral outcome or control-model comparison has been established. Phases 8+, full benchmark neural runs, webcam and 3D demonstrations remain outside this work. No dependencies added, commit or push performed.
""")
    print(f"{report['status']}: {totals}; {len(results)} samples; {len(before)} protected files unchanged", flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
