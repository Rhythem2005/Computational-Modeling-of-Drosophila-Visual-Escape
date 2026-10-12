# Phase 9 — closed-loop engineering environment v1.0

[Plan](plan.md), [research notes](research_notes.md), [separate protocol](protocol.md), [environment config](environment_config.yaml), [validation report](results/validation_report.md).

The deterministic planar world projects current relative geometry into 60 Hz images and connects them causally to the frozen encoder, Circuit v2 dynamics and Phase 8 decoder. A first request schedules bounded backward/lateral translation after a fixed delay; movement changes later visual inputs. Geometry-based collision danger, finite-horizon survival, escape success, false alarms, latency, clearance and movement cost have explicit definitions. All units and actuator parameters are engineered, not fly calibration. The primary uniform condition remains directionally neutral; five separate synthetic mapping seeds retain their original limitations.

The original open-loop benchmark/protocol is unchanged. Phase 9 runs fixed engineering fixtures only, with no threshold fitting, benchmark test use, shuffled/NN networks, statistical experiments or Phase 10 implementation.

## Run with the existing virtual environment

```bash
MPLCONFIGDIR=/tmp/fly-phase9-mpl ./venv/bin/python -m connectome.scripts.phase9.launch --task validate
MPLCONFIGDIR=/tmp/fly-phase9-mpl ./venv/bin/python -m connectome.scripts.phase9.launch --task run -- --fixture world_head_on
MPLCONFIGDIR=/tmp/fly-phase9-mpl ./venv/bin/python -m connectome.scripts.phase9.launch --task run -- --fixture world_left --condition synthetic_fields_within_type_and_side_v1 --seed 55010
```

Add `--overwrite` after the separator for an existing episode ID. Saved numerical traces, config, actions and metrics must match recorded results on reproduction; overwrite does not permit changing a recorded condition under the same ID. Programmatic interfaces are `World`, `ClosedLoopRunner`, `render_camera`, `stationary_danger`, `save_episode` and `load_episode`.

## Compatibility with the user's Git changes

During Phase 9 planning, the user pushed Phase 6 and stashed later phases. Missing Phase 7/8/planning files were recovered byte-for-byte from that local stash without popping it or changing branch/commits. The user also updated the root README and removed legacy Phase 1 duplicate paths. Earlier freeze inventories require the archival README and original Phase 1 paths. The launcher therefore copies frozen parents into a temporary execution snapshot, substitutes only the original verified README there, and recovers missing legacy Phase 1 bytes there from verified local Git history. The current repository README, branch, stash and Phase 1 cleanup are left intact. [Recovery record](recovery_record.json) documents restored files; `results/execution_snapshot.json` records the copy, commands and hashes. No new dependencies are installed.

Both execution-snapshot before/after inventories and original-workspace before/after inventories are saved. Original parent artifacts must remain unchanged during execution; archival replacements occur only in the copy. Phase 9 source/config/results live in this repository; only Phase 9 results are copied back. Frozen model/source/result changes are rejected. Existing earlier validators are never run to regenerate parent outputs. Reproduction uses the launcher while this README/legacy-path compatibility difference exists.

## Saved schema and limitations

Schema1.0 NPZ stores world positions/time/speed, exact camera frames/timestamps, body IDs, full neural and ten-DN states, causal held drive/scaled input/frame indices, score/persistence/event/latch and turn arrays. Config/action/metrics/metadata JSON preserve identity, mapping, calibration, units, endpoint interpretation and hashes. Loader checks hashes and does not allow pickle. Collision may end between neural ticks: world ends at contact; no future neural state or post-terminal decision is saved. Horizon contact counts as failure even though a decoder event at1s is excluded.

Plots show trajectories, clearance/score/timing, action-dependent observations and all five synthetic seeds. Fixed fixture outcomes are integration evidence, not an estimate of general escape performance. World images are a new domain outside the decoder's open-loop calibration. Multiple/clipped silhouettes, stabilized camera, billboard projection, fixed backward escape plant, synthetic retinotopy/motor mapping and one-float silence thresholds are explicit scientific limits. Permanent safety, biological fidelity and detailed-wiring advantage remain unestablished. No commit or push is performed by this phase.
