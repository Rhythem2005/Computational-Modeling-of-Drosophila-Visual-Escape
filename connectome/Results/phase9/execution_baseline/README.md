# Computational Modeling of Drosophila Visual Escape — Phases 1–3

This repository extracts, verifies, and freezes the synaptic connectome for the Drosophila melanogaster visual escape circuit, using the **MaleCNS v1.0** (male-cns:v1.0) dataset.

Phase 3 is complete, producing the frozen **Circuit v1**.

## Circuit v1 Neuron Types

| Type  | Role | Count |
|-------|------|-------|
| LC4   | Looming-sensitive visual projection neuron | 126 (63L + 63R) |
| LPLC2 | Lobula plate / lobula columnar neuron      | 185 (92L + 93R) |
| DNp01 | Descending neuron (Giant Fiber) (Primary)  | 2 (L/R) |
| DNp04 | Descending neuron (Secondary)              | 2 (L/R) |
| DNp06 | Descending neuron (Secondary)              | 2 (L/R) |
**Total Neurons:** 317

## Dataset

**male-cns:v1.0** — 2026 Drosophila Male Central Nervous System connectome. Phase 3 artifacts were built directly from the version-pinned feather data files.

## Phase 3 Frozen Artifacts

| File | Description |
|------|-------------|
| `connectome/phase3/circuit_v1.json` | Complete machine-readable circuit |
| `connectome/phase3/circuit_v1_nodes.csv` | Frozen 317 neurons |
| `connectome/phase3/circuit_v1_edges.csv` | Frozen 11,286 edges (w ≥ 3) |
| `connectome/phase3/specification.md` | Human-readable circuit specification |
| `connectome/phase3/decision_record.md` | Decision and assumption hierarchy |
| `connectome/phase3/excluded_candidates.md`| Excluded descending and interneurons |
| `connectome/phase3/phase4_handoff.md` | Usage contract for Phase 4 simulation |
| `connectome/phase3/validation_report.md` | Verification and checksums |

## Normalization

**Method:** max-normalization — each weight is divided by the global maximum weight (172).

## Retinotopy Status

**NOT AVAILABLE**. MaleCNS v1.0 does not populate retinotopic metadata for LC4/LPLC2 neurons. Phase 4 must model spatial representation explicitly if required.

## How to Verify Circuit v1

1. Activate the virtual environment: `source venv/bin/activate`
2. Run the independent verification script:

```bash
python connectome/scripts/phase3/verify_circuit_v1.py
```
*(Runs 41 validation checks against the original feather source files)*

## Assumptions and Limitations

- Structural synapse counts are unsigned; neurotransmitter sign is stored as metadata.
- All 317 neurons are predicted acetylcholine (excitatory). Phase 4 decides simulation sign convention.
- Phase 3 freezes the biological circuit. Phase 4 will handle simulation, vision modeling, and ML.
