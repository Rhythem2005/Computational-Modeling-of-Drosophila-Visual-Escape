# Dashboard usability update — 28 October 2026

Local frontend changes only. Behavior development remains paused. Servers and
simulations were not started, scientific configurations and saved results were
not edited, and no dependency installation, commit or push occurred.

- Charcoal/near-black spectator environment and panels, retaining mint accents.
  Room geometry, fly and play/pause/timeline transport are retained.
- Persistent text labels on scene controls and a prominent Recordings button.
  View settings keep everyday toggles visible and move neural filters under
  Advanced. The circuit is hidden until requested to reduce visual clutter.
- The table is hidden by default in the spectator view. Recorded furniture can
  be restored in View settings. A visible note explains that recorded collision
  geometry and sensor images remain unchanged: these are existing experiment
  recordings, not new table-free physics. Other static solids remain visible.
- Human-readable scene/controller names, experiment filtering, search using both
  friendly and technical names, duration and run timestamp, optional raw names
  and repeats. Source IDs and paths are preserved. Unknown outcomes are explicitly
  unpublished; a completed recording is not automatically labeled a success or
  a silent episode. Room adjudication remains in the original run summary.
- Neuron explorer with population/ID/role search, stable ID or highest-signal
  ordering, synchronized raw activity/input values, model-role descriptions,
  linked 3D selection and strongest structural connections. Missing values and
  GRU states are not substituted for anatomical activity. Front room activity
  is labeled an uncalibrated diagnostic, not the cause of room avoidance.
- Keyboard/focus support and responsive controls; playback transport behavior
  and scientific clocks remain unchanged.

Verification: TypeScript/Vite production build passed; all 18 frontend checks
passed. All 134 protected scientific references match the room-run preflight. No browser
visual QA was performed because the servers were deliberately left stopped.
This update adds no new behavioral evidence. The latest room pilot remains
24 completed attempts, with surround avoidance succeeding in four of six
hazard directions and failing on left/right; the two harmless controls had
no surround-controller false alarm.
