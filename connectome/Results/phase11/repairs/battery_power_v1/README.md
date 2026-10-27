# Battery power policy update

User authorized removal of the mandatory AC requirement. Battery power is allowed at 20% or above, with valid telemetry; normal discharge is allowed. Below 20%, invalid telemetry, or the existing disk/memory/worker/thermal blockers prevent startup. This is a startup check, not continuous low-battery monitoring. AC charging/stability checks are unchanged when AC is connected.

Only runtime.py, common.py (exact source-compatibility handling), and tests/test_manual_resume.py changed. The certificate binds the exact current execution source hashes to the previous checkpoint source identity for this resource-only edit. All scientific sources are identical. Any additional source change fails closed. Raw execution fingerprints are recorded separately in Gate B, Gate C metadata, the certificate, and future runtime preflights. No checkpoint or ledger was rewritten.

Gate B: 560 passed, zero failures/errors/skips, in disposable copies, including fresh-process interruption/resume tests. Existing paused production checkpoint loaded read-only at epoch 181 / offset 160 / Adam update 2890. All 263 bound production artifacts and the frozen protected inventory were unchanged. Three unapproved source-mutation checks were rejected.

Gate C compute measurements were reused because training computation is unchanged; no new profiling or live resource PASS is claimed. The launcher will perform a fresh live resource check at the next explicit start. The original failed battery preflight samples now have no blockers under the new policy. No registered trials, calibrations or held-out inference executed. Disposable test copies were removed after preserving logs.

Resume command (not executed):
`./venv/bin/python -B -m connectome.scripts.phase11.launch --task continuous`
