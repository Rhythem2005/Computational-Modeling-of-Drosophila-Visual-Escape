"""Read-only verification and preservation evidence for Phase 7."""
import hashlib
import json
from pathlib import Path

from connectome.scripts.phase6.encoder import ROOT, PHASE, digest, load_config, load_mapping

OUT = ROOT / "connectome/phase7/results"


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def protected_hashes():
    paths = []
    for phase in ("phase1", "phase2", "phase3", "phase4", "phase5", "phase5_5", "phase6"):
        for base in (ROOT / "connectome" / phase, ROOT / "connectome/scripts" / phase):
            paths.extend(p for p in base.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    paths.extend(p for p in (ROOT / "connectome/data/phase1").rglob("*") if p.is_file())
    paths.extend(ROOT / name for name in ("README.md", "config.yaml", "requirements.txt"))
    pdf = ROOT / "output/pdf/FLY_Project_Progress_Through_Phase_6.pdf"
    if pdf.exists():
        paths.append(pdf)
    return {str(p.relative_to(ROOT)): file_hash(p) for p in sorted(set(paths))}


def verify_frozen():
    """Validate existing locks without regenerating or fitting anything."""
    protocol = json.loads((ROOT / "connectome/phase5_5/results/protocol_lock.json").read_text())
    lock = json.loads((PHASE / "results/freeze_lock.json").read_text())
    checked = {}
    for saved in (protocol["sources_sha256"], protocol["protected_phase3_to5_sha256"],
                  lock["sources_sha256"], lock["protected_sha256"]):
        for name, expected in saved.items():
            if file_hash(ROOT / name) != expected:
                raise ValueError(f"Frozen file mismatch: {name}")
            checked[name] = expected
    manifest = json.loads((ROOT / "connectome/phase5_5/results/benchmark_manifest.json").read_text())
    normalization = json.loads((PHASE / "results/normalization.json").read_text())
    integrity = json.loads((PHASE / "results/dataset_integrity.json").read_text())
    for key, value in (("config_sha256", load_config()), ("normalization_sha256", normalization),
                       ("mapping_sha256", load_mapping()), ("manifest_sha256", manifest),
                       ("dataset_integrity_sha256", integrity["records"])):
        if digest(value) != lock[key]:
            raise ValueError(f"Phase 6 freeze mismatch: {key}")
    if digest(manifest) != protocol["manifest_sha256"]:
        raise ValueError("Protocol manifest mismatch")
    from connectome.scripts.phase5_5.protocol import load_design, validate_manifest
    from connectome.scripts.phase6.dataset import check_isolation
    validate_manifest(manifest, load_design())
    if check_isolation(integrity["records"]) != integrity["summary"]:
        raise ValueError("Dataset isolation summary mismatch")
    if digest(json.loads((PHASE / "results/mapping.json").read_text())) != lock["mapping_sha256"]:
        raise ValueError("Saved mapping mismatch")
    if len(normalization["training_records"]) != 256 or any(
            r["split"] != "train" or r["cohort"] != "train" for r in normalization["training_records"]):
        raise ValueError("Normalization provenance must be training only")
    if digest(normalization["training_records"]) != normalization["training_records_sha256"]:
        raise ValueError("Normalization training provenance mismatch")
    index = json.loads((PHASE / "results/encoded_index.json").read_text())
    if len(index) != 1024 or len({r["scenario_id"] for r in index}) != 1024:
        raise ValueError("Encoded index count/identity mismatch")
    if {r["scenario_id"] for r in index} != {r["scenario_id"] for r in manifest["scenarios"]}:
        raise ValueError("Encoded index/manifest identity mismatch")
    for row in index:
        if file_hash(PHASE / row["path"]) != row["sha256"] or row["freeze_lock_sha256"] != file_hash(PHASE / "results/freeze_lock.json"):
            raise ValueError(f"Frozen encoded artifact mismatch: {row['scenario_id']}")
    return dict(status="PASS", checked_locked_files=len(checked), encoded_files_checked=len(index),
                normalization_sha256=lock["normalization_sha256"], scales=normalization["scales"],
                phase6_freeze_lock_sha256=file_hash(PHASE / "results/freeze_lock.json"),
                manifest_sha256=digest(manifest))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "preservation_before.json"
    if target.exists():
        raise FileExistsError("Do not overwrite the before snapshot")
    write_json(target, protected_hashes())
    result = verify_frozen()
    write_json(OUT / "prior_evidence_checks.json", result)
    print(result)
