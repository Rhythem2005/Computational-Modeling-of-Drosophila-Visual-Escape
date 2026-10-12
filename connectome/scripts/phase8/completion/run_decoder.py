"""Run the final calibrated primary decoder on saved Phase 7 activity."""
import argparse
import json
from connectome.scripts.phase8.activity_io import load_activity
from .decoder import CalibratedDecoder
from .activity_io import save_action
from .evidence import OUT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activity-dir", required=True)
    parser.add_argument("--stimulus-id", required=True)
    parser.add_argument("--out-dir", default=str(OUT / "cli_actions"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    model = CalibratedDecoder()
    t, x, ids, duration, source = load_activity(args.activity_dir, args.stimulus_id)
    decoded, steering, action = model.decode_activity(t, x, ids, duration)
    paths = save_action(args.out_dir, args.stimulus_id, decoded, steering, action, source, overwrite=args.overwrite)
    print(json.dumps(action, allow_nan=False))
    print(paths[0])


if __name__ == "__main__":
    main()
