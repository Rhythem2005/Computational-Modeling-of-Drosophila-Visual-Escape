# Phase 5.5 — research protocol and benchmark design

Phase 5.5 defines the experiment before visual encoding and decoder tuning. Its deliverables are a research protocol, evidence register, versioned benchmark design, reproducible scenario manifest, validation evidence and Phase 6 handoff. This is a locally recorded protocol, not an externally registered study or an experiment result.

- [Research protocol](research_protocol.md): questions, hypotheses, endpoints, controls, tuning and statistical rules.
- [Evidence register](evidence_register.md): measured structure, literature support, assumptions and unresolved calibration.
- [Benchmark design](benchmark_design.yaml): version 1.0, explicit seeds and numeric choices.
- [Phase 6 handoff](phase6_handoff.md): implementation requirements and scientific gates.
- [Validation report](results/validation_report.md): checks actually executed.

From the repository root:

```bash
./venv/bin/python -m pytest connectome/phase5_5/tests/ -q
./venv/bin/python -m connectome.scripts.phase5_5.validate_protocol
```

The second command writes a deterministic `results/benchmark_manifest.json`, `results/protocol_lock.json` containing hashes of design documents/code, and timestamped `results/validation_results.json`. It validates all planned configs through the existing Phase 5 validator and renders representative stimuli in memory. It never writes Phase 3–5 files except possible Python bytecode caches, which are excluded from preservation checks. Results include before/after hashes of protected files.

The manifest contains **256 matched families / 1,024 planned episodes**: 256 training, 128 validation, 256 in-distribution test, and 128 episodes in each of three out-of-distribution test cohorts. These are scenario definitions, not recorded neural or behavioral outcomes. Labels and generator parameters are evaluator-only. Encoder input is restricted to `frames` and `timestamps_s`.

Only the training partition may be used for fitting. Validation selects thresholds and documented hyperparameters. Test manifests are available for reproducibility, not cryptographically sealed; inspect only integrity checks before evaluation. Any development informed by their model outcomes invalidates their held-out status and requires a new protocol version and fresh test scenarios.

Protocol changes require a version bump, rationale and regenerated manifests/lock before affected experiments. The lock detects edits; it is not a substitute for a timestamped public preregistration. No encoder, neural response, decoder, baseline network, or closed-loop environment is implemented in this phase.
