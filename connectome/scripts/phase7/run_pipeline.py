"""CLI for existing schema-1.0 Phase 5 movies."""
import argparse
from .evidence import OUT
from .pipeline import FrozenPipeline, save_run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stimulus-dir", required=True)
    parser.add_argument("--stimulus-id", required=True)
    parser.add_argument("--out-dir", default=str(OUT / "activity"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    pipeline = FrozenPipeline()
    run = pipeline.run_saved(args.stimulus_dir, args.stimulus_id)
    paths = save_run(args.out_dir, args.stimulus_id, run, overwrite=args.overwrite)
    print(f"Saved {len(run.times_ms)} state samples × {run.states.shape[1]} neurons to {paths[0]}")
    print(f"Finite={run.metrics['finite']}; clipped activation fraction={run.metrics['activation_clipped_fraction']}")


if __name__ == "__main__":
    main()
