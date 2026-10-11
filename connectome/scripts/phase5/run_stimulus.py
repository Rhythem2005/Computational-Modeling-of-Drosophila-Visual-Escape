"""CLI: python -m connectome.scripts.phase5.run_stimulus --config PATH."""
import argparse
from pathlib import Path
from .config import load_config
from .generator import generate_stimulus
from .stimulus_io import save_stimulus

DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "phase5" / "results" / "samples"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    c = load_config(args.config)
    frames, timestamps = generate_stimulus(c)
    paths = save_stimulus(args.out_dir, c, frames, timestamps, overwrite=args.overwrite)
    print(f"Generated {len(timestamps)} frames: {frames.shape}, {frames.dtype}; {paths[0]}")


if __name__ == "__main__":
    main()
