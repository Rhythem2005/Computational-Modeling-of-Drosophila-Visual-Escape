# Phase 5 initial audit

Starting working tree: clean. `./venv/bin/python -m pytest connectome/phase5/tests/ -q`: **11 passed**, one deprecated UTC timestamp warning.

| Decision | Evidence / action |
| --- | --- |
| Keep | Deterministic circle mask, uint8 grayscale, `(T,H,W)` layout, floor frame count, translation direction convention, and four-value loader return. |
| Fix | Generation accepts unchecked dictionaries; validate every entry point, numeric types, finite values and memory limits. |
| Fix | Looming validation and generation differ around onset; share the trajectory and document the abstract distance margin. |
| Fix | Fast diagnostic uses v=80 with Z0=50 over 0.8 s, crossing collision; replace with a valid trajectory. Existing diagnostics exited 134 with the default plotting backend in this session; use Agg. |
| Fix | Loader trusts dimensions/config and has no version or integrity checks. |
| Fix | README points to nonexistent `connectome/scripts/phase5/tests/`. |
| Remove | Blanket deletion of every report PNG; unrelated plots must survive regeneration. |
| Replace | Report generator hard-codes completion, old hashes and Phase 4 counts; derive Phase 5 evidence from executed checks. |
| Missing | CLI, saved sample frame arrays and config snapshots, per-frame geometry/timestamps, edge-case tests and protected-file baseline. |

Changes stay within Phase 5. No stochastic rendering is needed; seed is provenance only. The validation report maps each change to regression coverage.
