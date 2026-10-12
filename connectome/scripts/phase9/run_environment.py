"""CLI for frozen-model engineering world fixtures, with no fitting."""
import argparse
import json
from pathlib import Path
from .config import fixtures, OUT
from .runner import ClosedLoopRunner
from .activity_io import save_episode
from .evidence import verify_definition


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--fixture",choices=[s["scenario_id"] for s in fixtures()],default="world_head_on")
    parser.add_argument("--condition",choices=["uniform_population","synthetic_fields_within_type_and_side_v1"],default="uniform_population")
    parser.add_argument("--seed",type=int)
    parser.add_argument("--out-dir",type=Path,default=OUT / "cli_episodes")
    parser.add_argument("--overwrite",action="store_true")
    args=parser.parse_args()
    verify_definition()
    scenario=next(s for s in fixtures() if s["scenario_id"]==args.fixture)
    run=ClosedLoopRunner().run(scenario,condition=args.condition,seed=args.seed)
    name=args.fixture+("_primary" if args.seed is None else f"_spatial_s{args.seed}")
    paths=save_episode(args.out_dir,name,run,overwrite=args.overwrite)
    print(json.dumps(dict(episode_id=name,metrics=run["metrics"],paths=[str(p) for p in paths]),indent=2))


if __name__ == "__main__":
    main()
