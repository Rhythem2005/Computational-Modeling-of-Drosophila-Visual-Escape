"""Phase 8 read-only preflight and earlier-phase preservation."""
import json
from connectome.scripts.phase7.evidence import ROOT, protected_hashes as earlier_hashes, file_hash, write_json, verify_frozen

PHASE = ROOT / "connectome/phase8"
OUT = PHASE / "results"


def protected_hashes():
    hashes = earlier_hashes()
    for base in (ROOT / "connectome/phase7", ROOT / "connectome/scripts/phase7"):
        for path in sorted(base.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                hashes[str(path.relative_to(ROOT))] = file_hash(path)
    return hashes


def verify_previous():
    phase6 = verify_frozen()
    saved = ROOT / "connectome/phase7/results"
    report = json.loads((saved / "validation_results.json").read_text())
    if report["status"] != "PASS" or report["failed_gates"]:
        raise ValueError("Phase 7 saved validation is not passing")
    config = json.loads((saved / "run_configuration.json").read_text())
    for name, expected in config["sources_sha256"].items():
        if file_hash(ROOT / name) != expected:
            raise ValueError(f"Phase 7 source changed: {name}")
    episodes = json.loads((saved / "episode_results.json").read_text())
    for episode in episodes:
        for name, expected in episode["artifacts"].items():
            if file_hash(ROOT / name) != expected:
                raise ValueError(f"Phase 7 saved activity changed: {name}")
    for name, expected in report["plots"].items():
        if file_hash(ROOT / name) != expected:
            raise ValueError(f"Phase 7 plot changed: {name}")
    previous = json.loads((saved / "preservation_after.json").read_text())
    if previous != earlier_hashes():
        raise ValueError("Earlier phases changed after Phase 7")
    return dict(status="PASS", phase6=phase6, phase7_source_files=len(config["sources_sha256"]),
                phase7_saved_episodes=len(episodes), phase7_validation_sha256=file_hash(saved / "validation_results.json"))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "preservation_before.json"
    if target.exists():
        raise FileExistsError("Before snapshot already exists; do not overwrite")
    write_json(target, protected_hashes())
    result = verify_previous()
    write_json(OUT / "prior_evidence_checks.json", result)
    print(result)
