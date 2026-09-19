# Computational Modeling of Drosophila Visual Escape — Phase 1

This repository extracts and validates the synaptic connectome for the Drosophila melanogaster visual escape circuit, using the **MaleCNS v1.0** (male-cns:v1.0) dataset via the neuPrint API.

## Neuron Types

| Type  | Role | Count |
|-------|------|-------|
| LC4   | Looming-sensitive visual projection neuron | 126 |
| LPLC2 | Lobula plate / lobula columnar neuron      | 185 |
| DNp01 | Descending neuron (Giant Fiber)            | 2 (L/R) |
| DNp06 | Descending neuron                          | 2 (L/R) |

## Dataset

**male-cns:v1.0** — 2026 Drosophila Male Central Nervous System connectome, queried via `neuprint.janelia.org`. All biological claims in this repository derive solely from this dataset.

## Phase 1 Artifacts

| File | Description |
|------|-------------|
| `connectome/data/nodes.csv` | Neuron metadata (bodyId, type, side, predictedNt) |
| `connectome/data/raw_edges.csv` | Unfiltered synaptic edges from neuPrint |
| `connectome/data/processed_edges.csv` | Thresholded and aggregated edges (weight ≥ 3, duplicate pre/post pairs summed) |
| `connectome/data/weight_matrix.npy` | Raw structural weight matrix, W[post, pre] |
| `connectome/data/weight_matrix_normalized.npy` | Max-normalized weight matrix (values in [0, 1]) |
| `connectome/data/matrix_index.json` | Positional index → neuron metadata mapping |
| `config.yaml` | All pipeline parameters (dataset, thresholds, normalization) |

## Normalization

**Method:** max-normalization — each entry is divided by the global maximum weight. Simple, reproducible, preserves relative connection strengths. Parameters are documented in `config.yaml`.

## Retinotopy Status

The MaleCNS v1.0 dataset does not populate retinotopic metadata (`assignedOlHex1`, `assignedOlHex2`) for LC4/LPLC2 neurons. ROI data contains lobula column identifiers that could serve as proxies, but this has not been extracted. **Status: PENDING.**

## How to Run

1. Configure your `NEUPRINT_TOKEN` in the root `.env` file.
2. Activate the virtual environment: `source venv/bin/activate`
3. Run the pipeline:

```bash
python connectome/queries/fetch_nodes.py       # Extract neuron metadata
python connectome/queries/fetch_edges.py        # Extract synaptic edges
python connectome/queries/clean_and_export.py   # Process, aggregate, export matrix
python connectome/queries/verify_circuit.py     # Full verification (33 assertions)
```

## Assumptions and Limitations

- Requires a valid neuPrint authorization token.
- Phase 1 covers connectivity extraction and validation only — no simulation, vision modeling, or ML.
- Structural synapse counts are unsigned; neurotransmitter sign is stored as metadata, not applied to weights.
- All 315 neurons in this dataset are predicted acetylcholine.
