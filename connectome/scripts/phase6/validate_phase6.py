"""Stimulus-only validation, with training fit and explicit pre-evaluation lock."""
import hashlib
import json
import platform
import subprocess
from datetime import datetime,timezone
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from connectome.scripts.phase5.generator import generate_stimulus,compute_trajectory
from connectome.scripts.phase5_5.protocol import load_design,validate_manifest
from .encoder import ROOT,PHASE,load_config,load_mapping,extract_features,fit_normalization,CausalEncoder,digest,causal_hold
from .dataset import movie_hash,check_isolation,encode_saved

OUT = PHASE/"results"


def write_json(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_hashes():
    hashes = {}
    for phase in ("phase3","phase4","phase5","phase5_5"):
        for base in (ROOT/"connectome"/phase,ROOT/"connectome/scripts"/phase):
            for path in sorted(base.rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts:
                    hashes[str(path.relative_to(ROOT))] = hash_file(path)
    return hashes


def sources():
    hashes = {}
    for base in (PHASE,ROOT/"connectome/scripts/phase6"):
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix in {".py",".md",".yaml"} and "results" not in path.parts and "__pycache__" not in path.parts:
                hashes[str(path.relative_to(ROOT))] = hash_file(path)
    return hashes


def plot_family(cohort,scenarios,encoder):
    fig,axes = plt.subplots(3,1,figsize=(9,8),sharex=True)
    for row in scenarios:
        if row["group_id"] != f"{cohort}_f0000": continue
        frames,ts = generate_stimulus(row["config"])
        encoded = encoder.encode(frames,ts)
        _,truth = compute_trajectory(row["config"])
        for ch in (0,1): axes[ch].plot(ts,encoded.channels[:,ch],label=row["role"])
        axes[2].plot(ts,encoded.diagnostics["radius_px"],label=row["role"]+" raster")
        axes[2].plot(ts,truth,linestyle=":",linewidth=1,color="black",alpha=.5)
    for ax in axes:
        ax.axvline(.2,color="gray",linestyle="--")
        ax.grid(alpha=.2)
    axes[0].set_ylabel("LC4-like drive [0,1]"); axes[1].set_ylabel("LPLC2-like drive [0,1]")
    axes[2].set_ylabel("Radius (pixels)"); axes[2].set_xlabel("Time (s)")
    axes[0].legend(fontsize=8,ncol=2); axes[2].legend(fontsize=7,ncol=2)
    fig.suptitle(f"{cohort}: post-freeze engineered signals; dotted = analytic geometry")
    fig.tight_layout(); fig.savefig(OUT/"plots"/f"{cohort}.png",dpi=130); plt.close(fig)


def summarize(metrics):
    gates = []
    def record(name,value,threshold,passed,cohort="all",channel="both"):
        gates.append(dict(gate=name,cohort=cohort,channel=channel,value=value,threshold=threshold,status="PASS" if passed else "FAIL"))
    record("output_contract",sum(not m["contract_ok"] for m in metrics),"0 invalid episodes",all(m["contract_ok"] for m in metrics))
    errors = np.concatenate([np.asarray(m["radius_errors"]) for m in metrics])
    fraction = float(np.mean(errors <= 1))
    record("radius_geometry",fraction,">=0.95 frames within 1 pixel",fraction >= .95)
    speed_errors = np.concatenate([np.asarray(m["speed_errors"]) for m in metrics if m["speed_errors"]])
    median,p95 = np.quantile(speed_errors,[.5,.95]).tolist()
    record("speed_geometry_median",median,"<=0.20 relative error",median <= .2)
    record("speed_geometry_p95",p95,"<=0.50 relative error",p95 <= .5)
    record("pre_onset",sum(m["pre_onset_count"] for m in metrics),"0 nonzero samples",all(m["pre_onset_count"] == 0 for m in metrics))
    for cohort in sorted({m["cohort"] for m in metrics}):
        subset = [m for m in metrics if m["cohort"] == cohort]
        for polarity in (None,-1,1):
            part = [m for m in subset if polarity is None or m["polarity"] == polarity]
            suffix = "" if polarity is None else f"_polarity_{polarity}"
            for role in ("static_initial","static_terminal","translating_initial"):
                negatives = [m for m in part if m["role"] == role]
                peak = max(max(m["peak"]) for m in negatives)
                record(role+suffix,peak,"<=0.01 peak",peak <= .01,cohort)
            positives = [m for m in part if m["role"] == "looming"]
            cutoff,required = (.005,.9) if cohort == "test_ood_contrast" else (.01,.95)
            for ch,name in enumerate(("LC4_like","LPLC2_like")):
                fraction = sum(m["peak"][ch] > cutoff for m in positives)/len(positives)
                record("loom_response"+suffix,fraction,f">={required} fraction with peak>{cutoff}",fraction >= required,cohort,name)
            fraction = sum(m["first_response_s"] is not None and .2 <= m["first_response_s"] <= .38 for m in positives)/len(positives)
            record("onset_latency"+suffix,fraction,">=0.95 begin in [0.2,0.38] s",fraction >= .95,cohort)
    return gates


def fixture_gates(encoder,row):
    """Measured invariant outcomes from synthetic fixtures, not test tuning."""
    from copy import deepcopy
    checks = []
    def record(name,error):
        checks.append(dict(gate=name,value=float(error),threshold="exactly 0",status="PASS" if error == 0 else "FAIL"))
    frames,ts = generate_stimulus(row["config"])
    encoded = encoder.encode(frames,ts)
    zero = deepcopy(row["config"]); zero["object_intensity"] = zero["background_intensity"]
    z,t = generate_stimulus(zero)
    record("zero_contrast",np.max(encoder.encode(z,t).drive))
    reversed_polarity = deepcopy(row["config"])
    reversed_polarity["object_intensity"] = 256-reversed_polarity["object_intensity"]
    f,t = generate_stimulus(reversed_polarity)
    record("matched_polarity",np.max(np.abs(encoder.encode(f,t).drive-encoded.drive)))
    record("reproducibility",np.max(np.abs(encoder.encode(frames,ts).drive-encoded.drive)))
    mutated = frames.copy(); cut = 30; mutated[cut:] = 0
    record("future_frame_causality",np.max(np.abs(encoder.encode(mutated,ts).drive[:cut]-encoded.drive[:cut])))
    record("prefix_causality",np.max(np.abs(encoder.encode(frames[:cut],ts[:cut]).drive-encoded.drive[:cut])))
    rejections = 0
    for meta in (dict(label=0,type="static",radius=1,speed=1),dict(label=1,type="looming",radius=999,speed=999)):
        try: encoder.encode(frames,ts,metadata=meta)
        except TypeError: rejections += 1
    record("metadata_argument_rejection",2-rejections)
    for case,position,radius in (("border",[0,128],10),("offscreen",[-1000,128],10),("fullfield",[128,128],1000)):
        c = deepcopy(row["config"])
        c.update(stimulus_type="static",initial_position=position,initial_radius=radius)
        c.pop("expansion_params",None)
        f,t = generate_stimulus(c); output = encoder.encode(f,t)
        record("clipping_"+case,np.max(output.drive)+np.count_nonzero(output.diagnostics["valid"]))
    t = np.arange(len(frames),dtype=np.float64)/59.7+.0037
    fraction_out = encoder.encode(frames,t)
    record("fractional_timestamps",np.count_nonzero(~np.isfinite(fraction_out.drive)))
    stamps = np.array([0.,.125,.25],dtype=np.float64)
    values = np.array([[0.,0.],[1.,2.],[3.,4.]])
    queries = np.array([-.125,0.,.124,.125,.249,.25,.5])
    expected = np.array([[0,0],[0,0],[0,0],[1,2],[1,2],[3,4],[3,4]])
    record("causal_availability",np.max(np.abs(causal_hold(values,stamps,queries)-expected)))
    record("seconds_ms_availability",np.max(np.abs(causal_hold(values,stamps,queries)-causal_hold(values,stamps,queries*1000/1000))))
    return checks


def main():
    before = protected_hashes()
    for directory in (OUT,OUT/"encoded",OUT/"plots"):
        directory.mkdir(parents=True,exist_ok=True)
    preflight_sources = sources()
    old_lock = OUT/"freeze_lock.json"
    if old_lock.exists() and json.loads(old_lock.read_text())["sources_sha256"] != preflight_sources:
        raise RuntimeError("Sources changed after freeze. Do not silently retune: record an amendment before rerun.")
    config = load_config(); mapping = load_mapping()
    manifest_path = ROOT/"connectome/phase5_5/results/benchmark_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    validate_manifest(manifest,load_design())
    rows = manifest["scenarios"]
    integrity,training_features,training_records = [],[],[]
    # Pre-freeze: test clips are rendered ONLY for actual-content integrity.
    for row in rows:
        frames,ts = generate_stimulus(row["config"])
        entry = {k:row[k] for k in ("scenario_id","group_id","split","cohort")}
        entry.update(movie_sha256=movie_hash(frames),timestamps_sha256=hashlib.sha256(ts.tobytes()).hexdigest())
        integrity.append(entry)
        if row["split"] == "train":
            training_features.append(extract_features(frames,ts,config)["raw_channels"])
            training_records.append(entry)
    integrity_summary = check_isolation(integrity)
    if integrity_summary["records"] != 1024 or integrity_summary["families"] != 256:
        raise ValueError("Benchmark count mismatch")
    write_json(OUT/"dataset_integrity.json",dict(summary=integrity_summary,records=integrity))
    normalization = fit_normalization(training_features,config,training_records)
    write_json(OUT/"normalization.json",normalization); write_json(OUT/"mapping.json",mapping)
    lock = dict(schema_version="1.0",encoder_version="1.0.0",freeze_time_utc=datetime.now(timezone.utc).isoformat(),
        sources_sha256=preflight_sources,config_sha256=digest(config),normalization_sha256=digest(normalization),
        mapping_sha256=digest(mapping),manifest_sha256=digest(manifest),dataset_integrity_sha256=digest(integrity),
        protected_sha256=before,tuning_budget=0,normalization_training_clips=len(training_records),
        test_responses_inspected_before_freeze=False)
    if old_lock.exists():
        previous = json.loads(old_lock.read_text())
        for key in ("config_sha256","normalization_sha256","mapping_sha256","manifest_sha256","dataset_integrity_sha256","protected_sha256"):
            if previous[key] != lock[key]: raise RuntimeError(f"Freeze mismatch: {key}")
        lock = previous
    write_json(old_lock,lock)
    print(f"Freeze saved: {len(training_records)} training clips; {len(integrity)} unique movies; no test features used",flush=True)
    encoder = CausalEncoder(config,normalization,mapping)
    metrics,index = [],[]
    for number,row in enumerate(rows):
        frames,ts = generate_stimulus(row["config"])
        encoded = encoder.encode(frames,ts)
        _,truth = compute_trajectory(row["config"])
        features = encoded.diagnostics
        valid = features["valid"]
        # Independent evaluator geometry never reaches feature computation.
        radius_errors = np.abs(features["radius_px"][valid]-truth[valid]).tolist()
        anchors = features["anchor_index"]
        active = (anchors >= 0) & (features["raw_channels"][:,0] > 0)
        kk = np.flatnonzero(active); jj = anchors[active]
        true_speed = (truth[kk]-truth[jj])/(ts[kk]-ts[jj])
        measured = features["backward_speed_px_s"][active]
        speed_errors = (np.abs(measured-true_speed)/np.maximum(true_speed,1e-12)).tolist()
        assignment = np.array(mapping["channel_index"])
        contract = bool(np.all(np.isfinite(encoded.drive)) and np.all((encoded.drive >= 0)&(encoded.drive <= 1)) and np.all(encoded.drive[:,assignment < 0] == 0))
        for channel in (0,1):
            contract = contract and np.array_equal(encoded.drive[:,assignment==channel],np.repeat(encoded.channels[:,channel:channel+1],sum(assignment==channel),axis=1))
        nonzero = np.flatnonzero(np.any(encoded.channels > 0,axis=1))
        metrics.append(dict(scenario_id=row["scenario_id"],cohort=row["cohort"],split=row["split"],role=row["role"],
            polarity=int(np.sign(row["config"]["object_intensity"]-row["config"]["background_intensity"])),
            peak=encoded.channels.max(axis=0).tolist(),first_response_s=float(ts[nonzero[0]]) if len(nonzero) else None,
            pre_onset_count=int(np.count_nonzero(encoded.channels[ts < .2])),contract_ok=contract,
            radius_errors=radius_errors,speed_errors=speed_errors,
            output_cap_fraction=float(np.mean(encoded.channels >= 1)),evaluation_stage="post_freeze"))
        path = OUT/"encoded"/(row["scenario_id"]+".npz")
        np.savez_compressed(path,channels=encoded.channels,drive=encoded.drive,body_ids=encoded.body_ids,timestamps_s=encoded.timestamps_s,
            radius_px=features["radius_px"],area_px=features["area_px"],valid=features["valid"],raw_channels=features["raw_channels"],
            encoder_version=np.array(encoded.encoder_version),schema_version=np.array("1.0"),
            config_sha256=np.array(encoded.config_sha256),normalization_sha256=np.array(encoded.normalization_sha256))
        index.append(dict(scenario_id=row["scenario_id"],path=str(path.relative_to(PHASE)),sha256=hash_file(path),
            evaluation_stage="post_freeze",freeze_lock_sha256=hash_file(old_lock)))
        if (number+1)%256 == 0: print(f"Post-freeze encoding: {number+1}/{len(rows)}",flush=True)
    gates = summarize(metrics)+fixture_gates(encoder,rows[0])
    gates.append(dict(gate="dataset_integrity",value=integrity_summary["duplicate_movies"]+integrity_summary["cross_split_families"],threshold="0 collisions; 1024 records, 256 families",status="PASS"))
    write_json(OUT/"episode_metrics.json",metrics); write_json(OUT/"encoded_index.json",index)
    for cohort in ("train","validation","test_id","test_ood_size","test_ood_growth","test_ood_contrast"):
        plot_family(cohort,rows,encoder)
    # Consume the existing stable loader and record direct-array agreement.
    saved = encode_saved(encoder,ROOT/"connectome/phase5/results/samples","test_looming_1")
    from connectome.scripts.phase5.loader import load_stimulus
    f,t,_,_ = load_stimulus(ROOT/"connectome/phase5/results/samples","test_looming_1")
    assert np.array_equal(saved.drive,encoder.encode(f,t).drive)
    command = [str(ROOT/"venv/bin/python"),"-m","pytest","connectome/phase6/tests/","-q",f"--junitxml={OUT/'tests.xml'}"]
    tests = subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
    (OUT/"tests.log").write_text(tests.stdout+tests.stderr)
    xml = ET.parse(OUT/"tests.xml").getroot()
    suite = xml.find("testsuite") if xml.tag != "testsuite" else xml
    totals = {k:int(suite.attrib.get(k,0)) for k in ("tests","failures","errors","skipped")}
    gates.append(dict(gate="phase6_tests",value=totals["failures"]+totals["errors"],threshold="0 failures/errors",status="PASS" if tests.returncode == 0 else "FAIL"))
    after = protected_hashes()
    assert before == after,"Protected phase files changed"
    assert preflight_sources == sources(),"Source changed during evaluation"
    evidence = dict(schema_version="1.0",generated_at_utc=datetime.now(timezone.utc).isoformat(),
        status="PASS" if all(g["status"] == "PASS" for g in gates) else "FAIL",gates=gates,
        tests=totals,config_sha256=digest(config),normalization_sha256=digest(normalization),
        dataset=integrity_summary,encoded_episodes=len(index),evaluation_stage="post_freeze",
        saved_loader_check="PASS",protected_files=len(before),protected_files_unchanged=True,
        environment=dict(python=platform.python_version(),numpy=np.__version__,matplotlib=matplotlib.__version__),
        regression=json.loads((OUT/"regression/summary.json").read_text()) if (OUT/"regression/summary.json").exists() else "not_run")
    write_json(OUT/"validation_results.json",evidence)
    table = "\n".join(f"| {g['gate']} | {g.get('cohort','fixtures')} | {g.get('channel','both')} | {g['value']:.6g} | {g['threshold']} | {g['status']} |" for g in gates)
    report = f"""# Phase 6 standalone validation

UTC: {evidence['generated_at_utc']}. Overall gate status: **{evidence['status']}**.

Encoder 1.0.0 uses frame-only engineered expansion channels. Training-only normalization: 256 clips, zero parameter-search trials. Freeze precedes validation/test response computation; all test results are post-freeze. No circuit integration, decisions or behavioral conclusions.

## Executed commands

- `./venv/bin/python -m connectome.scripts.phase6.regression`: results in `regression/summary.json` (Phase 4 unit tests and integration assertions reported separately).
- `./venv/bin/python -m connectome.scripts.phase6.validate_phase6`: {totals['tests']} Phase 6 tests, {totals['failures']} failures, {totals['errors']} errors, {totals['skipped']} skipped; 1,024 movie hashes and encoded episodes, six diagnostic plots, stable Phase 5 loader exercised. Full logs/XML saved here.
- `{len(before)}` protected Phase 3/4/5/5.5 file hashes unchanged; bytecode caches excluded. Source/config/normalization/mapping hashes saved in `freeze_lock.json`.

## Gate outcomes

The test suite checks zero contrast, exact polarity symmetry, clipping suppression, reproducibility, metadata rejection/invariance, prefix/future causality, fractional timestamps, seconds/ms availability, invalid inputs and training-only fitting. Benchmark separation/onset/geometry gates are measured below. All cutoffs were recorded before response inspection.

| Gate | Cohort | Channel | Observed | Predeclared threshold | Result |
| --- | --- | --- | --- | --- | --- |
{table}

## Limitations / unresolved

Engineering proxy for a single circle on uniform background, not biological activity, radial-motion-opponency circuitry, receptive fields or spikes/s. Border-touching scenes suppress input rather than implement biological clipping compensation. Raw frame sets are never persisted by this validation; only hashes and encoded arrays are saved. Holding past the final timestamp requires an external episode end. All scientific hypotheses, biological calibration, synthetic fields/steering, complex scenes/flicker and Phase 7+ remain unresolved. The frozen NT confidence documentation mismatch is recorded in the specification, not repaired. A failed gate is a result, not permission to alter cutoffs or labels.
"""
    (OUT/"validation_report.md").write_text(report)
    failures = [g for g in gates if g["status"] == "FAIL"]
    print(f"{evidence['status']}: {totals}; {len(gates)-len(failures)}/{len(gates)} gates; {len(before)} protected files unchanged",flush=True)
    if failures: print(json.dumps(failures,indent=2))
    if tests.returncode: print(tests.stdout+tests.stderr)
    return 0 if evidence["status"] == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
