# Simulation driver

Frame-by-frame playback of time-stepped compute nodes, driven from the app's render loop.
A guide for adding another simulation: [docs/time_stepped_simulations.md](../time_stepped_simulations.md).

## Call flow

```
App::render()                               every frame, GUI shown or hidden, before painting
 └─ ImGuiManager::tick_simulations() → SimulationDriver::tick(graph)
      └─ for each TimeSteppedSimulation node: clock().tick(simulation, wall_dt)
           ├─ accuracy:  advance(steps, chunks)
           └─ real time: advance_frame(steps, end_run), set_interpolation(alpha)
 └─ a simulation is playing → repaint
 └─ paint: AvalancheRenderer draws mix(previous, current, alpha)

AvalanchePanel::draw()                      when the GUI is shown
 └─ sync_clock(solver): mode, speed, interpolation, budget; play / pause / step
```

## Files

| File | Content |
|---|---|
| `webgpu/compute/TimeSteppedSimulation.h` | Interface: `can_advance`, `is_advancing`, `advance(steps, chunks)`, `advance_frame(steps, end_run)`, `set_interpolation`, `time_step`, `simulated_time`, `gpu_ms_per_step`, `at_rest`, `reset`, `clock()` |
| `webgpu/compute/SimulationClock.h/.cpp` | Play/pause/step, mode, speed, interpolation, budget, presentation time, measured speed. No GPU or Qt |
| `webgpu/compute/SimulationDriver.h/.cpp` | Finds implementing nodes by `dynamic_cast`, ticks their clocks with the frame time, reports whether one plays |

The clock is owned by the simulation node.

## Modes

| Mode | Default for | Behaviour |
|---|---|---|
| Accuracy | sandbox, batch | Chunk = budget / GPU ms per step (1–64, 1/8 hysteresis); run = max(2 chunks, 24 steps); a new run when the previous one is done; two chunks in flight; no interpolation |
| Real time | map | One chunk per frame, fixed-step loop with interpolation; speed 0.1–4× |

Real-time loop per frame:

```
T     += wall_dt × speed                          wall_dt clamped to 0.25 s
steps  = ceil((T − S) / dt), at most the budget   S: simulated time
advance_frame(steps, end_run = every 8th chunk)
T      = min(T, S + dt)
alpha  = (T − S_before) / (S_after − S_before)    1 without interpolation
```

- Budget: `budget_ms` / best GPU ms per step since the reset, fractional, carried between frames
  (credit ≤ budget + 1 steps). `advance_frame()` refuses while three chunks are in flight.
- A run closes every 8 chunks; it counts as done when its last chunk is submitted. Pause or a
  switch to accuracy closes an open run with an empty chunk.
- "Behind": measured speed over 1 s windows below 90 % of the target, cleared above 95 %.
- T resyncs to S after changes not made by the clock (first frame, Step, reset).

Pacing budgets (GPU ms per frame): Smooth 6, Balanced 14, Fast 30; Manual uses
`substeps_per_run` / `substeps_per_submit`.

## `MpmSolverNode`

- `advance()` overrides `substeps_per_run` / `substeps_per_submit` for one run without writing
  them; `submit_chained_chunk()` takes an even share of the run's substeps.
- `advance_frame()` opens a run through `rerun()` or submits the next chunk of the open run;
  `close_frame_run()` ends it. `on_chunk_done(slot, substeps, run_serial)` continues only the
  current chained run.
- Before every real-time chunk `submit_chunk()` copies the particle buffer into
  `m_previous_particles`. Not on the reseeding chunk, not in accuracy runs (then
  `previous_particles` is null); an empty closing chunk leaves it unchanged.
- `render_avalanche.wgsl`, `render_avalanche_powder.wgsl` and `avalanche_surface_splat.wgsl`
  interpolate positions; velocity, strain rate and mass come from the current state. The 2D
  overlay, diagnostics and energy line update once per run.

## Panel

"Playback" (Real time / Accuracy), "Speed" and "Interpolate" (real time), "Pacing".

| QSettings key | Default |
|---|---|
| `playback/map_mode`, `playback/map_pacing` | Real time, Smooth |
| `playback/sandbox_mode`, `playback/sandbox_pacing` | Accuracy, Balanced |
| `playback/speed`, `playback/interpolate` | 1×, on |

Batch mode plays at accuracy, Fast. Readout: "Speed: 1.00x real time, budget N substeps/frame",
in orange with "behind" when behind; in accuracy "Speed: N.Nx real time, N substeps/frame".
