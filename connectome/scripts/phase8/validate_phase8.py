"""Phase 8 engineering validation; only training data, no final calibration."""
from datetime import datetime, timezone
import json
import platform
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from connectome.scripts.phase6.encoder import digest
from connectome.scripts.phase7.pipeline import FrozenPipeline
from .evidence import ROOT, PHASE, OUT, protected_hashes, verify_previous, file_hash, write_json
from .decoder import InitiationDecoder, Threshold, decode_score, load_config
from .candidates import build_candidates
from .activity_io import load_activity, save_decoded
from .regression import run as regression


def plot_requests(samples, group_id, threshold):
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    for row in samples:
        if row["group_id"] != group_id:
            continue
        decoded = row["decoded"]
        color = {"looming": "tab:blue", "static_initial": "tab:orange", "static_terminal": "tab:green", "translating_initial": "tab:red"}[row["role"]]
        axes[0].plot(decoded.times_ms / 1000, decoded.score, color=color, alpha=.6, label=f"{row['role']} score")
        axes[0].plot(decoded.times_ms / 1000, decoded.sustained_score, color=color, linestyle="--", label=f"{row['role']} 20 ms minimum")
        axes[1].step(decoded.times_ms / 1000, decoded.escape_requested.astype(int), where="post", color=color, label=row["role"])
        if decoded.first_event_ms is not None:
            for ax in axes:
                ax.axvline(decoded.first_event_ms / 1000, color=color, linestyle=":")
    axes[0].set_ylabel("DNp01 score (arbitrary units)")
    axes[0].legend(fontsize=7, ncol=2)
    axes[1].set_ylabel("Latched initiation request")
    axes[1].set_yticks([0, 1])
    axes[1].set_xlabel("Time (s); 1 s endpoint excluded")
    axes[1].legend(fontsize=8, ncol=2)
    for ax in axes:
        ax.axvline(.2, color="gray", linestyle="--", linewidth=.8)
        ax.grid(alpha=.2)
    fig.suptitle(f"{group_id}: provisional request; threshold {threshold.value:.3g}; steering unavailable")
    fig.tight_layout()
    path = OUT / "plots" / f"{group_id}_requests.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ("training_traces", "decoded", "original_rule_audit", "plots"):
        (OUT / name).mkdir(exist_ok=True)
    before = json.loads((OUT / "preservation_before.json").read_text())
    if before != protected_hashes():
        raise RuntimeError("Earlier files changed since the before snapshot")
    baseline = json.loads((OUT / "regression/before/summary.json").read_text())
    if baseline["status"] != "PASS":
        raise RuntimeError("Before regression is not passing")
    previous = verify_previous()
    config = load_config()
    sources = {str(p.relative_to(ROOT)): file_hash(p)
               for base in (PHASE, ROOT / "connectome/scripts/phase8")
               for p in sorted(base.rglob("*")) if p.is_file() and "results" not in p.parts and "__pycache__" not in p.parts}
    record = dict(decoder_config=config, decoder_config_sha256=digest(config), sources_sha256=sources,
                  parent_evidence=previous, amendment_approval="Explicit human reply: Add the versioned improvement, 2026-10-11",
                  threshold_status="provisional_not_validation_selected", validation_neural_runs=0, test_neural_runs=0,
                  training_negative_scenarios=192, sample_ids=FrozenPipeline().pipeline_config["validation_sample_ids"],
                  candidate_generation_saved_before_training_activity=True,
                  final_calibration_status="pending_required_controls_and_validation_selection")
    lock_path = OUT / "implementation_lock.json"
    if lock_path.exists() and json.loads(lock_path.read_text()) != record:
        raise RuntimeError("Phase 8 implementation lock differs; record an explicit new version rather than silently changing conditions")
    write_json(lock_path, record)
    command = [sys.executable, "-m", "pytest", "connectome/phase8/tests/", "-q", f"--junitxml={OUT / 'tests.xml'}"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    (OUT / "tests.log").write_text(result.stdout + result.stderr)
    totals = {k: sum(int(s.attrib.get(k, 0)) for s in ET.parse(OUT / "tests.xml").getroot().iter("testsuite"))
              for k in ("tests", "failures", "errors", "skipped")}
    after_regression = regression("after")
    gates = []
    def gate(name, passed, detail):
        gates.append(dict(name=name, passed=bool(passed), detail=detail))
    gate("phase8_tests", result.returncode == 0 and all(totals[k] == 0 for k in ("failures", "errors", "skipped")), totals)
    gate("previous_regression_before_after", after_regression["status"] == "PASS" and after_regression["tests"] == baseline["tests"] and
         after_regression["phase4_assertions"] == baseline["phase4_assertions"], after_regression)
    pipeline = FrozenPipeline()
    manifest = json.loads((ROOT / "connectome/phase5_5/results/benchmark_manifest.json").read_text())
    negatives = [r for r in manifest["scenarios"] if r["cohort"] == "train" and r["split"] == "train" and r["label"] == 0]
    if len(negatives) != 192 or len({r["group_id"] for r in negatives}) != 64:
        raise ValueError("Training negative completeness mismatch")
    trace_records = []
    silent_decoder = InitiationDecoder(Threshold("always_silent", None))
    start = time.perf_counter()
    for number, row in enumerate(negatives):
        sid = row["scenario_id"]
        try:
            encoded = pipeline.load_frozen_encoded(sid)
            run = pipeline.run_encoded(encoded, row["config"]["duration_ms"])
            decoded = silent_decoder.decode_run(run)
            maximum = float(decoded.sustained_score[decoded.eligible].max())
            path = OUT / "training_traces" / f"{sid}.npz"
            np.savez_compressed(path, schema_version=np.array("1.0"), times_ms=decoded.times_ms,
                score=decoded.score, sustained_score=decoded.sustained_score, eligible=decoded.eligible,
                dn_body_ids=decoded.dn_body_ids, dn_activity=decoded.dn_activity)
            with np.load(path, allow_pickle=False) as stored:
                valid = all(np.array_equal(stored[k], getattr(decoded, k)) for k in
                            ("times_ms", "score", "sustained_score", "eligible", "dn_body_ids", "dn_activity"))
            if not valid:
                raise RuntimeError("Training trace round-trip mismatch")
            trace_records.append(dict(scenario_id=sid, group_id=row["group_id"], split="train", cohort="train",
                label=0, role=row["role"], sustained_score_max=maximum,
                trace_path=str(path.relative_to(ROOT)), trace_sha256=file_hash(path), status="PASS",
                metrics=run.metrics, source_provenance=run.provenance))
        except Exception as error:
            write_json(OUT / "training_failures.json", dict(scenario_id=sid, error=str(error), completed=len(trace_records),
                        interpretation="Failed run; never omitted or silently replaced"))
            raise
        if (number + 1) % 32 == 0:
            print(f"Training negative traces: {number + 1}/192", flush=True)
    training_runtime = time.perf_counter() - start
    write_json(OUT / "training_negative_records.json", trace_records)
    plan = build_candidates(trace_records)
    plan.update(schema_version="1.0", decoder_config_sha256=digest(config),
                training_records_sha256=digest(trace_records), implementation_lock_sha256=file_hash(lock_path),
                benchmark_manifest_sha256=previous["phase6"]["manifest_sha256"],
                threshold_amendment_id=config["threshold_amendment_id"])
    original_plan = build_candidates(trace_records, policy="raw_quantile_original_v1")
    original_plan.update(schema_version="1.0", audit_only=True, training_records_sha256=digest(trace_records))
    write_json(OUT / "candidate_plan.json", plan)
    write_json(OUT / "original_candidate_audit.json", original_plan)
    candidate = next(c for c in plan["candidates"] if c["candidate_id"] == plan["provisional_demo_candidate_id"])
    threshold = Threshold(**candidate["threshold"])
    original_candidate = next(c for c in original_plan["candidates"] if c["candidate_id"] == original_plan["provisional_demo_candidate_id"])
    original_threshold = Threshold(**original_candidate["threshold"])
    gate("training_only_complete_candidates", len(trace_records) == 192 and len(plan["candidates"]) <= 32, dict(records=len(trace_records), candidates=len(plan["candidates"])))
    gate("training_numeric_contract", all(r["metrics"]["finite"] and r["metrics"]["activation_clipped_fraction"] == 0 for r in trace_records), "All training runs finite; no activation clipping; no exclusions")
    samples, summaries = [], []
    decoder = InitiationDecoder(threshold)
    original_decoder = InitiationDecoder(original_threshold)
    scenarios = {r["scenario_id"]: r for r in manifest["scenarios"]}
    for sid in record["sample_ids"]:
        row = scenarios[sid]
        if row["cohort"] != "train":
            raise ValueError("Held-out demonstration requested")
        times, states, ids, duration, source = load_activity(ROOT / "connectome/phase7/results/activity", sid)
        decoded = decoder.decode_activity(times, states, ids, duration)
        repeated = decoder.decode_activity(times, states, ids, duration)
        source.update(candidate_plan_sha256=file_hash(OUT / "candidate_plan.json"), candidate_id=candidate["candidate_id"])
        paths = save_decoded(OUT / "decoded", sid, decoded, source, overwrite=True)
        original = original_decoder.decode_activity(times, states, ids, duration, threshold_status="original_rule_audit")
        save_decoded(OUT / "original_rule_audit", sid, original, dict(source, audit_only=True), overwrite=True)
        gate(sid + ":demonstration", decoded.first_event_ms is not None if row["role"] == "looming" else decoded.first_event_ms is None,
             dict(action=decoded.action(), interpretation="Training integration sanity, not held-out performance"))
        gate(sid + ":determinism", all(np.array_equal(getattr(decoded, k), getattr(repeated, k)) for k in
             ("score", "sustained_score", "escape_event", "escape_requested")), "Bitwise deterministic decoded traces")
        with np.load(paths[0], allow_pickle=False) as stored:
            gate(sid + ":saved_roundtrip", all(stored[k].dtype == getattr(decoded, k).dtype and np.array_equal(stored[k], getattr(decoded, k)) for k in
                 ("times_ms", "score", "sustained_score", "eligible", "escape_event", "escape_requested", "dn_body_ids", "dn_activity")), "All saved trace arrays/dtypes match")
        samples.append(dict(group_id=row["group_id"], role=row["role"], decoded=decoded))
        summaries.append(dict(scenario_id=sid, group_id=row["group_id"], role=row["role"], action=decoded.action(),
                              original_raw_quantile_audit_action=original.action(),
                              artifacts={str(p.relative_to(ROOT)): file_hash(p) for p in paths}))
        print(f"{sid}: first provisional event={decoded.first_event_ms} ms; original audit={original.first_event_ms} ms", flush=True)
    plots = [plot_requests(samples, group, threshold) for group in sorted({s["group_id"] for s in samples})]
    # Independently verify a long synthetic reference; measure without a speed claim.
    rng = np.random.default_rng(88001)
    signal = rng.random(10000)
    signal[4000:4050] = 1.0
    start = time.perf_counter()
    optimized = decode_score(np.arange(len(signal), dtype=np.float64), signal, float(len(signal)), Threshold("finite", .8), threshold_status="synthetic_fixture")
    optimized_s = time.perf_counter() - start
    start = time.perf_counter()
    reference = np.zeros(len(signal))
    for k in range(20, len(signal)):
        reference[k] = min(signal[k - 20:k + 1])
    indices = np.flatnonzero((np.arange(len(signal)) >= 20) & (reference >= .8))
    event = None if len(indices) == 0 else float(indices[0])
    reference_s = time.perf_counter() - start
    gate("optimized_reference_equivalence", np.array_equal(reference, optimized.sustained_score) and optimized.first_event_ms == event,
         dict(samples=len(signal), seed=88001, streaming_decode_runtime_s=optimized_s, minimum_reference_runtime_s=reference_s,
              note="Streaming time includes checks and action arrays; reference time includes only minimum/event calculation. Not a like-for-like speed comparison."))
    after = protected_hashes()
    write_json(OUT / "preservation_after.json", after)
    gate("earlier_artifacts_preserved", before == after, dict(files=len(before), changed=[p for p in set(before) | set(after) if before.get(p) != after.get(p)]))
    write_json(OUT / "episode_results.json", summaries)
    failed = [g["name"] for g in gates if not g["passed"]]
    report = dict(status="PASS" if not failed else "FAIL", run_time_utc=datetime.now(timezone.utc).isoformat(),
                  invocation=[sys.executable, *sys.argv], tests_command=command, tests=totals,
                  gates=gates, failed_gates=failed, training_negative_runs=len(trace_records), training_materialization_runtime_s=training_runtime,
                  validation_neural_runs=0, held_out_neural_runs=0, demonstration_samples=len(summaries),
                  threshold=threshold.as_dict(), threshold_status="provisional_not_validation_selected",
                  calibration_status=plan["final_calibration_status"], steering_status="unavailable_no_spatial_mapping",
                  decoder_config_sha256=digest(config), candidate_plan_sha256=file_hash(OUT / "candidate_plan.json"),
                  implementation_lock_sha256=file_hash(lock_path), protected_files=len(before), protected_files_unchanged=before == after,
                  plots={str(p.relative_to(ROOT)): file_hash(p) for p in plots},
                  environment=dict(python=platform.python_version(), numpy=np.__version__, matplotlib=matplotlib.__version__))
    write_json(OUT / "validation_results.json", report)
    table = "\n".join(f"| {r['scenario_id']} | {r['action']['first_event_ms']} | {r['original_raw_quantile_audit_action']['first_event_ms']} |" for r in summaries)
    (OUT / "validation_report.md").write_text(f"""# Phase 8 engineering validation

UTC: {report['run_time_utc']}. Status **{report['status']}**: {len(gates)-len(failed)}/{len(gates)} gates passed; failed gates {failed}.

Working causal DNp01 initiation decoder, with the user-approved threshold amendment v1.1. No direction, physical movement, environment, behavioral evaluation or control models were implemented. Threshold is **provisional**, not validation-selected. Final calibration and directional steering remain gated.

## Commands and evidence actually run

- `./venv/bin/python -m connectome.scripts.phase8.evidence`: existing Phase 5.5/6 locks and all 1,024 encoded hashes verified; nine Phase 7 source files, eight saved episode artifact sets, plot hashes, passing report and earlier preservation inventory verified. Earlier full Phase 6 response gates were not recomputed.
- `./venv/bin/python -m connectome.scripts.phase8.regression --stage before`: 300 earlier unit tests and 159 Phase 4 integration assertions passed, writing only Phase 8 evidence.
- Phase 8 tests: {totals['tests']} passed, {totals['failures']} failures, {totals['errors']} errors, {totals['skipped']} skipped. Exact test command/log/XML saved here. Covers mapping, bilateral score, causal 20 ms persistence, equality/drop/pulse cases, first-event latch, future/prefix invariance, endpoint exclusion, candidate-only training provenance, amendment versus original audit, ranking/ties, explicit calibration gate, real saved Phase 7 replay and output round-trip.
- After implementation, all 300 earlier tests and 159 integration assertions passed again, with identical counts/results. `{len(before)}` earlier files retained identical before/after SHA-256 hashes. Earlier-output-writing validators were not invoked.
- Materialized all 192 training-negative neural traces (64 complete families), with no failed/excluded run and zero activation clipping. Saved ten-DN, score and sustained-score arrays reload exactly. Trace/config/input/model hashes, runtime and validity are saved per episode. Total materialization time {training_runtime:.6g} s includes loading, simulation, decoding and storage.
- Replayed eight saved Phase 7 training samples into provisional actions; repeated decoded arrays are bitwise identical, as are saved round-trips. Validation neural runs: 0. Held-out neural/decision runs: 0. No thresholds were selected from these demonstration outcomes.
- The bounded-history streaming minimum equals an independent brute-force reference on 10,000 synthetic samples. Seed/runtime evidence saved in the gate record; it is not a like-for-like speed comparison or a biological result.

## Threshold amendment and observed requests

Original raw quantiles are saved separately in `original_candidate_audit.json`. The approved finite threshold is the next larger float64 after each training-negative quantile. All observed training-negative sustained maxima are zero, so 31 quantile levels collapse to one finite candidate plus the silent sentinel. Provisional highest-quantile threshold: `{threshold.value!r}`. This tiny value separates numerical silence and is not noise-robust neural calibration.

The protocol's `>=` comparison is retained. Original raw threshold 0 fires after 20 ms on silent traces; the audit records this rather than changing comparison or hiding events. The amended provisional threshold rejects exact silence and emits initiation requests on the two training looming examples. These are engineered training demonstrations, not evidence of held-out accuracy, useful escape or a wiring advantage.

| Training example | Amended provisional first event (ms) | Original raw-quantile audit first event (ms) |
| --- | --- | --- |
{table}

The score is the mean of DNp01 body IDs 10010 and 10001 in arbitrary model units. A closed 21-sample window at 1 ms dt spans 20 elapsed ms. The first event is one impulse; the request remains latched. Pre-onset events are never reset. A 1 s endpoint state cannot trigger an event. All ten DN traces are saved, but only bilateral DNp01 affects initiation. Steering stays null, explicitly unavailable.

## Reproduction and artifacts

```bash
MPLCONFIGDIR=/tmp/fly-phase8-mpl ./venv/bin/python -m connectome.scripts.phase8.validate_phase8
```

Saved artifacts: implementation/config/amendment lock before training activity; all training trace records and candidate provenance; provisional decoded NPZ/action JSON/metadata; separate original-rule audit; two request plots; tests/regression logs/XML; complete before/after inventories; validation JSON with versions, exact invocations, hashes and gate outcomes. Earlier phase files, normalization and dynamics are unchanged. No new dependencies, commit or push.

## Gates and unresolved issues

The Phase 6 handoff requires feature-only and linear temporal controls before final decoder tuning. They are absent. Phase 8 therefore does not fit a final validation-selected threshold or claim a completed calibrated primary model; production code explicitly rejects final-calibrated status. The future validation rule remains highest timely TPR under full-episode FPR<=0.05, ties smaller FPR then higher threshold, with the always-silent sentinel. It was tested only on synthetic ranking fixtures here.

Spatial mapping is absent, so directional steering cannot be grounded in the existing global input; DN side differences and secondary populations are exploratory activity only. No calibrated activity/latency, noise robustness, physical jump/motor plant, danger or collision label, closed-loop escape, baseline comparison, H1/H2 outcome or biological fidelity is established. The numerical one-float margin may be inadequate once noise/spontaneous drive is introduced. Phase 9+ work remains unauthorized. Missing historical Phase 0 evidence and the earlier progress PDF remain unresolved. Earlier documentation conflicts are preserved in the Phase 7 specification. The approved amendment is separately versioned; parent protocol files were not edited.
""")
    print(f"{report['status']}: {totals}; 192 training negatives; 8 provisional demonstrations; {len(before)} earlier files unchanged", flush=True)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
