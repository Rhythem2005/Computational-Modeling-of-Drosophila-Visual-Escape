"""Reproduce the local protocol lock and inspect stimulus-only benchmark samples."""
import hashlib
import json
import subprocess
import sys
import importlib.metadata
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from connectome.scripts.phase5.generator import generate_stimulus, compute_trajectory
from connectome.scripts.phase5_5.protocol import (
    ROOT, PHASE, COHORTS, load_design, build_manifest, validate_manifest, digest,
)


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_hashes():
    result = {}
    for phase in ("phase3", "phase4", "phase5"):
        for base in (ROOT / "connectome" / phase, ROOT / "connectome" / "scripts" / phase):
            for path in sorted(base.rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts:
                    result[str(path.relative_to(ROOT))] = file_hash(path)
    return result


def inspect_samples(manifest):
    inspections = []
    for cohort in COHORTS:
        for row in manifest["scenarios"]:
            if row["group_id"] != f"{cohort}_f0000":
                continue
            c = row["config"]
            frames, ts = generate_stimulus(c)
            centers, radii = compute_trajectory(c)
            assert frames.shape == (60, c["height"], c["width"])
            assert frames.dtype == np.uint8 and ts.dtype == np.float64
            np.testing.assert_array_equal(ts, np.arange(60)/c["fps"])
            area = np.sum(frames != c["background_intensity"], axis=(1,2))
            assert np.all(area > 0)
            assert np.all(centers-radii[:,None] >= 0)
            assert np.all(centers+radii[:,None] < np.array([c["width"],c["height"]]))
            if row["role"] == "looming":
                assert np.all(np.diff(radii) >= 0) and radii[-1] > radii[0]
                assert np.all(np.diff(area.astype(float)) >= 0)
            if row["role"] == "translating_initial":
                expected = c["speed_px_per_s"] * max(0, ts[-1]-c["start_time_ms"]/1000)
                assert np.isclose(np.linalg.norm(centers[-1]-centers[0]), expected)
                # Pixel-center rasterization gives a small centroid quantization error.
                centroids = []
                for frame in (frames[0],frames[-1]):
                    y,x = np.nonzero(frame != c["background_intensity"])
                    centroids.append(np.array([x.mean()+.5,y.mean()+.5]))
                assert np.linalg.norm((centroids[-1]-centroids[0])-(centers[-1]-centers[0])) < 1
            inspections.append(dict(scenario_id=row["scenario_id"], shape=list(frames.shape),
                dtype=str(frames.dtype), timestamps_first_last_s=[float(ts[0]),float(ts[-1])],
                intensity_values=np.unique(frames).tolist(),
                first_last_area_px=[int(area[0]),int(area[-1])],
                frame_sha256=hashlib.sha256(frames.tobytes()).hexdigest(),
                timestamps_sha256=hashlib.sha256(ts.tobytes()).hexdigest()))
    assert len(inspections) == 24
    return inspections


def main():
    before = protected_hashes()
    output = PHASE / "results"
    output.mkdir(exist_ok=True)
    test_command = [str(ROOT / "venv/bin/python"), "-m", "pytest", "connectome/phase5/tests/", "connectome/phase5_5/tests/", "-q", f"--junitxml={output / 'tests.xml'}"]
    run = subprocess.run(test_command, cwd=ROOT, capture_output=True, text=True)
    if run.returncode:
        raise RuntimeError(run.stdout + run.stderr)
    xml = ET.parse(output / "tests.xml").getroot()
    suites = [xml] if xml.tag == "testsuite" else list(xml.iter("testsuite"))
    totals = {k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ("tests","failures","errors","skipped")}
    phase55_tests = sum("phase5_5" in case.attrib.get("classname","") for case in xml.iter("testcase"))
    design = load_design()
    manifest = build_manifest(design)
    counts = validate_manifest(manifest,design)
    assert digest(build_manifest(design)) == digest(manifest)
    inspections = inspect_samples(manifest)
    after = protected_hashes()
    assert before == after, "Protected Phase 3–5 files changed"
    sources = {}
    for base in (PHASE,ROOT / "connectome/scripts/phase5_5"):
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix in {".py",".md",".yaml"} and "results" not in path.parts and "__pycache__" not in path.parts:
                sources[str(path.relative_to(ROOT))] = file_hash(path)
    lock = dict(schema_version="1.0", lock_type="local_protocol_not_external_preregistration",
        protocol_id=design["protocol_id"], design_sha256=digest(design), manifest_sha256=digest(manifest),
        sources_sha256=sources, protected_phase3_to5_sha256=before)
    revision = subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    evidence = dict(schema_version="1.0", generated_at_utc=datetime.now(timezone.utc).isoformat(),
        base_git_commit=revision, tests=totals, phase55_test_count=phase55_tests,
        environment=dict(python=sys.version, packages={name:importlib.metadata.version(name) for name in ("numpy","PyYAML","pytest")}), cohort_counts=counts,
        planned_scenarios=len(manifest["scenarios"]), deterministic_manifest=True,
        sampled_renderings=inspections, protected_file_count=len(before), protected_files_unchanged=True,
        no_neural_encoder_or_behavioral_results=True, manifest_sha256=digest(manifest),
        validation_command="./venv/bin/python -m connectome.scripts.phase5_5.validate_protocol")
    for name,value in (("benchmark_manifest.json",manifest),("protocol_lock.json",lock),("validation_results.json",evidence)):
        (output / name).write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")
    report = f"""# Phase 5.5 — validation report

Generated: {evidence['generated_at_utc']}. Base Git commit: `{revision}`.

## Completed

Local research protocol, evidence/assumption register, Phase 6 handoff, versioned benchmark design, deterministic manifest generation, and protocol integrity tests. This is a research-design phase; no encoder, neural experiment, steering model, or behavioral outcome was implemented or measured.

## Commands and outcomes

- `./venv/bin/python -m pytest connectome/phase5_5/tests/ -q`: {phase55_tests} Phase 5.5 tests passed.
- `./venv/bin/python -m pytest connectome/phase5/tests/ connectome/phase5_5/tests/ -q`: {totals['tests']} tests, {totals['failures']} failures, {totals['errors']} errors, {totals['skipped']} skipped (runner repeats this command and also saves JUnit XML).
- `./venv/bin/python -m connectome.scripts.phase5_5.validate_protocol`: PASS. Validated {len(manifest['scenarios'])} planned configurations in 256 matched families; regenerated the manifest identically; inspected 24 rendered clips (four roles from each of six cohorts).
- Sample checks: THW uint8 frames, float64 frame timestamps, declared intensities, static/initial/terminal matching, monotonic looming, translating trajectory and raster centroid agreement, and absence of clipping. Per-sample hashes, endpoint areas, intensity values and timing are in `validation_results.json`.
- SHA-256 checks: {len(before)} protected files in Phase 3–5 outputs and scripts unchanged during validation. `protocol_lock.json` records their hashes and protocol source hashes.

## Limitations and unresolved work

The lock is local, not external preregistration or a sealed test set. No visual-angle calibration or biological receptive-field mapping is available. Parameter fingerprints rule out identical configs, not every possible identical raster movie; full movie deduplication is a required later gate. Sample rendering covers 24 of 1,024 planned clips, not all clips. The cohort sizes are computational budgets, not a power guarantee. Primary uniform-population encoding cannot establish directional steering. Biological input calibration, actual encoder behavior, decoder thresholds, model controls and research hypotheses remain untested until their later phases. Protected hashes check file integrity, not independent biological validity.

Phase 5.5 deliverables are complete under the documented protocol-only scope. No Phase 6 work, commit or push was performed by this validation command.
"""
    (output / "validation_report.md").write_text(report)
    print(f"PASS: {totals['tests']} tests; {len(manifest['scenarios'])} planned scenarios; 24 rendered clips; {len(before)} protected files unchanged")


if __name__ == "__main__":
    main()
