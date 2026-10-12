# Independent session inspection

Performed after the encoder freeze and full standalone validation; no tuning or source changes followed test-response inspection.

- Independently loaded all **1,024 saved NPZs** with `allow_pickle=False`. Verified file hashes against `encoded_index.json`, THW-derived `(60,321)` float64 drive, `(60,2)` channels, exact `arange(60)/60` timestamps, Circuit v2 body IDs, bounds/finiteness, uniform population broadcast, ten zero DN columns, encoder version and normalization/config hashes.
- Compared live source, config, normalization, mapping and protected-artifact hashes with `freeze_lock.json`: all match. Saved training scales are `[8.632185525889524, 8.417362938348457]`, derived from 256 training clips only.
- Visually inspected all six diagnostic PNGs (train, validation, ID test and three OOD tests): static/translation channels remain zero, growth signals follow onset, raster radius follows independent analytic geometry. Test plots were inspected post-freeze.
- Across every cohort, all negative-control channel peaks were **0**, below the predeclared 0.01 limit. Every looming clip responded on both channels, including both polarities and low contrast. Earliest/latest nonzero response across cohorts: **0.233333–0.300000 s**, i.e. 33.3–100 ms after synthetic motion onset; this is engineered, not fly latency.
- Geometry: 100% valid frame-radius errors <=1 px (required >=95%); median speed relative error 0.021771 (limit 0.20), 95th percentile 0.133264 (limit 0.50).
- Important observed limitation: the intentional [0,1] drive cap compresses high-growth and large-size OOD amplitudes. Mean fraction of all two-channel samples at cap in looming clips: growth OOD **20.34%**, size OOD **19.19%**; ID test **0.31%**, low-contrast OOD **0%**. This is input cap saturation, not neuron-state saturation or behavioral success. No thresholds/scales were changed to remove it.
- Encoded output directory is about **5 MB**. No raw benchmark frame sets were saved. Existing Phase 5 saved sample was consumed through its actual loader.
- Regression results match documented granularities: Phase 4 49 pytest cases plus 159/159 integration assertions; Phase 5 114 tests; Phase 5.5 44 tests. No count discrepancy. Integration output redirected to Phase 6 only.
- Matplotlib could not write its default home cache and used a temporary writable cache; plotting completed. No dependency was installed.
- A second `./venv/bin/python -m connectome.scripts.phase6.validate_phase6` run passed 52 tests and 127/127 gates again. SHA-256 of the encoded-file index (which includes all 1,024 NPZ hashes), normalization and original freeze lock was identical across runs.
- Final whole-session comparison: **143 protected Phase 3/4/5/5.5 files unchanged** against the hashes captured before implementation, excluding bytecode caches. Scoped `git diff --stat` is empty. `git status --short` lists only untracked Phase 5.5 directories (already present at start) and the new Phase 6 directories; no existing files were modified.

Remaining scientific limits are in the predeclared specification. No Phase 7+ implementation, commit or push.
