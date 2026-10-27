# Disk estimate made advisory

User requested removal of the disk-space startup blocker. Live preflight and profiling retain measured disk space and conservative estimates as warnings, without blocking on that estimate. This does not prevent real ENOSPC write failures. The original conservative estimate includes duplicate workspace/artifact storage and a 5 GiB reserve.

Worker exclusivity, checkpoint/frozen integrity, memory, low battery and thermal checks remain active. Training mathematics, schedule and outputs are unchanged. Changes: runtime.py, resources.py, tests/test_manual_resume.py, common.py exact source-compatibility scope. Previous compatibility certificate and source bytes are archived here. Updated certificate records actual execution hashes while preserving checkpoint source identity.

Verification: 561 tests passed, zero failures/errors/skips in disposable copies. Low-space inputs (including zero in a mock) pass with a recorded warning; other guards remain tested. Existing epoch 181 / offset 160 / Adam 2890 checkpoint loaded without training. All 263 bound production artifacts and frozen inventory unchanged. Four unapproved source mutations rejected. No production jobs or held-out inference executed. Existing compute profile reused; no current live resource PASS is asserted. Disposable test copies cleaned after preserving logs.
