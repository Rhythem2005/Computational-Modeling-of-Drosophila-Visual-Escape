# Phase 11A acceleration feasibility audit — 25 October 2026

**Recommendation: USE CPU.** Keep the existing NumPy/Apple Accelerate float64 implementation. An Apple M4 Metal device is available, but GPU training speedup and scientific equivalence have not been demonstrated. Both evaluated GPU backend families lack native GPU float64 support; adopting float32 would change the frozen numerical condition.

## Verified implementation and environment

The actual model has 321 inputs, 16 hidden units, and a scalar affine readout: **16,241 trainable parameters** (15,408 input weights + 768 recurrent weights + 48 gate biases + 17 readout parameters). It is a custom reset-before GRU with `h_next=(1-z)*h+z*n`. Readout at index k uses h[k] before input u[k]. Full float64 BPTT uses episode BCE on the earliest maximum logit in [200,1000) ms. Adam uses beta1=.9, beta2=.999, epsilon=1e-8 and global gradient clipping at norm 5. Batch size is 16; the 1 ms clock, .4 input scale, zero initial state, seeds and frozen partitions remain unchanged.

Python is 3.14.6, NumPy 2.5.3, SciPy 1.18.1, macOS 26.1 arm64. NumPy's build configuration reports **Apple Accelerate** BLAS/LAPACK. MLX, PyTorch, JAX/JAXLIB, TensorFlow and Numba are not importable in the specified venv. Nothing was installed or added to it.

A native Metal query initially returned no device under the sandbox. The approved unrestricted read-only query found **Apple M4**, unified memory, and a recommended working-set size of 12,713,115,648 bytes. This proves device exposure, not framework/operator compatibility or GRU performance. No GPU compute benchmark ran.

The checkpoint contract still requires parameters, Adam moments/update count, RNG/order, batch cursor, epoch/history, patience and best weights. Backend migration would require preserving and re-verifying those semantics.

## Measurements

Original frozen code ran inside a fresh byte-verified historical-path execution copy. Only the 256 training / 128 validation clips were loaded, through the existing isolation guards and frozen caches. Every epoch repetition reset to seed 55100, LR .0003 and the same initial shuffle. No checkpoint, LR, seed or threshold was selected.

Three separate CPU processes requested vecLib thread caps 1, 4, or the default; OMP/OpenBLAS hints stayed at 1. Actual Accelerate worker counts were not instrumented. Processes ran sequentially to avoid contention. The caps produced no meaningful performance difference (ratio 1.0022 between cap1 and cap4 epoch medians).

| Workload | CPU cap1 median | Repetitions |
| --- | ---: | ---: |
| Forward, batch 16 × 1000 × 321 | 21.500 ms | 7 |
| Loss + full BPTT, same batch | 62.997 ms | 7 |
| Adam update, initialization excluded | 0.126 ms | 15 |
| Full BPTT + Adam | 63.279 ms | 7 |
| All 128 validation clips, including input loading | 269.408 ms | 5 |
| Epoch: 16 updates + validation, without checkpoint writes | 1.5291 s | 5 |
| Epoch: 16 updates + validation + 17 checkpoint writes | **1.6151 s** | 5 |
| Reference rate circuit, one training clip | 14.684 ms | 9 |
| GRU score, one training clip | 6.021 ms | 9 |
| Decoder, one previously saved training score | 0.618 ms | 15 |

Cap4/default checkpointed epoch medians were 1.6116 / 1.6138 seconds. All samples and ranges are saved in the CPU JSON files. This audit executed **30 timed reset-first-epoch workloads and six warmup epochs**, plus component timings; it executed zero registered training trials, calibration conditions or held-out inference runs. Comparison weights are benchmark-only arrays, not selected scientific models.

Setup after imports took 0.330 s for cap1. First-call times were separately recorded: forward 23.314 ms, BPTT 63.373 ms, validation 299.437 ms and checkpointed epoch 1.6150 s. Python/NumPy has no GPU graph compilation here; no GPU compilation, synchronization or transfer latency was measured. CPU calls are synchronous. Benchmark checkpoint arrays and writers match production; profiling provenance metadata is smaller than full production histories/contracts, so extrapolations remain provisional.

Peak resident memory was **371.3–375.7 MiB** across workers, including benchmark intermediates. This is process peak RSS, not incremental GRU allocation or total system memory. GPU training memory is unmeasured. The existing 16 GiB CPU path has substantial memory headroom.

## Scientific and numerical equivalence

All **68 cross-process array comparisons** were exactly equal: logits, all gradient arrays, three-update weights and first-epoch weights against cap1. Two independent identical three-update runs also matched locally. Independent central finite differences checked the largest-magnitude gradient entry in each of 11 parameter tensors per process: **33 checks passed**, maximum absolute error 3.10e-12, with predeclared tolerance 2e-8 + 2e-5 × |numerical gradient|. These checks establish local CPU benchmark consistency; they do not establish GPU equivalence or universal cross-platform determinism.

