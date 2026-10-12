"""Read-only prior-phase checks and complete preservation inventory."""
import json
from connectome.scripts.phase8.completion.evidence import protected_hashes as older_hashes
from connectome.scripts.phase8.completion.decoder import load_freeze
from connectome.scripts.phase7.evidence import ROOT, file_hash, write_json
from .config import BASE, OUT, load_config, fixtures
from connectome.scripts.phase6.encoder import digest


def protected_hashes():
    hashes = older_hashes()
    for base in (ROOT / "connectome/phase8/completion", ROOT / "connectome/scripts/phase8/completion"):
        for p in sorted(base.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts:
                hashes[str(p.relative_to(ROOT))] = file_hash(p)
    return hashes


def verify_previous():
    f = load_freeze()
    parent = ROOT / "connectome/phase8/completion/results"
    report = json.loads((parent / "validation_results.json").read_text())
    if report["status"] != "PASS" or report["failed_gates"] or report["completion_status"] != "COMPLETE_ENGINEERING":
        raise ValueError("Phase 8 completion report failed")
    index = json.loads((parent / "delivery_artifact_index.json").read_text())
    for name, expected in index.items():
        if file_hash(ROOT / name) != expected:
            raise ValueError(f"Phase 8 delivered artifact differs: {name}")
    return dict(status="PASS", phase8_freeze_sha256=f["payload_sha256"], phase8_source_files=len(f["sources_sha256"]),
                phase8_prerequisites=len(f["prerequisite_artifacts_sha256"]), delivered_artifacts_checked=len(index),
                phase8_report_sha256=file_hash(parent / "validation_results.json"),
                scientific_limits="World domain not calibration data; synthetic retinotopy/motor assumptions and noise limits retained")


def verify_definition():
    path=OUT / "definition_lock.json"
    record=json.loads(path.read_text())
    if record["config_sha256"]!=digest(load_config()) or record["fixtures"]!=fixtures():
        raise ValueError("World definition changed after its lock")
    for name,value in record["sources_sha256"].items():
        if file_hash(ROOT/name)!=value:
            raise ValueError(f"Phase 9 source changed after definition: {name}")
    if record["parent_evidence"]!=verify_previous():
        raise ValueError("Parent evidence differs from Phase 9 definition")
    return record


if __name__ == "__main__":
    OUT.mkdir(parents=True,exist_ok=True)
    target=OUT / "preservation_before.json"
    if target.exists():
        raise FileExistsError("Before snapshot must not be overwritten")
    prior=verify_previous()
    write_json(target,protected_hashes()); write_json(OUT / "prior_evidence_checks.json",prior)
    print(prior)
