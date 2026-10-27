# Actual simulation demonstration, 2026-10-27

The unchanged historical simulator streamed real computed world positions, images, neural states, encoder drive and first-event decisions to the dashboard. The 0.1× pacing affected wall time only. Runs are finished, not looping. Live follows the most recent session and displays its end state; the archive provides full synchronized replay.

See ../runs/live_demo_20261027_summary.json for the complete aggregate. Fifteen physical attempt slots were reserved, thirteen recordings were independently checked and exactly matched saved reference arrays/metrics. Eleven dangerous cases escaped; two harmless cases made no request. One observer startup fault and one post-run schema-check fault remain excluded, without retry; a transport bootstrap fault consumed no physical attempt. Therefore this batch is incomplete as a 15-recording validation set. All error histories are retained.

Verified directional recordings include left seeds 55011–55014 and right seeds 55010–55014. Final X is positive for the former and negative for the latter. The finite gate uses backward actuation. The absent left/55010 verification is an adapter error, not favorable seed selection. Known fixtures and synthetic mappings establish engineering operation, not generalization or biological flight.

Original source and snapshot fingerprints, the production ledger and the partial checkpoint pointer remained unchanged across all launches. Training, threshold calibration and held-out evaluation were not run. New output is under dashboard/runs. The launcher refuses a further automatic demonstration after the aggregate is closed.
