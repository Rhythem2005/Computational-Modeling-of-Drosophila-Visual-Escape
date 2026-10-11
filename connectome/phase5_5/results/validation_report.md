# Phase 5.5 — validation report

Generated: 2026-10-11T10:15:02.707524+00:00. Base Git commit: `fe50a78c80d20f653e59523fa90c96bcccaf9d3f`.

## Completed

Local research protocol, evidence/assumption register, Phase 6 handoff, versioned benchmark design, deterministic manifest generation, and protocol integrity tests. This is a research-design phase; no encoder, neural experiment, steering model, or behavioral outcome was implemented or measured.

## Commands and outcomes

- `./venv/bin/python -m pytest connectome/phase5_5/tests/ -q`: 44 Phase 5.5 tests passed.
- `./venv/bin/python -m pytest connectome/phase5/tests/ connectome/phase5_5/tests/ -q`: 158 tests, 0 failures, 0 errors, 0 skipped (runner repeats this command and also saves JUnit XML).
- `./venv/bin/python -m connectome.scripts.phase5_5.validate_protocol`: PASS. Validated 1024 planned configurations in 256 matched families; regenerated the manifest identically; inspected 24 rendered clips (four roles from each of six cohorts).
- Sample checks: THW uint8 frames, float64 frame timestamps, declared intensities, static/initial/terminal matching, monotonic looming, translating trajectory and raster centroid agreement, and absence of clipping. Per-sample hashes, endpoint areas, intensity values and timing are in `validation_results.json`.
- SHA-256 checks: 130 protected files in Phase 3–5 outputs and scripts unchanged during validation. `protocol_lock.json` records their hashes and protocol source hashes.

## Limitations and unresolved work

The lock is local, not external preregistration or a sealed test set. No visual-angle calibration or biological receptive-field mapping is available. Parameter fingerprints rule out identical configs, not every possible identical raster movie; full movie deduplication is a required later gate. Sample rendering covers 24 of 1,024 planned clips, not all clips. The cohort sizes are computational budgets, not a power guarantee. Primary uniform-population encoding cannot establish directional steering. Biological input calibration, actual encoder behavior, decoder thresholds, model controls and research hypotheses remain untested until their later phases. Protected hashes check file integrity, not independent biological validity.

Phase 5.5 deliverables are complete under the documented protocol-only scope. No Phase 6 work, commit or push was performed by this validation command.