A float64 `5e-324` threshold casts to **0.0 in float32**, verified directly. GPU scores would therefore still require host float64 decoding and the unchanged next-float rule. Keeping the decoder on CPU does not make float32 GRU training equivalent to the frozen float64 computation. A future comparison must preserve max/tie gradients, causal state alignment, imported NumPy initialization, Adam bias correction/epsilon/clipping, stopping/rate selection, calibrated candidate rules, and resume state.

## Backend assessment

| Option | Assessment |
| --- | --- |
| Current NumPy/Accelerate CPU | Installed, measured, preserves the frozen float64 model and checkpoint machinery. Suitable now. |
| MLX GPU | Most plausible first experimental candidate for this Mac, **not a demonstrated winner**. Unified memory and graph compilation could reduce overhead; float64 arrays work only on CPU. A custom cell and precision amendment would be needed. |
| PyTorch MPS | Not installed; GPU float64 unsupported. Built-in GRU is not this model and cannot be substituted. A custom cell has unmeasured dispatch/autograd costs. |
| Custom Metal/Core ML/other frameworks | No tested equivalent backend is installed. Custom kernels add substantial maintenance and verification; inference deployment does not reproduce full BPTT/Adam. No supported advantage established. |

The reset order in the built-in [PyTorch GRU](https://docs.pytorch.org/docs/main/generated/torch.nn.GRU.html) and [MLX GRU](https://ml-explore.github.io/mlx/build/html/python/nn/_autosummary/mlx.nn.GRU.html) differs from the frozen cell. Their update-gate convention and returned state timing also need explicit mapping; extra default biases must not add trainable parameters.

[MLX data types](https://ml-explore.github.io/mlx/build/html/python/data_types.html) explicitly restrict float64 operations to CPU. [PyTorch's MPS documentation](https://docs.pytorch.org/docs/main/notes/mps.html) likewise excludes float64 GPU tensors. These are correctness blockers under the unchanged numerical protocol, independently of performance.

For 1000 sequential steps with hidden size 16, dispatch, graph construction, autograd bookkeeping and synchronization are plausible bottlenecks; speedup cannot be inferred from GPU specifications. [MLX unified memory](https://ml-explore.github.io/mlx/build/html/usage/unified_memory.html) avoids explicit movement between its CPU/GPU memory pools, while dependencies and materialization still matter. Any future timing must warm up [compiled graphs](https://ml-explore.github.io/mlx/build/html/usage/compile.html), force evaluation/synchronize, include optimizer work, and separately report setup. [MLX numerical precision settings](https://ml-explore.github.io/mlx/build/html/usage/precision.html) would also need explicit verification. These are considerations, not measured overheads on this GRU.

## Runtime implications and decision

Using the unchanged CPU cap1 median, all **120 trials project to 1.13–10.77 hours** at the frozen earliest-stop 21 / maximum 200 epochs. This assumes first-epoch throughput transfers to other seeds, rates, epochs and five spatial mappings; it is not measured full training.

The newly timed reference clip projects about **1.17 hours** for 744 × 384 fixed-rate responses. GRU scoring for 60 × 384 calibration clips projects about 0.039 hours. Decoder cost projects about 0.126–0.663 hours for 816 conditions with 2–32 candidates, including training sustained scores, validation candidate assessments and selected-threshold behavior diagnostics. Candidate counts are bounds, not observed calibration outcomes.

Together, these measured-component extrapolations give **2.46–12.64 hours**, plus unmeasured spatial preparation, minimal-control fitting/scoring, score-cache/metadata/hash I/O and freeze overhead. A reliable complete Phase 11A wall-clock duration is **not established**. Accelerating GRU training alone would leave the other CPU work. GPU runtime/speedup is **not measured**, with no supported acceleration factor.

These short runs do not quantify multi-hour thermal throttling on a fanless Air; sustained performance may differ. Thermal telemetry was unavailable in the audit session. There is no measured throttling factor to apply.

GPU adoption is not worthwhile on the present evidence. A future experiment would require approval to install a compatible, pinned framework in an isolated environment, and explicit authorization for a versioned float32 numerical condition. Separate migration approval would follow only after forward/gradient/optimizer/controlled-training/resume and decoder checks pass with justified tolerances and an end-to-end speedup is measured. No production migration, precision change or dependency installation was performed.

## Preservation and evidence

`preservation_verification.json` confirms **3,097 pre-existing files unchanged** and the installed distribution set unchanged. Production sources, configurations, result indices, hashes and the Phase 11 job ledger were preserved. No commit/push occurred. `audit.py`, component script, exact commands/logs, raw timings, comparison arrays, native Metal result, numeric checks and summary are saved in this audit directory. No process continues in the background.
