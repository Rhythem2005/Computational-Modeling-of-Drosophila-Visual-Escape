"""Fixed engineering validation, frozen model replay, and preservation evidence."""
from datetime import datetime,timezone
import json
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from connectome.scripts.phase6.encoder import digest
from connectome.scripts.phase8.completion.spatial import assign_fields
from .config import BASE,OUT,load_config,fixtures
from .evidence import ROOT,protected_hashes,verify_previous,file_hash,write_json
from .regression import run as regression
from .runner import ClosedLoopRunner
from .world import World,render_camera
from .activity_io import save_episode,load_episode


def stable_json(path,data):
    if path.exists() and json.loads(path.read_text()) != data:
        raise ValueError(f"Recorded definition/result changed: {path}")
    write_json(path,data)


def coupling_check(config):
    on=World(config,fixtures()[0]);off=World(config,fixtures()[0])
    for _ in range(300):on.step();off.step()
    before_on,_=render_camera(config,on.fly,on.obstacles,on.radii)
    before_off,_=render_camera(config,off.fly,off.obstacles,off.radii)
    np.testing.assert_array_equal(before_on,before_off)
    on.request(0)
    for _ in range(100):on.step();off.step()
    after_on,_=render_camera(config,on.fly,on.obstacles,on.radii)
    after_off,_=render_camera(config,off.fly,off.obstacles,off.radii)
    if np.array_equal(after_on,after_off):raise ValueError("No action-to-visual-input coupling")
    arrays=dict(before_on=before_on,before_off=before_off,after_on=after_on,after_off=after_off,
                fly_on=on.fly,fly_off=off.fly)
    path=OUT / "coupling_check.npz"
    if path.exists():
        with np.load(path,allow_pickle=False) as old:
            for k,v in arrays.items():np.testing.assert_array_equal(old[k],v)
    else:np.savez_compressed(path,**arrays)
    report=dict(status="PASS",request_ms=300,before_frame_ms=300,after_frame_ms=400,scripted_turn=0,
                before_frames_equal=True,after_frames_differ=True,pixels_differ=int(np.count_nonzero(after_on!=after_off)),
                fly_displacement_difference=float(np.linalg.norm(on.fly-off.fly)),
                interpretation="scripted plumbing check only; no controller baseline, tuning or efficacy comparison")
    stable_json(OUT / "coupling_check.json",report)
    return arrays,report


