"""Create a Phase 5 report from recorded validation evidence."""
import json
from pathlib import Path
PHASE5 = Path(__file__).resolve().parents[2] / "phase5"


def regenerate_report():
    e = json.loads((PHASE5 / "results" / "validation_results.json").read_text())
    c = e["test_counts"]
    if e["test_exit_code"] or c["failures"] or c["errors"] or c["skipped"] or not e["protected_files_unchanged"]:
        raise ValueError("Validation evidence does not support completion")
    text = f'''# Phase 5 validation report

Validated at {e["validated_at"]}. Automated acceptance checks passed.

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

- `{e["test_command"]}`: {c["tests"]} passed, {c["failures"]} failures, {c["errors"]} errors, {c["skipped"]} skipped.
- `./venv/bin/python -m connectome.scripts.phase5.validate_phase5`: tests plus {e["sample_count"]} saved samples verified by exact loader round trip, {e["plot_count"]} diagnostic plots generated. Looming radii are nondecreasing and within 1 px of analytic radius; translating centroid errors are below 1 px. See `results/sample_verification.json` for measurements.
- {e["protected_file_count"]} Phase 3/4 files matched their pre-validation hashes. The baseline is saved in `results/protected_file_hashes.json`.
- `./venv/bin/python -m connectome.scripts.phase5.generate_report`: produces this report from saved evidence; it rejects recorded failures.

## Assumptions and limitations

One circle per run; instantaneous hard-edged grayscale frames with clipping at image boundaries. Frame count is floor(duration_s * fps), timestamps are i/fps, and zero-frame runs are invalid. Looming is a physically motivated pinhole projection using abstract distances; no calibrated fly visual angles or retinotopy. No motion blur, anti-aliasing or stochastic rendering. The seed records provenance. Visibility/clipping can prevent area-equivalent radius or centroid from representing the full analytic object. Metadata generation date varies, while frame/timestamp hashes and config hashes are reproducible. Frame arrays are limited to 256 MiB.

## Unresolved

Automated checks have no unresolved failures. Plot visual inspection and session-wide Git/hash checks are recorded separately in `results/session_inspection.md`; this report alone does not certify visual inspection. Legacy unversioned files lack frame integrity hashes and trigger a loader warning. No Phase 6 implementation or biological calibration is claimed.
'''
    (PHASE5 / "phase5_validation_report.md").write_text(text)
    print("Generated evidence-based Phase 5 validation report.")


if __name__ == "__main__":
    regenerate_report()
