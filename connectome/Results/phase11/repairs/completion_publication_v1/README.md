# Completion publication repair

An interrupted live publication exposed a COMPLETE ledger entry for train_55010_55102_0p001 while canonical storage still held its unfinished epoch-196 checkpoint and no report/selected model. The completed original artifacts survived in fly-phase11-execution-mkunvufv. Their selected model hash exactly matches the already registered model hash.

Restored the original final checkpoint, selected model and report after completed_trial/restore verification: 200 epochs, 3200 Adam updates, identical checkpoint contract and history prefix. No model was retrained and no result fabricated. Previous canonical checkpoint and ledger are preserved here. All 26 completed models passed loading verification, including all original legacy-source checks. Canonical recovered trial loaded again after repair.

Fixed launch.publish by capturing the ledger bytes before artifact traversal, then publishing that captured registration state after files. This prevents publishing completion entries created after their report directories were already scanned. A deliberately frozen traversal reproduces that race; the first publication retains RUNNING and the next publishes complete artifacts before COMPLETE. Existing interruption/resume tests remain intact.

The next job train_55010_55103_0p0003 was marked failed by the predecessor report-read error before any checkpoint directory was created. Its failure entry is retained in failure_history and ledger_amendment.json, with the same identity requeued PENDING_INFRASTRUCTURE_REPAIR. No scientific failure was replaced. Other ledger rows/identities and scientific sources are unchanged. Exact operational source compatibility updated with archived previous certificate and raw execution fingerprints.

Final Gate B: 562 passed, zero failures/errors/skips. Initial verification had one new-fixture NameError (missing Path import), corrected without changing assertions; its failed log is retained under results/engineering/1793003282955246000. Gate C compute profile reused because no computation changed; next start still performs live resource checks. Training/calibration executed during this repair: zero. Complete saved totals: 26/120 trials, 136/816 calibrations. Frozen inventory and unrelated training/model bytes unchanged. No commits or held-out inference.

Production remains stopped. Resume manually with:
`./venv/bin/python -B -m connectome.scripts.phase11.launch --task continuous`
Use Ctrl+C once and wait for committed-checkpoint publication before closing the terminal.
