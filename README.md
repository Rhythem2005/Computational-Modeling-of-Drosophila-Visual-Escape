# FLY — Drosophila Flight, Connectome & Visual Escape Research

**A dual-architecture 3D fruit-fly simulation and computational neuroscience research platform.**

**Project status:** Active research; algorithmic avoidance demonstrated; connectome-derived neural-to-motor activity demonstrated under exploratory assumptions; **connectome-controlled wingbeats, free flight, and escape have not been demonstrated**.  
**Research snapshot:** 29 October 2026.

FLY investigates whether anatomically reconstructed neural circuits from *Drosophila melanogaster* can be connected to a physically grounded body and flight apparatus to produce visually triggered escape behavior. The project includes two **independent control approaches** operating in **one shared 3D environment**:

- **Algorithmic Fly** — a conventional, working obstacle-avoidance simulation and behavioral baseline.
- **Connectome Fly** — a research system that uses real connectome-derived neuronal connectivity, simulated neural dynamics, identified motor outputs, and exploratory muscle/mechanical models. Its full flight-control loop remains an open research objective.

The project does **not** claim to have reconstructed a complete biological fly, reproduced natural neural firing, validated an entire flight motor, or demonstrated superior performance of biological wiring.

## Contents

- [Research objective](#research-objective)
- [Scientific foundation and data](#scientific-foundation-and-data)
- [The two fly approaches](#the-two-fly-approaches)
- [What has been implemented](#what-has-been-implemented)
- [Experimental results](#experimental-results)
- [Current limitations and lessons](#current-limitations-and-lessons)
- [Next research direction and roadmap](#next-research-direction-and-roadmap)
- [Scientific integrity and reproducibility](#scientific-integrity-and-reproducibility)
- [Repository guide](#repository-guide)
- [References](#references)

---

## Research objective

The long-term Connectome Fly objective is an **embodied, causal visual–neural–mechanical feedback loop**:

```text
Approaching object in shared 3D world
           ↓
Fly-mounted, time-resolved RGB observations
           ↓
Image-derived visual processing (including LC4/LPLC2-related inputs)
           ↓
Anatomically derived connectome + simulated neuronal dynamics
           ↓
Identified descending and motor-neuron activity
           ↓
Neuromuscular activation and muscle mechanics
           ↓
Loaded thorax ↔ wing hinges ↔ bilateral wings ↔ aerodynamics
           ↓
Body forces, torques, and free-body motion
           ↓
Updated camera position and visual observations (feedback)
```

In the eventual Connectome Fly, wing motion and body movement must result from neural activity acting through defensible physical mechanisms—not from a predetermined escape sequence, an imposed online wingbeat trajectory, obstacle coordinates supplied directly to the neural controller, or the Algorithmic Fly's steering commands.

**Research milestones are deliberately distinguished:** an implemented interface, a numerically accepted simulation, a model-generated neural event, and an experimentally validated biological mechanism are not equivalent claims.

## Scientific foundation and data

### Primary connectome: MaleCNS v1.0

The project's anatomical source is the **MaleCNS v1.0** connectome of the adult male *Drosophila melanogaster* central nervous system. This public resource was developed by **HHMI Janelia/FlyEM, the University of Cambridge, the MRC Laboratory of Molecular Biology, Google Research, and collaborators**. It contains the brain and ventral nerve cord; FLY uses **selected, version-pinned subsets**, not all neurons in the resource. [1–3]

- **Primary publication:** Berg *et al.* (2026), *Cell*, DOI [10.1016/j.cell.2026.08.015](https://doi.org/10.1016/j.cell.2026.08.015).
- **Dataset portal:** [male-cns.janelia.org](https://male-cns.janelia.org/).
- **Version and downloads:** [MaleCNS v1.0 release notes](https://male-cns.janelia.org/release/) and [dataset downloads](https://male-cns.janelia.org/download/).
- **Google Research overview:** [A connectomics milestone: Mapping the complete male fruit fly brain](https://research.google/blog/a-connectomics-milestone-mapping-the-complete-male-fruit-fly-brain/).

The biological literature informing visual escape, descending pathways, power-muscle physiology, and wing-hinge mechanics is listed in [References](#references). Those studies motivate hypotheses and constraints; they do **not** automatically validate parameters transferred into this model.

### Anatomical model generations

| Model | Neurons | Directed chemical pairs | Scope and status |
|---|---:|---:|---|
| **Legacy Circuit v1** | 317 | 11,286 | Archived LC4/LPLC2 and selected descending-neuron circuit. |
| **Legacy Circuit v2** | 321 | 11,557 | Archived expanded direct visual/descending circuit; 91,023 raw synapses reported for this legacy selection. |
| **Selected motor circuit** | **1,679** | **93,677** | Frozen visual-to-eight-steering/control-motor-neuron reference; neural and muscle-interface work. |
| **Expanded chemical candidate** | **1,703** | **96,103** | Separately versioned exploratory candidate adding 24 identified DLM/DVM flight-power motor neurons. |

The 1,703-neuron candidate includes **32 selected motor outputs**: the original eight steering/control outputs plus **10 DLM and 14 DVM motor neurons**. It adds **2,426 existing source-data connection pairs**, not newly invented anatomical connections. The candidate retains only approximately **20.8%** of the known raw incoming synapse counts for those 24 power neurons; omitted inputs, receptor signs, intrinsic properties, and electrical/modulatory effects limit biological interpretation.

Earlier anatomical audits also examined broader candidates (including 2,014-, 2,446-, and 2,570-neuron selections). Those are **not** automatically accepted flight-control models.

The old 321-neuron Circuit v2 is a **historical verified milestone**, **not** the active final scope of the project. Legacy roadmap phase numbers should not be confused with the later Stage A/B/C neuromechanical work.

### Modeling conventions

- A **synapse count is structural evidence**, not a calibrated synaptic efficacy or known functional sign.
- Neurotransmitter predictions and confidence are metadata; postsynaptic receptor actions require additional physiological assumptions.
- Missing anatomical pathways, gap junctions, and neuromodulatory effects are **not** replaced with invented connectivity.
- Image-derived visual inputs are experimental model encodings, not a reconstructed full biological retina or experimentally validated receptive-field map.
- Frozen source artifacts and model versions are maintained separately from exploratory expansions.

---

## The two fly approaches

### 1. Algorithmic Fly — working baseline

The Algorithmic Fly uses conventional perception and control logic in the shared three-dimensional environment to react to an approaching obstacle. Its implemented simulation includes a fly/body/wing representation, obstacle-approach behavior, motion/physics-related infrastructure, and visible avoidance behavior.

**Demonstrated:** algorithmically controlled obstacle avoidance in the existing 3D simulation.  
**Not claimed:** a reconstruction of biological neural processing or fully validated insect aerodynamics.

This approach is preserved as a **separate engineering baseline**. It is **not** used to fill gaps in the Connectome Fly's controller.

### 2. Connectome Fly — exploratory research system

The Connectome Fly uses anatomically identified neural circuits and simulated spiking dynamics. It has working visual-input, neural-recording, motor-output, and muscle-activation infrastructure, plus an experimental physical-mechanics layer.

The shared application includes an existing **React/Three.js 3D interface** and **FastAPI integration layer**, with exactly two independent modes: **Algorithmic** and **Connectome**. The scene, environment, fly assets, approaching object, and visualization infrastructure are shared; the decision/control pathways are not.

**Important dashboard limitation:** Connectome-mode neural playback currently uses **historical scientific recordings**. The live 3D ball/RGB preview is not yet demonstrated to cause those recordings through a fully validated online scene → neural → muscle → wing → body → scene loop. The image-acquisition/adapter infrastructure should not be mistaken for completed closed-loop biological flight.

---

## What has been implemented

| System | Current outcome | Interpretation |
|---|---|---|
| Real-connectome circuit discovery and audits | **Implemented** | Selected chemical anatomy is source-derived and versioned. |
| Sparse conductance-based spiking simulator | **Implemented and software-tested** | 0.05 ms timestep; receptor signs/gains and cellular dynamics remain exploratory. |
| LC4/LPLC2-related image-derived visual input | **Implemented** | Stimulus-to-neural propagation observed at uncalibrated 10× gain; nominal inputs silent. |
| Original eight motor-neuron outputs | **Recorded and audited** | Identified motor events, not measured animal recordings. |
| Motor-spike-to-muscle activation (Stage A) | **Engineering-validated** | Correct event identities, delays, and dimensionless activation proxies; not force calibration. |
| Expanded 1,703-neuron chemical candidate | **Implemented and tested** | Real additional anatomical pairs; incomplete power-MN input coverage. |
| Expanded DLM/DVM neural study | **6/6 experiments completed and audited** | Power-MN spikes under 10× stimulus only; exploratory neural result. |
| Steering muscle-to-wing mechanics (Stage B) | **Blocked at physical identification** | b1/b3/i1/ps1 transmission and hinge mechanics not established; original proposed wing trials not run. |
| Thoracic power mechanism (Stage C) | **Built; active scientific acceptance failed** | Partial spike → activation → tension → work chain; no accepted sustained oscillation. |
| Shared dual-mode 3D dashboard | **Engineering-integrated** | Existing visualization and historical neural playback; no demonstrated live Connectome flight. |
| Connectome-generated wingbeats / free flight | **Not demonstrated** | Mechanically coupled, independently constrained flight motor is missing. |
| Connectome-driven visual escape | **Not demonstrated** | Requires flight, neural control authority, and validated closed-loop sensing. |

### Neural simulation and visual response

The current neural engine implements conductance-based leaky integrate-and-fire dynamics, including membrane voltage, excitatory/inhibitory conductances, delays, refractoriness, resets, spike recording, and independent numerical checks.

The earlier visual-response study ran **48 controlled trials**. Under nominal/base stimulation, the relevant trials remained silent; the uncalibrated 10× looming condition produced **9,355 all-neuron spikes and 181 original steering/control motor spikes** in the selected recording. These numbers characterize **the model under that condition**, not an animal's physiological firing rates.

### Motor activation (Stage A)

Using preserved original-network recordings, the accepted engineering audit matched **181 motor spikes to 181 delayed release events** in the high-gain condition, with a specified **1 ms NMJ delay** and independently checked muscle activation. Blank and nominal controls remained silent. The activation variable is a normalized surrogate; it is not measured calcium concentration or calibrated muscle force.

---

## Experimental results

### Expanded DLM/DVM neural validation — 29 October 2026

Six separately approved simulations used two equally ranked exploratory central power-output sign hypotheses (**E** and **I**), each tested with blank, nominal looming, and **uncalibrated 10× looming** input. Every trial lasted **500 ms** with a **0.05 ms** neural timestep. No outcome was tuned to force activity.

| Condition | All-neuron spikes | Original eight motor spikes | DLM spikes | DVM spikes | Active power neurons |
|---|---:|---:|---:|---:|---:|
| E — blank | 0 | 0 | 0 | 0 | 0/24 |
| E — nominal looming | 0 | 0 | 0 | 0 | 0/24 |
| **E — 10× looming** | **9,633** | **181** | **233** | **45** | **15/24** |
| I — blank | 0 | 0 | 0 | 0 | 0/24 |
| I — nominal looming | 0 | 0 | 0 | 0 | 0/24 |
| **I — 10× looming** | **9,584** | **181** | **191** | **37** | **15/24** |

**Result: PASS for the frozen exploratory neural recording and numerical acceptance criteria.** Both high-gain trials produced model-computed DLM/DVM events (278 E, 228 I); nine of the 24 power neurons remained silent in each. Neither sign hypothesis, the 10× gain, nor the resulting rates are accepted as a biological reference.

The expanded run recomputes spikes for all selected neurons. Original motor spike totals match the earlier 1,679-neuron high-gain recording, but some event timestamps differ; expanded results were **not** copied from the old recordings.

**Preserved results:** `connectome/Results/stage_c_expanded_chemical_v1_20261029/`.

### Stage B — steering-wing mechanics

Source-derived wing geometry was extracted (approximately **270 vertices**, **263 triangles**, and **2.456 mm²** surface area per wing in the reference mesh). However, evidence-backed per-muscle wing-hinge Jacobians and especially the indirect **ps1** transmission were not established. The original tethered Stage B scientific trial set did **not** execute. An earlier normalized-element software model is **not** evidence of actual wing movement.

**Result: unresolved biological/physical transfer; no claimed wingbeat success.**

### Stage C — thoracic-power execution — 29 October 2026

A nine-trial protocol was separately approved for a candidate DLM/DVM-driven thoracic mechanism. The study stopped on the first active-trial domain rejection, as predeclared.

| Trial group | Disposition |
|---|---|
| Blank, 1/2/4 mechanical substeps | **3/3 complete; independent passive audits PASS** |
| E 10× active, 1 substep | **FAIL at attempted 305.35 ms step** |
| E 10× active, 2/4 substeps | Not dispatched |
| I 10× active, 1/2/4 substeps | Not dispatched |

The last accepted active state was at **305.30 ms**: thorax displacement **+9.9526 µm**, with outward velocity **+3.886 mm/s**, approaching the frozen **±10 µm** model domain. The saved state was internally consistent, but the next attempted step was rejected and rolled back. The partial trajectory contained genuine recorded candidate-neural events transported through activation, muscle tension, and mechanical work; it did **not** constitute complete power or oscillation acceptance.

The read-only postmortem found that the instantaneous DLM generalized load was approximately **0.295 µN**, with DVM force **zero** at that time, while spring capacity at +10 µm was only **0.250 µN**. The first DVM activity occurred after the rejection. A separately identified provenance error showed that the stated rectangular-beam calculation yields **2.5 × 10⁻⁵ N/m**, not the previously claimed **0.025 N/m**. The active solver used the configured value correctly; the error was in its physical justification. Substituting the smaller calculated value would not repair the missing physical reference.

**Result: Stage C active mechanism acceptance FAIL; no sustained oscillations, powered wingbeats, or flight demonstrated.** The attempt is closed and must not be silently continued or reinterpreted as complete.

**Preserved results:** `connectome/Results/stage_c_thoracic_final_v2_20261029/`.

---

## Current limitations and lessons

The principal obstacle is **not simply generating neural spikes**. It is identifying an interoperable, biologically and physically defensible **neural → muscle → loaded wing apparatus → aerodynamic flight** pathway.

| Limitation | Why it matters |
|---|---|
| **Incomplete flight-state neural circuitry** | The 1,703-cell candidate omits most known incoming power-MN synapses and does not reproduce a supported sustained-flight state. |
| **Uncalibrated visual response** | Nominal visual stimuli were silent; activity under 10× sensitivity cannot be promoted to a normal reference. |
| **Unknown synaptic and intrinsic physiology** | Structure and neurotransmitter predictions do not uniquely determine effective conductances, receptor signs, electrical coupling or neural state. |
| **Muscle activation is not force** | Stage A proxies do not identify in-vivo calcium, preload, fibre cross-section, stretch-dependent constitutive behavior or actual muscle work. |
| **Unidentified muscle-to-wing transmission** | Direct and indirect steering paths, thoracic deformation, sclerites and wing-hinge coupling must be constrained independently. |
| **Unsupported isolated thorax reference** | The failed Stage C mechanism omitted wing inertia, hinge constraints and aerodynamic load, with inconsistent stiffness provenance. |
| **No validated online closed loop** | Recorded neural activity is not yet driven by live scene observations and coupled back into computed wing/body motion. |
| **No behavioral escape result** | No connectome-mediated change in flight trajectory or collision outcome has been demonstrated. |

### Lessons shaping the next architecture

1. **Define physical feasibility before building another actuator model.** A passing software test is not evidence that a plausible biological motor has been identified.
2. **Model wing, hinge, thorax, passive mechanics and aerodynamic loading as a coupled system.** An unloaded oscillator cannot independently validate the flight motor it is intended to represent.
3. **Use common specimen references, frames, physical units and energy accounting.** Combining isolated published constants can create an inconsistent model.
4. **Select neural circuitry for sustained flight as well as escape.** A resting looming-response circuit is not automatically a controller for a fly already airborne.
5. **Preserve failure as evidence.** Do not tune gains, forces, stiffness or spatial limits merely to produce successful-looking movement.

---

## Next research direction and roadmap

The project is shifting from repeated **isolated Stage B/C repairs** to a **flight-first, evidence-constrained neuromechanical architecture**. This is a proposed research strategy, **not** an implemented or validated replacement model.

### Scientific strategy

**Offline inverse feasibility:**

```text
Measured Drosophila flight / wing kinematics
    → required aerodynamic wrench and root torque
    → cycle work, power and passive energy storage
    → admissible muscle forces, geometry and bandwidth
    → identifiable neural/muscle control interfaces
```

**Eventual forward causal simulation:**

```text
Rendered RGB → selected flight-state connectome → actual motor events
    → named muscle state/forces → coupled thorax/hinge/wing dynamics
    → aerodynamic loads → 6-DoF body motion → next rendered RGB
```

Published wing histories may be used for **offline system identification, load estimation, and validation**. They must **not** act as an imposed wingbeat generator or hidden controller in a claimed connectome-powered flight experiment.

### Development gates

| Gate | Required deliverable | Completion criterion |
|---|---|---|
| **1. Flight feasibility** | Compatible reference anatomy, observed wing histories, inverse load/power budget, and muscle/hinge evidence audit | Establish a physically plausible operating region and identify whether effective muscle-to-wing ports are identifiable; explicit GO/NO-GO. |
| **2. Coupled mechanics** | Reduced loaded thorax–hinge–wing–body model with passive/preload and aerodynamic terms | Independent motion/load evidence, equilibrium, dimensional, convergence, and energy/momentum checks; no hidden actuation. |
| **3. Flight-state neural boundary** | Versioned audit of power, steering, stabilization and supported sensory pathways | Real anatomical connectivity and independently justified operating-state assumptions, not parameter tuning toward flight success. |
| **4. Neuromechanical integration** | Actual motor events causally drive named physical muscle ports | Auditable event → activation → tension → wing force/power transfer in one loaded mechanical reference. |
| **5. First exploratory flight** | Short predeclared airborne test with causal controls | Neural contribution to supported flight and physical control authority; not ballistic motion, prescribed wingbeats, or algorithmic control. |
| **6. Visual escape** | Scene RGB → neural response → flight trajectory change → updated RGB | Repeatable stimulus-dependent trajectory/avoidance effect relative to appropriate controls, without object-state shortcuts. |
| **7. Biological and comparative validation** | Independent flight/escape physiology, ablations, robustness and model controls | Claims limited to measured agreement; no connectome superiority claim without controlled evidence. |

**Immediate priority:** Establish a **common experimentally constrained flight reference** and an **inverse load/authority feasibility report**. In parallel, audit broader existing anatomical candidates for the sustained-flight neural functions the physical system would require. If effective mechanical ports cannot be constrained from available evidence, record the precise missing measurement and stop rather than constructing another speculative system.

### What counts as a first escape demonstration?

A completed exploratory escape must show that an approaching stimulus changes **connectome-generated motor activity**, which changes **physical wing forces** and therefore the **body trajectory**, with feedback to subsequent visual observations. It must pass prespecified matched controls. Merely detecting looming, drawing an escape animation, replaying prerecorded neural spikes, or triggering an algorithmic turn does **not** meet this criterion.

Biological validation is a separate, stronger objective requiring agreement with independent physiological and behavioral measurements.

---

## Scientific integrity and reproducibility

- **Versioned sources:** The MaleCNS source release, original circuit, expanded candidate, scientific inputs, protocols and artifacts are kept distinguishable.
- **Immutable past experiments:** Passed and failed studies retain exact configurations, hashes, outputs, outcome states and independent audits.
- **Explicit approval:** Bounded scientific neural or mechanical runs are not dispatched merely by opening the dashboard or preparing a protocol.
- **Failure semantics:** A failed prefix is not a completed silent trajectory; unrun trials are not reported as zeros.
- **Hypothesis discipline:** Exploration of receptor sign, sensitivity gain, muscle kinetics and mechanics does not promote any variant to a biological reference without evidence.
- **Controls and comparisons:** Legacy shuffled-network, neural-network and ablation ideas remain research directions; accepted superiority or generalization claims have **not** been established.
- **Software versus science:** Historical project reports describe extensive passing software/unit checks. These support implementation integrity, not physiological or mechanical fidelity. The numbers were **not rerun solely for this README update**.

Data and code availability/licensing for upstream sources must be respected. The MaleCNS dataset is distributed under **CC BY**; users of this project should follow its attribution and any applicable terms for third-party datasets, models and software. Refer to the [official MaleCNS download page](https://male-cns.janelia.org/download/) for authoritative dataset information.

## Repository guide

The following are **documented paths and research entry points**, not an exhaustive or independently audited repository tree:

```text
connectome/
├── data/                                  # source and discovery artifacts (historical)
├── phase2/                                # legacy candidate analysis
├── phase3/                                # frozen legacy Circuit v1/v2 and audits
├── simulation/
│   ├── power_neural/                     # expanded candidate preparation, runner, audits
│   ├── flight_power/                     # exploratory loaded/unloaded power-model work
│   └── thoracic_diagnostics/             # read-only failure and physical-provenance audit
└── Results/
    ├── stage_c_expanded_chemical_v1_20261029/
    └── stage_c_thoracic_final_v2_20261029/
```

Legacy circuit documentation includes `connectome/phase3/phase3_final_audit_report.md`. The two-mode 3D dashboard, application services, and additional physics modules are maintained in the existing codebase; their exact startup commands and complete directory structure should be taken from the checked-out repository rather than inferred from this summary.

**Safe read-only neural preflight (when the documented local environment exists):**

```bash
./venv/bin/python -B -m connectome.simulation.power_neural.run
```

This command invokes the read-only expanded-neural preflight. Scientific execution requires a separate, explicit approved scope and must not be confused with this preflight. For reproducibility, prefer the frozen manifests and exact per-experiment runner instructions saved with the research artifacts over recreating parameters from README text.

---

## References

### Connectome, visual escape and descending pathways

1. **Berg, S., et al.** (2026). Sexual dimorphism in the complete *Drosophila* male central nervous system connectome. *Cell*, 189(18), 5504–5526.e15. [DOI: 10.1016/j.cell.2026.08.015](https://doi.org/10.1016/j.cell.2026.08.015).
2. **HHMI Janelia/FlyEM, Cambridge, MRC LMB and Google Research.** *MaleCNS v1.0*: [dataset portal](https://male-cns.janelia.org/), [release notes](https://male-cns.janelia.org/release/), [downloads and license](https://male-cns.janelia.org/download/).
3. **Google Research** (2026). [A connectomics milestone: Mapping the complete male fruit fly brain](https://research.google/blog/a-connectomics-milestone-mapping-the-complete-male-fruit-fly-brain/).
4. **von Reyn, C. R., et al.** (2014). A spike-timing mechanism for action selection. *Nature Neuroscience*, 17, 962–970. [DOI: 10.1038/nn.3741](https://doi.org/10.1038/nn.3741).
5. **Klapoetke, N. C., et al.** (2017). Ultra-selective looming detection from radial motion opponency. *Nature*, 551, 237–241. [DOI: 10.1038/nature24626](https://doi.org/10.1038/nature24626).
6. **Namiki, S., et al.** (2018). The functional organization of descending sensory-motor pathways in *Drosophila*. *eLife*, 7, e34272. [DOI: 10.7554/eLife.34272](https://doi.org/10.7554/eLife.34272).
7. **Ache, J. M., et al.** (2019). Neural basis for looming size and velocity encoding in the *Drosophila* Giant Fiber escape pathway. *Current Biology*, 29(6), 1073–1081.e4. [DOI: 10.1016/j.cub.2019.01.079](https://doi.org/10.1016/j.cub.2019.01.079).
8. **Kim, H., et al.** (2023). A visuomotor circuit for evasive flight turns in *Drosophila*. *Current Biology*, 33(2), 321–335.e6. [DOI: 10.1016/j.cub.2022.12.014](https://doi.org/10.1016/j.cub.2022.12.014).
9. **MANC descending-to-motor circuit study.** (2026). Organization of circuits linking descending input to motor output in the *Drosophila* Male Adult Nerve Cord connectome. *eLife*. [DOI: 10.7554/eLife.96084](https://doi.org/10.7554/eLife.96084). **Contextual supporting anatomy:** this is a separate dataset and does not authorize importing unmatched neuron IDs into MaleCNS.

### Flight muscle, thorax, hinge and embodied flight

10. **Wang, Q., Zhao, C., & Swank, D. M.** (2011). Calcium and stretch activation modulate power generation in *Drosophila* flight muscle. *Biophysical Journal*, 101(9), 2207–2213. [DOI: 10.1016/j.bpj.2011.09.034](https://doi.org/10.1016/j.bpj.2011.09.034).
11. **Bergou, A. J., et al.** (2010). Fruit flies modulate passive wing pitching to generate in-flight turns. *Physical Review Letters*, 104, 148101. [DOI: 10.1103/PhysRevLett.104.148101](https://doi.org/10.1103/PhysRevLett.104.148101).
12. **Pons, A., et al.** (2023). Solving the thoracic inverse problem in the fruit fly. *Bioinspiration & Biomimetics*, 18(4). [DOI: 10.1088/1748-3190/accc23](https://doi.org/10.1088/1748-3190/accc23).
13. **Hürkey, S., et al.** (2023). Gap junctions desynchronize a neural circuit to stabilize insect flight. *Nature*, 618, 118–125. [DOI: 10.1038/s41586-023-06099-0](https://doi.org/10.1038/s41586-023-06099-0).
14. **Melis, J. M., Siwanowicz, I., & Dickinson, M. H.** (2024). Machine learning reveals the control mechanics of an insect wing hinge. *Nature*, 628, 795–803. [DOI: 10.1038/s41586-024-07293-4](https://doi.org/10.1038/s41586-024-07293-4). [Author-associated data repository](https://doi.org/10.22002/aypcy-ck464).
15. **Gau, J., et al.** (2023). Bridging two insect flight modes in evolution, physiology and robophysics. *Nature*, 622, 767–774. [DOI: 10.1038/s41586-023-06606-3](https://doi.org/10.1038/s41586-023-06606-3). Its multi-species mechanisms are **not** direct *Drosophila* parameter estimates.
16. **Whole-body physics simulation of fruit fly locomotion** (2025). *Nature*. [DOI: 10.1038/s41586-025-09029-4](https://doi.org/10.1038/s41586-025-09029-4). [Flybody code](https://github.com/TuragaLab/flybody). A learned imitation/RL flight policy is **not** used as Connectome Fly evidence or control.

---

## Research position

**Already achieved:** a functioning algorithmic avoidance baseline; verified real-anatomy-derived neural subgraphs; an executable spiking neural model; image-derived responses under specified sensitivity; recorded identified power-motor events; audited neural-to-muscle activation; and a reproducible account of unsuccessful thoracic/wing-mechanics experiments.

**Still unsolved:** a physiologically supported sustained flight-state neural controller, an identifiable muscle-to-wing transfer, a validated coupled flight motor, powered wing motion, real-time connectome-to-body feedback, and visually triggered connectome-controlled escape.

FLY therefore remains a **computational research platform with an explicit open scientific objective**, not a completed biological escape simulator. Its next phase prioritizes **evidence-backed feasibility and causal physical integration** over animation-driven success claims.
