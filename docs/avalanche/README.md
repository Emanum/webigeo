# MLS-MPM avalanche simulation

Technical reference of the MLS-MPM snow avalanche solver in weBIGeo.

Detailed documentation (design rationale, verification, performance analysis and benchmarks,
AvaFrame comparison, scripts) is in the project repository:
[Emanum/webigeo, `mpm-mls-doc/`](https://github.com/Emanum/webigeo/tree/main/mpm-mls-doc).

## Components

| Component | Where | Doc |
|---|---|---|
| GPU MLS-MPM solver: three constitutive models, Coulomb and Voellmy friction, entrainment, terrain-following grid | `MpmSolverNode`, `webgpu/compute/shaders/mpm_*.wgsl` | [01](01-theory.md), [03](03-shaders.md), [04](04-data-layout.md), [07](07-constitutive-models.md), [15](15-entrainment.md) |
| Playback of time-stepped nodes (real time, accuracy) | `TimeSteppedSimulation`, `SimulationClock`, `SimulationDriver` | [13](13-simulation-driver.md) |
| Raw grid view for visualisation and export | `MpmSolverNode::raw_view()` | [16](16-raw-grid-view.md) |
| 3D rendering on the map | `AvalancheRenderer`, `ParticleRenderNode` | [12](12-rendering.md) |
| Switchable overlays | `Overlay::enabled` | [02](02-files-and-api.md) |
| AvaFrame sandbox and release areas on the map | `AvaFrameSandboxNode`, `AvaFrameReleaseNode`, `AvaFrameData` | [14](14-avaframe-release-on-map.md) |
| Avalanche panel, scenarios, graph presets, `GeoRegionNode` | `apps/webgpu_app/avalanche/` | [02](02-files-and-api.md) |

## Documents

| File | Content |
|---|---|
| [01-theory.md](01-theory.md) | Methods per stage and their references |
| [02-files-and-api.md](02-files-and-api.md) | Files added and modified, node sockets and methods |
| [03-shaders.md](03-shaders.md) | Dispatch order, bindings, kernels |
| [04-data-layout.md](04-data-layout.md) | Structs, buffers, fixed point, uniform, terrain-following grid |
| [05-tuning.md](05-tuning.md) | Settings, readouts, extending |
| [07-constitutive-models.md](07-constitutive-models.md) | Material and friction models, presets |
| [12-rendering.md](12-rendering.md) | 3D rendering |
| [13-simulation-driver.md](13-simulation-driver.md) | Playback |
| [14-avaframe-release-on-map.md](14-avaframe-release-on-map.md) | AvaFrame release areas on the map |
| [15-entrainment.md](15-entrainment.md) | Entrainment |
| [16-raw-grid-view.md](16-raw-grid-view.md) | Raw grid view |
| [refs.md](refs.md) | References |

## Node graph

```
Region ─→ Select Tiles ─→ Request Height ─→ Stitch Tiles ─→ Height Decode ─┬─→ Normals ─→ Release Points ─┐
                                                                           └──────────────┬───────────────┘
                                                                                          ↓
                                                                                     MPM Solver ─┬─→ Overlay       (2D density)
                                                                                                 └─→ Particles 3D  (AvalancheRenderer)
```

Sandbox graph: `AvaFrameSandboxNode` → `MpmSolverNode`. Map graph with AvaFrame scenarios:
`AvaFrameReleaseNode` → `MpmSolverNode` "release area".

## Execution

One node run = a number of substeps, continuing from the current state. Each submitted chunk
is one compute pass:

```
sort particles by tile (once per chunk)
per substep: P2G → grid update → G2P + advection
```

The `SimulationDriver` advances the solver every frame ([13](13-simulation-driver.md)).

Implementation and documentation were written with AI assistance (Claude Code).
