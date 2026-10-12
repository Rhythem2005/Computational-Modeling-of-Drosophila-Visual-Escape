"""Decode saved Phase 7 activity using an explicitly provisional candidate."""
import argparse
import json
from pathlib import Path

from connectome.scripts.phase6.encoder import digest
from .activity_io import load_activity, save_decoded
from .decoder import InitiationDecoder, Threshold, load_config
from .evidence import OUT, file_hash, verify_previous


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activity-dir", required=True)
    parser.add_argument("--stimulus-id", required=True)
    parser.add_argument("--candidate-plan", default=str(OUT / "candidate_plan.json"))
    parser.add_argument("--out-dir", default=str(OUT / "cli_decoded"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    verify_previous()
    plan_path = Path(args.candidate_plan)
    plan = json.loads(plan_path.read_text())
    if plan.get("policy") != load_config()["threshold_policy"] or plan.get("decoder_config_sha256") != digest(load_config()):
        raise ValueError("Candidate plan differs from the amended decoder condition")
    if plan.get("final_calibration_status") != "pending_required_controls_and_validation_selection":
        raise ValueError("This CLI accepts provisional training candidates only")
    matches = [c for c in plan["candidates"] if c["candidate_id"] == plan["provisional_demo_candidate_id"]]
    if len(matches) != 1:
        raise ValueError("Provisional candidate identity is ambiguous")
    times, states, ids, duration, source = load_activity(args.activity_dir, args.stimulus_id)
    decoded = InitiationDecoder(Threshold(**matches[0]["threshold"])).decode_activity(times, states, ids, duration)
    source.update(candidate_plan_sha256=file_hash(plan_path), candidate_id=matches[0]["candidate_id"])
    paths = save_decoded(args.out_dir, args.stimulus_id, decoded, source, overwrite=args.overwrite)
    print(json.dumps(decoded.action(), allow_nan=False))
    print(f"Saved decoded request traces to {paths[0]}")


if __name__ == "__main__":
    main()
