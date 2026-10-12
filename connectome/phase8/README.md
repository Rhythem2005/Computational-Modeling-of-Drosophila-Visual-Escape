# Phase 8 — descending-neuron initiation decoder

The decoder converts bilateral DNp01 mean activity into one abstract escape initiation request after 20 ms sustained threshold activity. It records score, persistence, a single event impulse, and a latched request. Directional steering is unavailable because the uniform visual representation has no verified spatial mapping. Read [specification.md](specification.md) and the user-approved [threshold amendment v1.1](protocol_amendment.md).

The amendment advances each training-negative quantile to its next larger float64 value. This avoids the original zero-threshold rule firing on silence. Original raw-quantile candidates are retained for audit. This is a separately named condition; earlier protocol files remain unchanged.

**Threshold status is provisional.** Phase 6 requires feature-only and linear controls before final decoder tuning. Phase 8 materializes training-negative candidates and uses the predeclared highest-quantile candidate for a demonstration. It does not run validation or test cohorts, fit a final threshold, implement those controls, or evaluate escape behavior.

Run from repository root:

```bash
# First implementation only; before evidence is never overwritten.
./venv/bin/python -m connectome.scripts.phase8.evidence
./venv/bin/python -m connectome.scripts.phase8.regression --stage before
./venv/bin/python -m pytest connectome/phase8/tests/ -q
MPLCONFIGDIR=/tmp/fly-phase8-mpl ./venv/bin/python -m connectome.scripts.phase8.validate_phase8
```

Subsequent reproduction uses the existing before records and runs the validator. It refreshes Phase 8 outputs only. No earlier phase validator is called, and no dependencies are installed. All 192 training negatives have their score and DN traces saved; eight existing Phase 7 training samples demonstrate decoding. All first decisions, including pre-onset events, are retained. State at the 1 s endpoint cannot trigger an event.

Decode an existing saved Phase 7 activity file using the provisional plan:

```bash
./venv/bin/python -m connectome.scripts.phase8.run_decoder \
  --activity-dir connectome/phase7/results/activity \
  --stimulus-id train_f0000_looming
```

Files go to `connectome/phase8/results/cli_decoded`. Repeat with `--overwrite` if needed. The loader verifies the Phase 7 array/config hashes and frozen model provenance before decoding.

```python
from connectome.scripts.phase8.decoder import InitiationDecoder, Threshold

# Explicit illustrative threshold; this is not a final calibrated model.
decoder = InitiationDecoder(Threshold("finite", 1.0))
decoded = decoder.decode_run(activity_run)
print(decoded.action())
```

`StreamingDecoder` also accepts individual `(time_ms,score)` samples beginning at zero and advancing 1 ms. It maintains at most 21 history entries. A new instance resets for a new episode. The score and activity are arbitrary model units, not spikes/s. An emitted request is not physical movement or successful escape.

See [validation report](results/validation_report.md), candidate plan, training trace records, decoded sample action JSONs and plots under `results/`. Final calibration after the required controls, directional mapping, action physics, behavioral environment and experiments remain later work requiring authorization. No new dependency, commit or push.
