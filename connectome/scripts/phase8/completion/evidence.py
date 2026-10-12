"""Preserve the prior Phase 8 checkpoint while completing a new version."""
import json
from connectome.scripts.phase8.evidence import ROOT, PHASE, verify_previous, protected_hashes as previous_hashes
from connectome.scripts.phase7.evidence import file_hash, write_json

BASE = PHASE / "completion"
OUT = BASE / "results"


def protected_hashes():
    hashes = previous_hashes()
    for base in (PHASE, ROOT / "connectome/scripts/phase8"):
        for path in sorted(base.rglob("*")):
            relative = path.relative_to(base)
            if path.is_file() and "__pycache__" not in path.parts and relative.parts[0] != "completion":
                hashes[str(path.relative_to(ROOT))] = file_hash(path)
    return hashes


def verify_checkpoint():
    previous = verify_previous()
    report = json.loads((PHASE / "results/validation_results.json").read_text())
    if report["status"] != "PASS" or report["failed_gates"]:
        raise ValueError("Prior Phase 8 checkpoint failed")
    lock = json.loads((PHASE / "results/implementation_lock.json").read_text())
    for name, expected in lock["sources_sha256"].items():
        if file_hash(ROOT / name) != expected:
            raise ValueError(f"Prior Phase 8 source changed: {name}")
    if json.loads((PHASE / "results/preservation_after.json").read_text()) != previous_hashes():
        raise ValueError("Earlier phases changed after Phase 8 checkpoint")
    return dict(status="PASS", previous=previous, checkpoint_report_sha256=file_hash(PHASE / "results/validation_results.json"),
                checkpoint_lock_sha256=file_hash(PHASE / "results/implementation_lock.json"))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "preservation_before.json"
    if path.exists():
        raise FileExistsError("Completion before evidence must not be overwritten")
    write_json(path, protected_hashes())
    result = verify_checkpoint()
    write_json(OUT / "checkpoint_verification.json", result)
    print(result)
