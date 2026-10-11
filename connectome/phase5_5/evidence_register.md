# Evidence register and claim boundaries

| Item | Evidence available | Permitted statement / boundary |
| --- | --- | --- |
| Circuit structure | Phase 3 saved Circuit v2 and independent audit: 321 nodes, 11,557 edges, 91,023 structural synapses. | Extracted measured connectivity within a chosen subset, not the complete escape pathway. |
| Weights and signs | Synapse counts, max-normalization by 172, predicted ACh for all selected neurons. | Counts are structural measurements; conductance/rate gain and positive functional signs are modeling assumptions. |
| Retinotopy | Phase 3 audit: selected neurons' optic-lobe column coordinates unavailable; soma positions are not receptive fields. | Uniform population input is the primary mapping. Synthetic fields support conditional computational studies only. |
| Phase 4 dynamics | Deterministic rate model; saved results record 159 passing integration assertions. | Existing numerical evidence; this phase does not rerun those tests or certify neural physiology. |
| Phase 5 frames | Saved validation records 114 passing tests, schema 1.0, pixel coordinates and abstract looming distances. | Existing stimulus software evidence; phase 5.5 checks generated benchmark compatibility separately. |
| LC4/LPLC2 input roles | Ache et al. (2019): LC4 supplies a looming velocity component and LPLC2 a size component to the GF. | Motivation for distinct engineered channels. Their equations, units and scaling are not measured MaleCNS neuron responses. |
| LPLC2 selectivity | Klapoetke et al. (2017): radial motion opponency provides looming selectivity and rejection of confounding motion/luminance patterns. | Standalone negative-control tests are needed; a size-only signal is an incomplete proxy. No upstream T4/T5/inhibitory circuit is included here. |
| Directional takeoff | Dombrovski et al. (2023): spatial LC4-to-DN gradients and behavioral evidence for DNp02/DNp11-associated takeoff directions. | Literature supports the mechanism in studied data, not the identity of receptive fields in this project's male dataset. DNp04/02 coactivity and DNp11 are later candidates, not already implemented motor mappings. |
| Connectome and optimization | Lappalainen et al. (2024): both connectome constraints and task optimization contributed to functional predictions in another fly visual-system model. | Motivation for controls and separating fixed from optimized models. Their performance does not predict FLY's outcome. |
| Missing context | Phase 3 audit lists excluded intermediate populations, including predicted inhibitory candidates. | Conclusions are conditional on this subset. Do not manufacture inhibition or alter the frozen circuit to match expected responses. |

## Sources

- Local: `../phase3/phase3_final_audit_report.md` sections 7–10, `../phase3/circuit_v2_specification.md`, `../phase4/specification.md`, `../phase4/results/phase4_test_results.json`, `../phase5/specification.md`, `../phase5/results/validation_results.json`.
- Ache et al., *Neural Basis for Looming Size and Velocity Encoding in the Drosophila Giant Fiber Escape Pathway* (2019). [DOI](https://doi.org/10.1016/j.cub.2019.01.079), [PubMed](https://pubmed.ncbi.nlm.nih.gov/30827912/).
- Klapoetke et al., *Ultra-selective looming detection from radial motion opponency* (2017). [Full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC7457385/).
- Dombrovski et al., *Synaptic gradients transform object location to action* (2023). [Article](https://www.nature.com/articles/s41586-022-05562-8). [Publisher correction](https://doi.org/10.1038/s41586-023-05930-y): corrected figure-axis labels to azimuth; use the corrected article.
- Lappalainen et al., *Connectome-constrained networks predict neural activity across the fly visual system* (2024). [Article](https://www.nature.com/articles/s41586-024-07939-3).

## Outstanding evidence

No calibrated visual-field mapping, cell-specific time constants, absolute rate/current calibration, validated decoder thresholds, closed-loop motor plant, completed baseline comparisons or behavioral results exist for the proposed experiment. The benchmark is synthetic and does not establish biological danger labels. Future acquisition of receptive fields must verify cell correspondence and dataset/specimen differences; another paper's coordinates cannot simply be attached to these body IDs.
