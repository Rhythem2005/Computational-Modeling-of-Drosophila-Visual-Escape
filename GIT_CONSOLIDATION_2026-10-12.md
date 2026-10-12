# Git consolidation — 12 October 2026

The user authorized committing and pushing saved project phases directly to `main`, followed by removing other branches once preservation and remote verification succeed. This supersedes the earlier session's no-commit/no-push restriction for this Git maintenance task. Implementation remains paused after Phase 9 for study.

## Preflight findings

- Refreshed origin: `main` was `10c62793e4c82f6620df39872e386aff93d6af8c`. Phase 5.5 was committed at `8ef70f3d099e3bfa19d32daf3b5ae43437287f5c`; Phase 6 was committed at `10c62793e4c82f6620df39872e386aff93d6af8c`. Both phase directories and scripts were already present on origin/main. Phase 7 was absent remotely and uncommitted locally; saved Phases 8/9 and STUDY_CHECKPOINT.md were also uncommitted.
- Local main was 11 commits behind; working branch `phase6-main-push` already matched origin/main. Main was fast-forwarded to it, then checked out, preserving working files.
- No open repository PRs were returned by the connected GitHub search. Historical PRs #1–#6 were found; their branches were inspected through actual fetched refs/history.
- Original Phase 6 commit `b3aacab56b06b600398b0f3e577e5d45beb91d84` is patch-equivalent to the published Phase 6 change. Its tree differs from origin/main only in README.md; the current main README was retained.
- Phase 4 PR tip `aef8b78ed722ea015ba8898eebccb02eb1c504a7` is patch-equivalent to main's `169712a` and their complete trees match. Both original branch tips were integrated with ancestry-preserving merges retaining main's content. No history was rewritten.
- Six existing Phase 1 working-tree deletions were left unstaged and unchanged. These files remain in committed history and on origin/main. Missing legacy aliases and the earlier README compatibility issue remain as documented in Phase 9.

## Preservation and saved artifacts

- Before mutation, created a verified all-refs Git bundle, a compressed archive of 2,304 existing project files, SHA-256 inventory, tracked deletion patch, and refs/status/history records under `/var/folders/ny/1v8103651lxbgv3ms88n0yyw0000gn/T/fly-main-preservation-5w4_hvei/`.
- Existing stash was retained. All 892 untracked files in its snapshot match current files byte-for-byte; its tracked/index changes were empty. The backup bundle retains the stash objects and all original branches.
- Saved Phase 9 workspace inventory: 2,139 files verified unchanged. Phase 8 completion delivery index: 525 hashes verified. Phase 9 delivery index: 126 hashes verified. No earlier output-overwriting validator was run for this maintenance task.
- Included saved Phase 7/8/9 code, configurations, tests, results, plots and documentation, the study checkpoint, and 21 previously ignored earlier evidence files needed by saved preservation inventories. Cache files, environments and raw datasets remain excluded.
- Scientific results are unchanged. Earlier test counts and episode outcomes are historical evidence described in STUDY_CHECKPOINT.md, not new experiments during Git maintenance.

## Completion conditions

Push uses ordinary fast-forward Git push. Before deleting any other branches, verify fetched origin/main equals local main, contains all original branch tips, and contains byte-identical saved phase files including forced-included evidence logs. Recheck that no open PR has appeared. Only branches fully preserved in main may be deleted; retain the existing stash and recovery copies. The final chat report records the resulting commit and branch verification.
