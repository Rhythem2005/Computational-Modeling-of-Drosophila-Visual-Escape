# Phase 5 validation report

Validated at 2026-10-11T09:12:57.141256+00:00. Automated acceptance checks passed.

## Changes and justification / regression coverage

| Change | Concrete gap addressed / tests |
| --- | --- |
| Validate generation, config, rendering and saves | Prevent invalid types, NaN/Inf, intensity wrapping, empty runs, memory exhaustion and unsafe IDs; `test_invalid_config`, `test_entry_points`, `test_memory_budget`, `test_defaults`. |
| Share analytic trajectories | Correct onset clamping and collision validation; `test_directions`, `test_delayed_motion`, `test_looming_exact`, `test_looming_constraints`. |
| Version metadata and verify hashes/snapshots | Detect inconsistent arrays, metadata or files; `test_metadata_contract`, `test_tampering`, `test_legacy`, `test_save_checks`. |
| CLI and saved examples | Provide reproducible outputs beyond plots; `test_cli`, `test_diagnostics`. |
| Valid fast looming and Agg plotting; retain unrelated PNGs | Old diagnostic crossed collision and default backend crashed; `test_diagnostics`, `test_old_fast_invalid`. |
| Evidence-derived report and UTC timestamps | Remove hard-coded completion claims and deprecated timestamp API; this validation runner and `test_metadata_contract`. |

## Execution evidence

- `./venv/bin/python -m pytest connectome/phase5/tests/ -q --junitxml=connectome/phase5/results/unit_tests.xml`: 114 passed, 0 failures, 0 errors, 0 skipped.
- `./venv/bin/python -m connectome.scripts.phase5.validate_phase5`: tests plus 7 saved samples verified by exact loader round trip, 7 diagnostic plots generated. Looming radii are nondecreasing and within 1 px of analytic radius; translating centroid errors are below 1 px. See `results/sample_verification.json` for measurements.
- 66 Phase 3/4 files matched their pre-validation hashes. The baseline is saved in `results/protected_file_hashes.json`.
- `./venv/bin/python -m connectome.scripts.phase5.generate_report`: produces this report from saved evidence; it rejects recorded failures.

## Assumptions and limitations

One circle per run; instantaneous hard-edged grayscale frames with clipping at image boundaries. Frame count is floor(duration_s * fps), timestamps are i/fps, and zero-frame runs are invalid. Looming is a physically motivated pinhole projection using abstract distances; no calibrated fly visual angles or retinotopy. No motion blur, anti-aliasing or stochastic rendering. The seed records provenance. Visibility/clipping can prevent area-equivalent radius or centroid from representing the full analytic object. Metadata generation date varies, while frame/timestamp hashes and config hashes are reproducible. Frame arrays are limited to 256 MiB.

## Unresolved

Automated checks have no unresolved failures. Plot visual inspection and session-wide Git/hash checks are recorded separately in `results/session_inspection.md`; this report alone does not certify visual inspection. Legacy unversioned files lack frame integrity hashes and trigger a loader warning. No Phase 6 implementation or biological calibration is claimed.
