# Returning to the anatomical escape objective — 28 October 2026

## Scope and findings

This implementation begins the neural-output interface; it does not claim a new
neural motor controller or biological escape demonstration. No research run,
training, fitting, held-out evaluation, installation, commit or push was performed.
Tests use explicit artificial software fixtures, not recorded or predicted biology.

The top-level README stops at Phase 3 and is stale. Source and later phase records
establish the following implemented path:

- Phase 3: MaleCNS v1.0 selected anatomical subgraph. Current CSV inspection gives
  321 real neuron identities (126 LC4, 185 LPLC2, ten DNs), 11,557 directed edges,
  91,023 summed synapses, threshold 3 and normalization by 172. This is a selected
  subgraph, not a reconstructed whole fly brain. Edge classes include 9,994
  intra-population, 388 cross-visual, 1,141 visual-to-readout, 27 inter-readout and
  seven readout-to-visual edges; despite the historical feedforward designation,
  the implemented matrix includes recurrence. Matrix convention is W[post,pre].
- Raw files are present: connectivity Feather has 151,856,684 rows, annotations
  211,577, and neurotransmitter predictions 1,835,518. Schemas were inspected.
  The historical independent Phase 3 audit reports exact raw-source reconstruction;
  this session did not independently repeat that full reconstruction.
- Phase 4: deterministic ReLU rate dynamics, Euler dt=1 ms, tau=10 ms,
  gain=.5, input scale=.4 and activation cap 50. Signs are assumed excitatory
  from predicted cholinergic labels, not physiologically measured conductances.
  DNp01 prediction confidence in the actual node CSV is approximately .50–.56.
- Phases 6–7: causal image-history encoder, engineered contrast/area/radius-growth
  channels, broadcast to LC4/LPLC2. This does not reconstruct retinal processing,
  measured receptive fields or LC4/LPLC2 electrophysiology. DN input is zero.
  The single-circle/uniform-background domain does not cover furnished room RGB.
- Phase 8: primary initiation score averages DNp01 states. Sustained threshold
  decoding is an explicit modeling choice, not a biological decision mechanism.
  The inherited 5e-324 threshold is effectively positive-versus-zero, with no
  established physiological interpretation or noise margin.
- Phase 9: earlier 2D closed loop already lets neural initiation cause movement,
  using a prescribed delayed backward/lateral actuator. Neutral retreat is
  engineered; synthetic spatial mappings/turn semantics are not biological
  retinotopy or motor reconstruction. Saved development successes and a near-miss
  false alarm are documented in the behavior-readiness audit, not rerun here.
- Phases 10–11: GRU is a separate dense 321-input, 16-hidden-state comparator,
  16,241 learned parameters and scalar discrimination output. It neither modifies
  anatomical synapses nor supplies anatomical motor neurons. Training is partial;
  the saved-score audit finds ceiling calibration results shared by anatomical,
  shuffled, rewired and simpler models. No anatomical advantage is established.
- Room: six views feed color/size/pose-prior tracking and a geometric candidate
  velocity planner. RoomRunner sends that planner's commands to the world;
  FrontCircuitDiagnostic supplies neural telemetry only. This explicit separation
  preserved the frozen study instead of pretending an unvalidated panoramic
  neural/motor mapping existed. It is the reason current room survival is not
  evidence for anatomical control.

## Implemented now

`dashboard/simulation/room_flight/neural_output.py` adds AnatomicalOutput to the
existing verified-snapshot FrozenCircuit. It checks anatomical state ID order and
extracts all ten selected DN states. It calculates their recurrent inputs using
actual signed model weights, gain and current presynaptic state. `incoming` exposes
all nonzero structural inputs and their current modeled contributions for any
selected neuron, retaining zero-activity edges and original body IDs. These are
model algebra, not measured synaptic current, proof of effective connectivity or
an intervention establishing causal necessity.

FrontCircuitDiagnostic.sample now supplies that output; RoomRunner records
`dn_body_ids`, decision-clock `dn_activity`, `dn_recurrent_input` and
`motor_mapping_available=false` alongside existing full states, inputs, cameras,
policy events and commands. Existing dashboard state telemetry remains connected
and unchanged; no new frontend panel or incoming-contribution visualization was
added. Existing recordings are not rewritten. New fields apply to future explicitly
authorized runs with the front diagnostic enabled, not to absent/null signals.

`motor_command()` raises MissingMotorMapping, with no heuristic/planner fallback.
No selectable anatomical room controller is advertised. Existing baseline behavior,
transport, geometry and rendering remain untouched. No inherited calibration,
scientific source, dataset, checkpoint or result was edited.

## Critical blockers and next implementation boundary

1. **Sensory mapping:** need an evidence-backed visual-field/receptive-field mapping
   and a supported encoder for room images. Do not clone the circuit across six
   views or infer retinotopy from hemisphere/coordinates. A restricted synthetic
   front-view engineering condition is possible but must be labeled as such and
   requires approval to execute.
2. **Motor mapping:** selected descending neurons are not a reconstructed downstream
   motor circuit. Need defensible sign, direction, units and temporal relationships
   to effectors, or an explicitly approved abstract plant. The old Phase 9 retreat
   can demonstrate neural-triggered engineered movement, not emergent biological
   direction selection. It cannot be silently generalized to 3D.
3. **Functional dynamics:** conductances, time constants and response calibration
   remain assumptions. Structural counts and predicted transmitters do not resolve
   these. No new connection or response has been invented to bridge the gap.
4. **Causal evidence:** separately review bounded intervention comparisons (same
   sensory inputs/plant, intact vs blocked DN output, pathway ablation and graph
   controls), with predeclared endpoints and untouched evaluation conditions.
   Source algebra and animated activity alone cannot establish causal efficacy or
   anatomical advantage. None of these experiments is authorized or run here.

The chain now reaches inspectable anatomical DN outputs in the 3D recording path.
The DN→3D motor link is deliberately blocked. Earlier 2D fixtures support a weaker
claim of anatomical-model-triggered abstract movement; neither they nor the room
pilot demonstrate escape generated by a biologically reconstructed whole brain.

## Source trail

Inspected root README; Phase 3 specification/audit and frozen node/edge CSVs; raw
Feather schemas; Phase 4 specification/loader and controller dynamics; Phase 6
specification; Phase 7 pipeline; Phase 8/9 protocols and Phase 9 runner; Phase 10
models/networks/GRU; Phase 11 plan, ledger, validation report and saved-score and
behavior-readiness audits; room plan/final audit, adapter, runner, planner and
recording contracts. Historical reports retain their original timestamp/status;
old 'not run' or Phase 3-only milestones must not override the later pilot/ledger.