def make_plots(runs,coupling):
    paths=[]
    head=runs["world_head_on_primary"];a=head["arrays"]
    fig,axes=plt.subplots(1,3,figsize=(14,4))
    axes[0].plot(a["fly_position"][:,0],a["fly_position"][:,1],label="fly")
    axes[0].plot(a["obstacle_positions"][:,0,0],a["obstacle_positions"][:,0,1],label="object")
    axes[0].set_xlabel("World x (abstract)");axes[0].set_ylabel("World y (abstract)");axes[0].legend();axes[0].set_aspect("equal",adjustable="datalim")
    clearance=np.linalg.norm(a["obstacle_positions"][:,0]-a["fly_position"],axis=1)-2
    axes[1].plot(a["world_times_ms"]/1000,clearance,label="sampled clearance")
    axes[1].axhline(0,color="tab:red",linestyle="--",label="contact")
    axes[1].set_ylabel("World units");axes[1].set_xlabel("Time (s)");axes[1].legend(fontsize=8)
    axes[2].plot(a["decision_times_ms"]/1000,a["score"],label="DNp01 score")
    axes[2].plot(a["decision_times_ms"]/1000,a["sustained_score"],"--",label="20 ms minimum")
    axes[2].set_ylabel("Arbitrary activity");axes[2].set_xlabel("Time (s)")
    for key,color in (("first_request_ms","tab:red"),("first_motion_ms","tab:green")):
        if head["metrics"][key] is not None:axes[2].axvline(head["metrics"][key]/1000,color=color,linestyle=":",label=key)
    axes[2].legend(fontsize=7)
    for ax in axes:ax.grid(alpha=.2)
    fig.suptitle("Head-on primary engineering fixture; fixed backward escape plant, no calibrated behavior claim")
    fig.tight_layout();p=OUT / "plots/primary_world_activity.png";fig.savefig(p,dpi=140);plt.close(fig);paths.append(p)
    fig,axes=plt.subplots(2,2,figsize=(7,7))
    for ax,key,title in zip(axes.flat,("before_on","before_off","after_on","after_off"),
                             ("300 ms: before scripted action","300 ms: same world without action","400 ms: action changes relative view","400 ms: no-action plumbing fixture")):
        ax.imshow(coupling[key],cmap="gray",vmin=0,vmax=255);ax.set_title(title,fontsize=9);ax.axis("off")
    fig.suptitle("Action-to-observation coupling check; scripted interface test")
    fig.tight_layout();p=OUT / "plots/action_visual_coupling.png";fig.savefig(p,dpi=140);plt.close(fig);paths.append(p)
    fig,axes=plt.subplots(1,2,figsize=(10,5))
    for ax,side in zip(axes,("left","right")):
        for seed in load_config()["spatial_seeds"]:
            run=runs[f"world_{side}_spatial_s{seed}"];a=run["arrays"]
            ax.plot(a["fly_position"][:,0],a["fly_position"][:,1],label=f"{seed}: turn {run['metrics']['turn']:.2f}")
        ax.set_title(f"{side} approaching object");ax.set_xlabel("World x (abstract)");ax.set_ylabel("World y (abstract)");ax.legend(fontsize=8);ax.grid(alpha=.2);ax.set_aspect("equal",adjustable="datalim")
    fig.suptitle("All five synthetic spatial mappings; engineered steering with reused threshold")
    fig.tight_layout();p=OUT / "plots/synthetic_escape_paths.png";fig.savefig(p,dpi=140);plt.close(fig);paths.append(p)
    return paths


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for name in ("episodes","plots","mappings"):(OUT / name).mkdir(exist_ok=True)
    before=json.loads((OUT / "preservation_before.json").read_text())
    if before != protected_hashes():raise ValueError("Frozen execution parents changed since before snapshot")
    previous=verify_previous();config=load_config();scenarios=fixtures()
    sources={str(p.relative_to(ROOT)):file_hash(p) for base in (BASE,ROOT / "connectome/scripts/phase9") for p in sorted(base.rglob("*"))
             if p.is_file() and "results" not in p.parts and "__pycache__" not in p.parts}
    definition=dict(version="1.0.0",protocol_id=config["protocol_id"],config=config,config_sha256=digest(config),fixtures=scenarios,
                    sources_sha256=sources,parent_evidence=previous,threshold_fitting=False,benchmark_test_use=False,
                    statistical_experiment=False,definition_saved_before_engineering_model_outcomes=True)
    lock=OUT / "definition_lock.json"
    # Source-only development repairs are logged; condition definitions cannot change
    # after first unit/model outcomes. A completed definition is immutable.
    if lock.exists() and json.loads(lock.read_text()) != definition:
        old=json.loads(lock.read_text());report=OUT / "validation_results.json"
        if report.exists() and json.loads(report.read_text()).get("status")=="PASS":
            raise ValueError("Completed Phase 9 source definition differs")
        if any(old[k]!=definition[k] for k in definition if k!="sources_sha256"):
            raise ValueError("World/protocol conditions changed after definition; explicit new version required")
        repairs=OUT / "development_repairs.json"
        history=json.loads(repairs.read_text()) if repairs.exists() else []
        history.append(dict(previous_definition=old,repaired_definition=definition,time_utc=datetime.now(timezone.utc).isoformat(),reason="Source-only correctness repair; model/world/fixture definitions unchanged"))
        write_json(repairs,history)
    write_json(lock,definition)
    runner=ClosedLoopRunner(config)
    for seed in config["spatial_seeds"]:
        stable_json(OUT / "mappings" / f"seed_{seed}.json",assign_fields(runner.pipeline.encoder.mapping["nodes"],seed))
    command=[sys.executable,"-m","pytest","connectome/phase9/tests/","-q",f"--junitxml={OUT / 'tests.xml'}"]
    tests=subprocess.run(command,cwd=ROOT,capture_output=True,text=True);(OUT / "tests.log").write_text(tests.stdout+tests.stderr)
    counts={k:sum(int(s.attrib.get(k,0)) for s in ET.parse(OUT / "tests.xml").getroot().iter("testsuite")) for k in ("tests","failures","errors","skipped")}
    if tests.returncode or any(counts[k] for k in ("failures","errors","skipped")):
        write_json(OUT / "development_failure.json",dict(status="FAIL",stage="tests",counts=counts,exit_code=tests.returncode))
        print(tests.stdout+tests.stderr,flush=True);raise RuntimeError("Phase 9 tests failed; no fixture omitted")
    print("Phase 9 tests:",counts,flush=True)
    baseline=json.loads((OUT / "regression/before/summary.json").read_text());after_regression=regression("after")
    if baseline["status"]!=after_regression["status"] or after_regression["status"]!="PASS" or baseline["tests"]!=after_regression["tests"] or baseline["phase4_assertions"]!=after_regression["phase4_assertions"]:
        raise RuntimeError("Parent regressions differ")
    jobs=[(s,"uniform_population",None) for s in scenarios]
    jobs += [(s,config["secondary_condition"],seed) for seed in config["spatial_seeds"] for s in scenarios if s["scenario_id"] in ("world_left","world_right")]
    runs={}; summaries=[]
    for scenario,condition,seed in jobs:
        sid=scenario["scenario_id"]+("_primary" if seed is None else f"_spatial_s{seed}")
        try:
            run=runner.run(scenario,condition=condition,seed=seed);repeat=runner.run(scenario,condition=condition,seed=seed)
            if run["metrics"]!=repeat["metrics"] or run["action"]!=repeat["action"]:raise ValueError("World repeat outcome differs")
            for k,v in run["arrays"].items():np.testing.assert_array_equal(v,repeat["arrays"][k])
            paths=save_episode(OUT / "episodes",sid,run,overwrite=True)
            if run["metrics"]["activation_clipped_fraction"]!=0 or run["metrics"]["direct_dn_input_max"]!=0:
                raise ValueError("Frozen neural numerical contract failed")
            runs[sid]=run;summaries.append(dict(episode_id=sid,metrics=run["metrics"],action=run["action"],repeat_bitwise=True,
                                               artifacts={str(p.relative_to(ROOT)):file_hash(p) for p in paths[:4]}))
            print(sid,"request",run["metrics"]["first_request_ms"],"success",run["metrics"]["escape_success"],"false_alarm",run["metrics"]["false_alarm"],flush=True)
        except Exception as error:
            write_json(OUT / "fixture_failure.json",dict(status="FAIL",episode_id=sid,error=str(error),completed=len(summaries),no_exclusion_or_replacement=True))
            raise
    stable_json(OUT / "episode_results.json",summaries)
    coupling,coupling_report=coupling_check(config)
    cli_command=[sys.executable,"-m","connectome.scripts.phase9.run_environment","--fixture","world_head_on","--overwrite"]
    cli=subprocess.run(cli_command,cwd=ROOT,capture_output=True,text=True);(OUT / "cli.log").write_text(cli.stdout+cli.stderr)
    if cli.returncode:raise RuntimeError("Environment CLI failed")
    cli_run=load_episode(OUT / "cli_episodes","world_head_on_primary")
    for k,v in runs["world_head_on_primary"]["arrays"].items():np.testing.assert_array_equal(v,cli_run["arrays"][k])
    if cli_run["metrics"]!=runs["world_head_on_primary"]["metrics"]:raise ValueError("CLI metrics differ")
    write_json(OUT / "cli_verification.json",dict(status="PASS",command=cli_command,array_and_metrics_equality=True))
    plots=make_plots(runs,coupling)
    after=protected_hashes();write_json(OUT / "preservation_after.json",after)
    if before != after:raise ValueError("Earlier frozen execution files changed")
    report=dict(status="PASS",completion_status="COMPLETE_ENGINEERING",protocol_id=config["protocol_id"],run_time_utc=datetime.now(timezone.utc).isoformat(),
                invocation=[sys.executable,*sys.argv],tests=counts,tests_command=command,earlier_regression=after_regression,
                fixed_engineering_fixtures=15,repeat_runs=15,spatial_mapping_seeds=config["spatial_seeds"],failed_gates=[],
                episode_results_sha256=file_hash(OUT / "episode_results.json"),definition_lock_sha256=file_hash(lock),
                protected_execution_files=len(before),protected_execution_files_unchanged=True,action_visual_coupling=coupling_report,
                streamed_batch_neural_and_decoder_equal=True,saved_round_trips=True,cli_status="PASS",
                world_threshold_fitting=False,benchmark_test_neural_or_decision_runs=0,phase10_implementation=False,
                calibration_scope=config["calibration_scope"],biological_fidelity_claim=False,
                plots={str(p.relative_to(ROOT)):file_hash(p) for p in plots},environment=dict(python=platform.python_version(),numpy=np.__version__,matplotlib=matplotlib.__version__))
    write_json(OUT / "validation_results.json",report)
    rows="\n".join(f"| {r['episode_id']} | {r['metrics']['danger']} | {r['metrics']['first_request_ms']} | {r['metrics']['turn']:.4g} | {r['metrics']['escape_success']} | {r['metrics']['false_alarm']} | {r['metrics']['final_clearance']:.4g} |" for r in summaries)
    (OUT / "validation_report.md").write_text(f"""# Phase 9 engineering validation v1.0

Status **PASS / COMPLETE_ENGINEERING**. UTC {report['run_time_utc']}. Scope: deterministic abstract planar world, bounded delayed escape actuator, relative camera, causal frozen-model coupling and geometry-based metrics. The separate protocol/plan/config and five fixtures were fixed before outcomes. Parent open-loop protocol, encoding normalization, circuit, dynamics and decoder calibration were not tuned.

## Implementation and evidence actually run

The stabilized camera uses pinhole-style circular billboards rendered by the existing Phase 5 rasterizer. World positions change after a decoder request, and therefore change subsequent frames. The first request latches backward/lateral translation, with fixed20 ms delay, acceleration400 and speed cap20 in abstract units. No body yaw, camera rotation or flight biomechanics is implied. Frame prefixes alone enter the frozen encoder; world geometry/danger remain evaluator-only. Strict 60 Hz availability feeds the existing 1 ms Euler step, with scale0.4 applied once. Phase 8 bounded-history streaming initiation and normalized DNp06 steering agree exactly with their batch interfaces.

- **{counts['tests']} Phase 9 tests passed**, zero failures/errors/skips. Tests cover geometry/tangency/tunneling, initial/fractional/horizon collision, boundary failure, delay/latch/bounds, projection, dangerous versus safe geometry, streamed/batch full neural states, decoder/drive equivalence, causal pre-onset prefixes, fractional frame timing, all five seeds, deterministic replay and saved/hash/path guards.
- **{after_regression['tests']['tests']} existing tests and {after_regression['phase4_assertions']['passed']} Phase 4 integration assertions passed before and after**, with unchanged counts. Outputs were redirected into Phase 9; earlier-output-writing validators were not run.
- Ran all five primary world fixtures plus both side fixtures for all five synthetic seeds: **15 fixed model runs and 15 exact repeat runs**, no excluded/failing fixture. Saved full world/frame/neural/DN/input/decision traces, configs, actions and per-episode metrics. Every neural run was finite, direct DN input zero, and activation clipping zero. Saved arrays/JSON/hash checks passed. World input differs from original benchmark observations; thresholds were reused, not refitted or claimed calibrated for this domain.
- Ran a scripted action-on/action-off plumbing check: equal frames at300 ms before the command, then {coupling_report['pixels_differ']} differing pixels and {coupling_report['fly_displacement_difference']:.6g} world-unit position difference at400 ms. This verifies action-to-future-input coupling; it is not a controller baseline or efficacy estimate.
- Executed the environment CLI on the head-on fixture: arrays and metrics equal integrated output. Inspected/recorded plots separately in delivery evidence. Runtime commands and versions are in JSON/logs/XML.
- **{len(before)} frozen execution files unchanged** by before/after SHA-256 inventory. The launcher also verifies the actual repository parents before/after and records the isolated execution snapshot. No dependency installation, commit or push was performed by Phase 9.

## Fixed fixture outcomes

| Fixture/condition | Stationary-fly danger | First request ms | Turn | Escape success | False alarm | Final clearance |
| --- | --- | --- | --- | --- | --- | --- |
{rows}

Metrics use geometric stationary-fly contact as danger, not expansion. Success is defined only for dangerous fixtures, requiring timely request, survival through the inclusive1s horizon and final clearance>=1. Harmless episodes have success=None and are not counted as successful escapes. Pre-onset requests, misses, minimum swept clearance, path length, actuation/motion times and failure details are saved per episode. Collision/boundary termination differs from horizon truncation. Physical horizon contact counts as failure; a decoder event at1s remains excluded. No post-terminal decision or future neural state is saved.

## Reproduction and compatibility

Run `MPLCONFIGDIR=/tmp/fly-phase9-mpl ./venv/bin/python -m connectome.scripts.phase9.launch --task validate`. Definition/model/source changes after completion are rejected; numerical traces and outcomes must match saved values. Deterministic reruns are not independent trials. See the Phase 9 README for CLI use and schema1.0.

The user pushed Phase 6 during planning, stashed later phases, updated root README and removed legacy Phase 1 paths. Missing Phase 7/8/planning files were restored from the local stash without popping it. Earlier strict freezes include the original README/legacy paths, so the launcher uses a temporary snapshot with exact verified archival bytes. Current README, branch, stash and Phase 1 cleanup remain intact. `execution_snapshot.json` and workspace preservation inventories distinguish original workspace evidence from frozen execution evidence. Only Phase 9 results are copied back.

## Unresolved scientific issues and boundaries

This is engineering completion of Phase 9, not a behavioral performance experiment. The five fixtures are not a representative held-out distribution; the original benchmark test cohorts were unused. World-domain primary calibration and separate spatial calibration remain unestablished. Synthetic retinotopy, DN motor interpretation, billboard/stabilized-camera/translation-plant assumptions and tiny silence thresholds require later robustness work. Multiple silhouettes and image-edge clipping can invalidate the frozen encoder and remain visible in diagnostics. Finite-horizon survival is not permanent safety. No biological movement calibration, wiring advantage, H1/H2 assessment, shuffled/NN control or Phase 10 implementation occurred. Historical Phase 0 evidence/PDF gaps and earlier specification discrepancies remain preserved.
""")
    print(f"PASS / COMPLETE_ENGINEERING: {counts['tests']} Phase 9 tests, 15 fixtures plus repeats, {len(before)} frozen execution files unchanged",flush=True)


if __name__ == "__main__":main()
