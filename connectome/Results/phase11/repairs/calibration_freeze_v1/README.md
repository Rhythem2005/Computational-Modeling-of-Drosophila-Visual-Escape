# Calibration freeze packaging repair v1

**Verified and resumed.** The first calibration had completed scoring and threshold
assessment, but failed while packaging its freeze. The writer read every JSON
artifact as a possible GRU training-proof dictionary. `diagnostics.json` is a list
of per-clip records, so calling `.get()` on it raised AttributeError.

The Phase 11 writer now considers only dictionary-valued JSON records as candidate
training proofs. Exactly one valid selected-model proof is still required. The
frozen Phase 10 implementation, all training/decoder mathematics, input encodings,
seeds, budgets and scientific configurations remain unchanged.

## Verification

- Full engineering suite: **552 passed**, 0 failures/errors/skips (542 existing +
  10 added regression/compatibility cases).
- Regression tests replay the actual failed freeze using its saved selected model,
  input index, assessments and list-valued diagnostics; freeze creation and reload
  verification pass. Missing/ambiguous selected proofs remain rejected.
- A separate full-path disposable replay loaded the original two completed trials
  for seed 55100, verified their provenance, reused all saved score records and
  created/verified the exact formerly failing freeze. Retraining, new neural
  inference and ledger-registration calls were forbidden during that replay.
- All **100 original training and selected-model files** retained identical hashes.
- After actual restart, the repaired freeze was published to the canonical result
  directory and its payload/artifact hashes were independently verified. Its
  calibration explicitly contains no held-out IDs.

## Narrow source compatibility

Checkpoint contracts bind the complete source catalog. Changing metadata-packaging
code otherwise prevents loading the already completed models and existing score
cache. Their contracts and files were **not rewritten**.

`compatibility_certificate.json` fixes the exact legacy source catalog, the repaired
`jobs.py` hash, scientific manifest/configuration/lock hashes and **1,255 specific
legacy artifact hashes**. The new `repair_provenance.py` binds that certificate by
SHA-256. `approval.json` binds the tested new source catalog after the passing
suite. Only this exact source pair and these exact files can be reused. Unregistered
sources/artifacts, modified training/configuration files, certificate changes and
missing approval are rejected by tests. Incomplete old trials are not grandfathered;
all 20 legacy trials are already complete. New trials use the current source catalog.

The source bridge is read-only. Old diagnostics, assessments, model metadata,
checkpoint arrays, optimizer/RNG state and histories remain intact. Newly created
freezes bind the current tested source catalog and the original model/artifact
hashes. This repair does not authorize held-out inference.

## Failure history and restart

The original failure trace, ledger and source files are archived in this directory.
The one affected ledger entry was explicitly requeued as an infrastructure repair,
retaining its complete original failure history and its exact job/model/mapping
identity. This is not a new seed, replacement model, numerical-failure redraw or
scientific condition exclusion. No completed training registration was reset.

Gate C was refreshed and passed before the authorized continuous restart. The
interrupted assistant turn did not terminate that process; continuation checked
and followed the existing worker instead of starting another one.

At the independent post-resume audit, **20/120 trials** remained complete and
**18/816 calibration conditions** had completed, with the next calibration active.
These are progress counts, not a claim that Phase 11A is complete. The run continues.
No comparative scientific conclusions are drawn from training/validation calibration.

`jobs.py.diff`, `replay_result.json`, `replay.log`, `approval.json`,
`ledger_amendment.json`, and `verification_after_resume.json` contain the detailed
evidence. No dependencies, commits or pushes were introduced.
