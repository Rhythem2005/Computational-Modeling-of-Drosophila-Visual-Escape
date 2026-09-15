# Phase 0.1: neuPrint/MaleCNS setup and connectivity verification

This repository phase sets up a minimal Python environment to connect to the neuPrint service and verify the presence and connectivity of key neuron types for the Connectome-Grounded Real-Time Visual Escape Agent based on the Drosophila melanogaster MaleCNS connectome.

## What was queried
The script `connectome/queries/verify_circuit.py` queries the neuPrint API for the existence of three main neuron classes:
* **LPLC2**
* **LC4**
* **DNp06**

It also checks for synaptic connectivity between these classes:
* LPLC2 → DNp06
* LC4 → DNp06

## Dataset and Version
The script targets the **MaleCNS (manc:v1.0)** dataset via neuPrint (Male Adult Nerve Cord). The environment variables are set up to connect to the public `neuprint.janelia.org` server, but require a personal authentication token.

## What the returned connection data represents
The script returns the aggregated synaptic weights (total number of synaptic connections) between the pre-synaptic neuron classes and the post-synaptic neuron classes.

## Assumptions and Limitations
- The connection requires a valid neuPrint authorization token.
- This phase only verifies existence and total connectivity weight between classes, it does not download complete neuron skeletons, locations, or single-neuron connectivity profiles.
- Any neuron or connection reported as "NOT FOUND" means it does not exist in the queried dataset under those specific type names, which might require adjusting the names based on specific naming conventions in the MaleCNS dataset.

## How to run
1. Ensure your `.env` file is properly configured with your `NEUPRINT_TOKEN`.
2. Activate your virtual environment: `source venv/bin/activate`
3. Run the script: `python connectome/queries/verify_circuit.py`
