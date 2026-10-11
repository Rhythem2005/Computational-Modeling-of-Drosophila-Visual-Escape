# Phase 6 development audit

- Keep: frozen Phase 5 generator/loader and Phase 5.5 benchmark/protocol; Circuit v2 CSV/JSON node mapping and row order.
- Missing initially: encoder, normalization, numeric standalone gates, actual-movie deduplication, per-neuron schema and leakage/causality evidence. Added only under Phase 6.
- Concrete fixes before any benchmark response evaluation: initial mapping code incorrectly expected population literal `input`; the verified CSV/JSON use `visual_input`. The first Phase 6 pytest run returned 12 passed / 40 setup errors from this one literal. Corrected Phase 6 mapping/spec only; equations, tuning budget and gate cutoffs unchanged. No validation/test benchmark features had been computed.
- Frozen-context discrepancy: NT confidence range in descriptive Phase 3 documentation does not match all CSV values. Recorded, not repaired or used for encoder assignment.
- No code removed from earlier phases. No new dependencies, Phase 7 integration, commits or pushes.
