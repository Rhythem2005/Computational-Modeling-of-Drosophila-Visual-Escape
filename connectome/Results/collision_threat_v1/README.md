# Collision-threat v1 — approved diagnostic and prototype completed

The user approved the [staged implementation plan](../collision_threat_implementation_plan_20261027/README.md), then approved the concrete rule and bounded prototype at the reserved review gate. Both stages are implemented in `connectome/scripts/collision_threat_v1/`. Stage A involved saved-image measurements only; Stage B completed the authorized known-fixture comparison. Neither stage fitted a model or threshold, resumed training, or used held-out evaluation.

## Prototype result

[Prototype report](prototype/1793093607177149000/README.md), [per-controller/episode summary](prototype/1793093607177149000/summary.json), [saved-file QA](prototype/1793093607177149000/saved_file_audit.json), and [detailed findings](prototype_findings.md).

**The standalone image-motion rule passed the five known fixtures: 3/3 dangerous escapes, 0/2 harmless requests, no pre-onset request.** The circuit hybrid still failed: it held the near-miss initiation initially but emitted a harmless fallback escape at 767 ms when the object touched the image border and perception became unknown. The pending internal circuit request was at 239 ms. That 528 ms gate delay and false alarm remain recorded; the approved fallback policy was not changed after observing its outcome.

All **73 targeted checks passed** (23 feature checks, 20 new rule/gate checks, 30 preserved adapter checks). The exact approved 60-attempt budget was consumed: 30 combinations and 30 exact repeats. The run took 31.93 seconds of episode execution. Original controls matched saved trajectories exactly; a separate saved-file audit rechecked all repeats, all physical geometry and internal/physical timing. All 214,448 protected earlier files and all 198 Stage A files remained unchanged.

These are development fixtures, not a generalization result. The rule assumes a point observer and constant unknown object radius/relative velocity. It can miss collisions with the finite-radius fly on different geometries. The evaluator retained finite-fly swept collision geometry. No extra conditions, training, threshold fitting or independent evaluation were introduced to rescue failures.

## Current result

[Information audit](1793092658671112000/information_audit.md), [full diagnostic record](1793092658671112000/information_audit.json), [per-trajectory validity report](1793092658671112000/validity_report.json), [tests](1793092658671112000/tests.log), [execution](1793092658671112000/execution.json), and [preservation](1793092658671112000/preservation.json).

Processed all 91 unique saved trajectories. **23 feature tests passed.** The harmless near-miss has image-bearing motion observable at **217 ms**, before the legacy circuit request at **239 ms**. The three dangerous paths keep constant image bearing while growing. Both images and old channels are not exactly identical between the dangerous and harmless cases. This supports reviewing an image-motion candidate; it is not a learned classifier, a claim that the old input was mathematically insufficient, or an avoidance result.

The causal extractor accepts only a camera frame and timestamp. It measures area-derived radius, centroid, normalized position, bearing/extent proxies and adjacent-frame derivatives. Unknown observations, disconnected components, edge contact, foreground dominance, gaps and insufficient history have explicit validity/reason records. Renderer diagnostics are audit references only and never enter perception. Full no-action dangerous trajectories stop at collision; no later frames are fabricated. Post-escape frames are not used to infer what could have been known before action.

All **214,448 protected earlier files remained unchanged**. The running Stage A source catalog also remained unchanged. Saved trial/checkpoint identity is still 45/120 complete, 272/816 calibrations complete, partial trial epoch 51 / offset 256 / 816 updates / unfinished. No training continuation occurred.

## Exact-rule gate and authorization history

The approved plan reserved review of the exact equations and assumptions before policy implementation and prototype execution. The [exact specification](decision_rule_spec.md) and [original candidate manifest](candidate_manifest.json) retain their proposal-time pending status unchanged. The user's subsequent answer, **“Approve exact rule and bounded prototype”**, is recorded in [candidate_authorization.json](candidate_authorization.json), binding their exact hashes and resolving that gate. The Stage A run's disabled-Stage-B statements remain true records of its earlier execution time.

The original Stage A `--stage prototype` guard remains unchanged and disabled. Stage B uses the separately gated `launch_prototype` entry point and refuses changed or absent exact-rule authorization. The [global attempt ledger](prototype/attempt_ledger.json) now contains all 60 authorized attempts. Another prototype launch refuses to create extra attempts; no automatic rerun or retry is permitted.

## Reproduction

Stage A only, using the existing virtual environment and installed dependencies:

```bash
./venv/bin/python -B -m connectome.scripts.collision_threat_v1.launch --stage saved-diagnostic
```

This creates a new evidence directory and does not overwrite this completed run. It verifies the bound source-run/plan/checkpoint hashes and the earlier source catalog, holds the production worker lease read-only, checks existing startup worker/power/memory/thermal policy, runs targeted tests, and enforces 91 trajectories / 15 minutes / 4 GiB RSS / 250 MiB output. The extractor uses existing NumPy/SciPy; plotting uses installed Matplotlib. No dependency installation is needed.

The Stage B invocation was `./venv/bin/python -B -m connectome.scripts.collision_threat_v1.launch_prototype`. Its approved attempt budget is exhausted; it is documented here for provenance, not as an instruction to start another run. Exact source/dependency fingerprints and the verified execution snapshot are recorded in its `manifest.json`, `snapshot.json` and `execution.json`.

Every execution contains authorization, source/config/episode hashes, per-frame NPZ/JSON features and timing alignment with saved original scores, validity diagnostics, logs, resource telemetry, failed-attempt records where needed, and before/after protected inventories. Stored NaNs mark explicitly undefined feature fields and are paired with masks/reasons; the extractor returns `None` rather than numerical NaNs. It raises on nonfinite defined calculations or invalid clocks.

![Saved no-action image measurements](/Users/rhythemsabharwalgmail.com/Desktop/FLY/connectome/Results/collision_threat_v1/1793092658671112000/saved_image_measurements.png)
