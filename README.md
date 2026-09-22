# FLY — Connectome-Based Visual Escape System

A computational neuroscience project testing whether real neural wiring from the *Drosophila melanogaster* connectome can drive a working model of visually triggered escape behavior.

The project starts from the **MaleCNS v1.0** connectome and focuses on the looming-sensitive visual populations **LC4** and **LPLC2**, feeding into a selected set of descending neurons involved in escape and steering. The long-term goal is to compare three model classes on equal footing — the connectome-derived circuit, a shuffled version of the same circuit, and a conventional neural network of comparable scale — to test what, if anything, the biological wiring contributes computationally. No claim that biological structure is superior is made unless the experiments support it.

```text
Video / Scene → Visual Stimulus → Visual Processing → LC4 + LPLC2
   → Connectome-Derived Circuit → Descending Neurons → Escape Decision → Behavioral Evaluation
```

Connectome analysis, literature evidence, modeling assumptions, and experimental results are kept in separate, clearly labeled stages throughout the pipeline.

---

## Research Basis

**Dataset:** Berg et al. (2026), *Sexual dimorphism in the complete Drosophila male central nervous system connectome*, Cell 189(18), 5504–5526.e15 [[1]](#references) — the source connectome (MaleCNS v1.0).

**Visual pathway:** LC4 encodes looming expansion/velocity [[2]](#references); LPLC2 detects looming via radial motion opponency and encodes angular size of an approaching object [[3]](#references). These findings motivate LC4/LPLC2 as the project's visual entry populations.

**Descending neurons:** candidates were selected using anatomical and behavioral evidence — DNp01/Giant Fiber for rapid escape and takeoff, DNp04 and DNp02 for visual escape and backward takeoff/steering, DNp11 for jump/escape, and DNp06 for visually guided evasive turns — drawn from Namiki et al. (2018) [[4]](#references), Ache et al. (2019) [[5]](#references), Kim et al. (2023) [[6]](#references), and Dombrovski et al. (2023) [[7]](#references). This literature informs candidate *selection*; it is not treated as proof the computational model will reproduce the same behavior.

---

## Circuit v2 (frozen, active)

| Population | Count | Role |
|---|---:|---|
| LC4 | 126 | Visual looming pathway |
| LPLC2 | 185 | Visual looming pathway |
| DNp01 | 2 | Primary escape readout |
| DNp04 | 2 | Escape / steering readout |
| DNp06 | 2 | Evasive flight steering readout |
| DNp02 | 2 | Escape / takeoff readout |
| DNp11 | 2 | Forward escape / takeoff readout |
| **Total** | **321** | |

- **11,557** directed edges, **91,023** total synapses
- Minimum edge threshold (`w_min`): **3 synapses** · Max synaptic weight: **172**
- Normalization: `weight / 172` · Matrix convention: `W[post, pre]`
- Independently reconstructed from raw Feather source files; matched the frozen artifacts exactly

**Circuit v1** (archival baseline, unchanged): 317 neurons, 11,286 edges — LC4, LPLC2, DNp01, DNp04, DNp06. v2 adds DNp02 and DNp11 on top of v1 without altering v1's original connections.

### Scope

The frozen circuit is an **Expanded Biologically Motivated Direct Feedforward Sensorimotor Model Circuit** — not a complete biological reconstruction. It excludes: the full descending-neuron and interneuron population, non-visual sensory convergence, thoracic motor circuitry, membrane/ion-channel biophysics, and experimentally calibrated synaptic conductances. These are deliberate scope limits, not gaps to be silently filled later.

### Modeling conventions

- **Weights** are unsigned structural synapse counts. Neurotransmitter predictions are stored as metadata, not treated as established functional sign. Converting structure to excitatory/inhibitory conductance is a Phase 4 modeling assumption, not a connectome fact.
- **Retinotopy is not available** — the MaleCNS data lacks the optic-lobe column metadata needed for it. Coordinates are not converted to visual-field degrees without a validated biological mapping.

---

## Roadmap

| Phase | Description | Status |
|---|---|---|
| 0 | Dataset validation, version pinning, repo structure, provenance | Complete |
| 1 | Whole-connectome discovery — LC4/LPLC2 targets, two-step pathways, threshold robustness (w_min = 1, 3, 10) | Complete |
| 2 | Candidate & biological analysis across all 63 direct visual DNs; anti-cherry-picking audit | Complete |
| 3 | Circuit definition, freeze, and independent verification (Circuit v2) | Complete |
| 4 | Neural simulation — state variables, synaptic dynamics, sign conventions, input encoding | Not started |
| 5 | Visual stimulus / environment (looming, approach, motion, synthetic & video scenes) | Not started |
| 6 | Visual encoder — image/video → LC4/LPLC2-equivalent input, kept separate from the frozen circuit | Not started |
| 7 | Behavioral readout — DN activity → takeoff/steering/timing signals | Not started |
| 8 | Behavioral evaluation — escape probability, latency, directional response | Not started |
| 9 | Controls — connectome-derived vs. shuffled-connectome vs. conventional model | Not started |
| 10 | Ablations — population removal, pathway removal, weight perturbation | Not started |
| 11 | Robustness & generalization under noise and novel stimuli | Not started |
| 12 | Statistical comparison across model classes | Not started |
| 13 | Interpretation of results (no superiority claims without experimental support) | Not started |
| 14 | Reproducibility package, configs, checkpoints, figures, final docs | Not started |

**Current milestone:** Phase 3 complete, Circuit v2 frozen and independently verified. Next: Phase 4 (neural simulation).

*As Phases 4–8 grow, phase-level detail will move to `docs/roadmap.md`; this table will stay as the summary.*

---

## Repository Structure

```text
connectome/
├── data/
│   ├── raw/
│   ├── discovery/
│   └── phase1/
├── phase2/
├── phase3/
│   ├── circuit_v1.json, circuit_v1_nodes.csv, circuit_v1_edges.csv
│   ├── circuit_v2.json, circuit_v2_nodes.csv, circuit_v2_edges.csv
│   ├── specification.md
│   ├── decision_record.md
│   ├── excluded_candidates.md
│   ├── phase4_handoff.md
│   └── phase3_final_audit_report.md
└── scripts/
    ├── phase1/
    ├── phase2/
    └── phase3/
```

---

## Verification

Full detail: [`phase3/phase3_final_audit_report.md`](connectome/phase3/phase3_final_audit_report.md).

- Circuit v1: 41/41 independent checks passed
- Circuit v2: 48/48 independent checks passed
- Final Phase 3 audit: 12/12 checks passed — raw-source reconstruction matched frozen artifacts, v1→v2 edge delta verified, zero missing/extra/duplicate edges, zero self-loops, source checksums verified
- Phase 4 implementation present: **0** · Phase 4 gate: **cleared**

---

## References

1. Berg, S. et al. (2026). Sexual dimorphism in the complete Drosophila male central nervous system connectome. *Cell*, 189(18), 5504–5526.e15. [doi:10.1016/j.cell.2026.08.015](https://doi.org/10.1016/j.cell.2026.08.015)
2. von Reyn, C. R. et al. (2014). A spike-timing mechanism for action selection. *Nature Neuroscience*, 17, 962–970. [doi:10.1038/nn.3741](https://doi.org/10.1038/nn.3741)
3. Klapoetke, N. C. et al. (2017). Ultra-selective looming detection from radial motion opponency. *Nature*, 551, 237–241. [doi:10.1038/nature24626](https://doi.org/10.1038/nature24626)
4. Namiki, S. et al. (2018). The functional organization of descending sensory-motor pathways in Drosophila. *eLife*, 7, e34272. [doi:10.7554/eLife.34272](https://doi.org/10.7554/eLife.34272)
5. Ache, J. M. et al. (2019). Neural basis for looming size and velocity encoding in the Drosophila Giant Fiber escape pathway. *Current Biology*, 29(6), 1073–1081.e4.
6. Kim, H. et al. (2023). A visuomotor circuit for evasive flight turns in Drosophila. *Current Biology*, 33(2), 321–335.e6.
7. Dombrovski, M. et al. (2023). Morphology and synapse topography optimize linear encoding of synapse numbers in Drosophila looming-responsive descending neurons. *Cell Reports*.

---

## Dataset

MaleCNS v1.0: [male-cns.janelia.org](https://male-cns.janelia.org/) — version-pinned; the project does not query the live/latest connectome state.
