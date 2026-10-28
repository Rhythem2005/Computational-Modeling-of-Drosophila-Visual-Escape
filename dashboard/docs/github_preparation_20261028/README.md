# GitHub preparation — 28 October 2026

This is an index/ignore cleanup, not a commit or a history rewrite. Scientific
files and results remain locally in place. Existing source modifications remain
unstaged; generated-file removals are staged because index-only untracking requires
an index change. Review these separately before approving a future commit.

## Inclusion policy

Keep source, tests, configuration, sanitized environment examples, dependency
lockfiles, documentation, protocols, provenance hashes, calibration/normalization
metadata and the compact frozen Phase 3 circuit CSV/JSON required by runtime code.
Keep lightweight historical reports rather than rewriting scientific history.
Exclude raw Feather data, bulk discovery exports, generated NumPy arrays, model
weights/checkpoints, episode bundles, private runtime snapshots, recordings,
virtual environments, dependencies, builds, caches and local credentials. Removed
old Phase 1–9 array exceptions. Fixed ineffective report exceptions by ignoring
result-directory children rather than their parent. Dependency lockfiles are no
longer covered by a blanket `*.lock` rule.

The retained frozen circuit is an intentional exception to excluding connectome
data: it is the small versioned model specification used by the neural loader and
dashboard. It is not a full raw dataset. Its largest file is under 4 MiB.

## Reproducing from a fresh clone

A source clone is not a complete scientific artifact archive. Restore separately
archived, hash-matching artifacts to their original relative paths to inspect or
replay existing experiments. In particular, full frozen historical validation and
snapshot checks may require excluded arrays and derived data. Do not regenerate
missing results by silently starting training or evaluation; follow each phase's
protocol and obtain authorization. Existing local replay remains available because
index cleanup deletes no working files.

Raw MaleCNS inputs are version-pinned in project configuration/provenance. Acquire
them separately using the existing acquisition scripts and authorized credentials;
compare against recorded hashes. Do not place tokens in source or tracked files.
Use `.env.example` / `dashboard/.env.example` as templates. Dashboard runtime
credentials are generated locally by its launcher and stay in `.runtime/`.

Python dependencies are declared in root and dashboard requirements files. The
frontend has a versioned package-lock.json; use that lockfile when separately
setting up dependencies. Python requirements are not fully version-pinned, so
bit-for-bit environment reproduction is not guaranteed by the repository alone.
Frontend dist and local environments are intentionally omitted; build/setup is a
separate explicit operation. This preparation did not install or build anything.

## Review artifacts and risks

- `audit.json`: candidate sizes, local oversized-file inventory, secret-signature
  findings and preservation check.
- `included-files.txt`: tracked and nonignored new-file candidates for a future
  add/commit; this report's own files are included in the final inventory.
- `untracked-artifacts.txt`: paths removed from the index, still present locally.

Git push sends committed history, not working-tree or index changes. No cleanup
is published until a separately approved commit and push. Historical artifact
versions remain in the existing approximately 1.7 GiB `.git` directory. Untracking
shrinks future snapshots, not that history. No reachable blob >=50 MiB was found.
Do not rewrite history or run destructive cleanup without explicit approval.

Secret checks use known credential signatures and exact matches to existing local
credentials without printing their values. These checks cannot rule out unknown
credentials or sensitive prose. A final human review is still appropriate before
public publication. Historical reports also contain local filesystem paths and
scientific metadata; these were preserved rather than sanitized destructively.

Verification: 1,835 index-only removals, all local hashes unchanged; zero ignored
files remain tracked; 18 ignore-policy checks passed. Current candidates and
selected historical text-diff signatures had no credential matches. Historical
sensitive-filename checks also returned no matches. No training or simulations ran.
