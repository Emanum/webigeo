# Files and API

## Added

### Solver (`webgpu/compute/`)

| File | Purpose |
|---|---|
| `nodes/MpmSolverNode.h/.cpp` | The solver: particles, grid and state on the GPU, the substep loop, readbacks, `raw_view()` ([16](16-raw-grid-view.md)) |
| `nodes/GeoRegionNode.h/.cpp` | Region AABB from latitude, longitude and extent |
| `nodes/AvaFrameSandboxNode.h/.cpp` | Loads an AvaFrame dataset (DEM, release, entrainment area, com1DFA footprint) as `SandboxTerrain`, in metres |
| `nodes/AvaFrameReleaseNode.h/.cpp` | AvaFrame release and entrainment areas resampled onto the map region as `ReleaseArea` ([14](14-avaframe-release-on-map.md)) |
| `TimeSteppedSimulation.h` | Interface of a frame-by-frame simulation ([13](13-simulation-driver.md)) |
| `SimulationClock.h/.cpp` | Per-simulation playback: real time or accuracy, play/pause/step, speed |
| `SimulationDriver.h/.cpp` | Ticks every `TimeSteppedSimulation` in the graph once per frame |
| `shaders/mpm_*.wgsl` | The solver kernels and modules ([03](03-shaders.md)) |

### Rendering (`webgpu/engine/`)

| File | Purpose |
|---|---|
| `avalanche/AvalancheRenderer.h/.cpp` | 3D particles, flow surface, track, entrainable snow ([12](12-rendering.md)) |
| `shaders/render_avalanche*.wgsl`, `shaders/avalanche_surface_*.wgsl` | Its shaders |

### App (`apps/webgpu_app/`)

| File | Purpose |
|---|---|
| `avalanche/AvalanchePanel.h/.cpp` | Sidebar panel: scenarios, transport, playback, material presets, entrainment, 3D view, sandbox export and batch |
| `avalanche/SandboxView.h/.cpp` | 2D view of sandbox runs: hillshade, release, com1DFA outline, particles, domain |
| `avalanche/AvaFrameData.h/.cpp` | Downloads AvaFrame 2.1's five test avalanches and prepares them as sandbox datasets |
| `compute/ParticleRenderNode.h/.cpp` | Node "Particles 3D": hands the particle view to `AvalancheRenderer`, owns the "Avalanche snow cover" overlay |
| `compute/nodes/MpmSolverNodeRenderer.h/.cpp` | Node editor settings of the solver |
| `resources/graphs/mpm_avalanche_simulation.json` | Map graph preset |
| `resources/graphs/mpm_avaframe_sandbox.json` | Sandbox graph preset: `AvaFrameSandboxNode` → `MpmSolverNode` |

## Modified

| File | Change |
|---|---|
| `webgpu/compute/CMakeLists.txt`, `apps/webgpu_app/CMakeLists.txt`, `apps/webgpu_app/resources.qrc` | Sources, shaders, graph presets |
| `webgpu/compute/NodeRegistry.cpp` | Registers `MpmSolverNode`, `GeoRegionNode`, `AvaFrameSandboxNode`, `AvaFrameReleaseNode` |
| `webgpu/compute/nodes/Node.h` | `const SandboxTerrain*`, `const MpmParticleView*`, `const ReleaseArea*` in the socket data variant |
| `apps/webgpu_app/compute/nodes/NodeRendererFactory.cpp` | Solver node renderer |
| `apps/webgpu_app/compute/NodeGraphPanel.h/.cpp` | `node_graph()` accessor, public `load_preset()`, preset entries |
| `apps/webgpu_app/ImGuiManager.h/.cpp`, `App.cpp` | Registers `AvalanchePanel`; owns the `SimulationDriver`; `App::render()` calls `tick_simulations()` before painting and repaints while a simulation plays |
| `webgpu/engine/Context.h/.cpp`, `apps/webgpu_app/RenderingContext.cpp` | Context owns the `AvalancheRenderer`; registers `ParticleRenderNode` |
| `webgpu/engine/Window.cpp` | Calls `prepare()`, `draw()`, `draw_transparent()` |
| `webgpu/engine/overlay/Overlay.h`, `OverlayRenderer.cpp` | `Overlay::enabled`: disabled overlays are skipped |
| `apps/webgpu_app/compute/OverlayRenderNode.h/.cpp` | `set_overlay_enabled()` |
| `webgpu/engine/overlay/ScreenSpaceSnowOverlay.h/.cpp`, `shaders/overlays/screen_space_snow.wgsl`, `apps/webgpu_app/overlay/ScreenSpaceSnowOverlayImGuiRenderer.cpp` | Skips pixels with the avalanche marker; `patches` setting |

## `MpmSolverNode`

Namespace `webgpu_compute::nodes`, subclass of `Node` and `TimeSteppedSimulation`.

### Sockets

| In | Type | |
|---|---|---|
| `region aabb` | `Aabb<2,double>*` | |
| `height texture` | `TextureWithSampler*` | R32Float |
| `release point texture` | `TextureWithSampler*` | Release mask (map) |
| `sandbox` | `const SandboxTerrain*` | Optional. Region in metres, domain from the dataset, release texture as vertical depth per cell (`release_mode = 1`) |
| `release area` | `const ReleaseArea*` | Optional, map only. Seeds from its depth texture instead of the disc |

| Out | Type | |
|---|---|---|
| `texture` | RGBA | 2D density raster |
| `domain aabb` | AABB | World bounds of the simulated domain |
| `density buffer` | `RawBuffer<u32>*` | |
| `raster dimensions` | `uvec2` | |
| `particle buffer` | `RawBuffer<u32>*` | |
| `particle view` | `const MpmParticleView*` | Particle buffers and count, previous particles and interpolation, metres → world affine, spacing, grid origin/dx/columns, `column_stats`, height texture, region size, `reset_count`, `layout_version` |

### Methods

| Method | |
|---|---|
| `run_impl()` | Optional reset, then the run's substeps in chunks (`submit_chunk()`), then splat and rasterize |
| `advance(steps, chunks)` | `TimeSteppedSimulation`: one chained accuracy run, without writing the settings |
| `advance_frame(steps, end_run)` | `TimeSteppedSimulation`: one real-time chunk; refused while three chunks are in flight |
| `set_interpolation(alpha)` | Blend factor carried by the particle view |
| `submit_chunk()` | Encodes one chunk as one command buffer and compute pass; chained runs keep two chunks in flight |
| `perf_stats()` | Runs since reset, ms per run, GPU ms per substep (timestamp queries), GPU bytes |
| `has_valid_inputs()` | Sockets connected and payloads non-null |
| `request_reset()` | Rescan terrain and reseed on the next run |
| `simulated_time()` | Seconds since the last reset |
| `last_state()` | `SimStateReadback` of the previous completed run: active and yielding particles, max speed, terrain range, centre of mass, mean \|v\|², mean path, box contacts, seeded share, entrainment volumes |
| `energy_line()`, `energy_line_friction()` | `EnergySample`s since the reset (at most 2048) and the fitted effective friction |
| `at_rest()` | Mean kinetic energy below `stop_kinetic_fraction` (0.01) of its peak |
| `read_back_peaks(callback)` | `ColumnPeaks`: peak depth and speed per column since the reset |
| `max_stable_dt(settings, dx)` | Static. CFL bound for these settings |
| `domain_aabb()`, `sandbox()`, `raw_view()` | Domain bounds, connected sandbox, raw grid view |
| `set_settings()`, `get_settings()`, `serialize_settings()`, `deserialize_settings()` | Settings, applied lazily in `run_impl()` |

Internals: `ensure_resources()` reallocates on size changes (clamped to the device's storage
binding limit) and forces a reset; `ensure_bind_group()` rebuilds on new buffers, input
textures or graph run id; `update_gpu_settings()` fills the uniform; asynchronous callbacks
hold a copy of `m_alive` (`shared_ptr<MpmSolverNode*>`, nulled in the destructor) instead of
`this`.

Output sockets are null until the node has run; code that drives the node outside graph order
checks `has_valid_inputs()` first.

## `GeoRegionNode`

No inputs. Output `region` (`Aabb<3,double>*`). Settings: centre latitude/longitude, extent
[m on the ground, scaled by 1/cos(latitude) for Web Mercator], min/max altitude.

## `AvalanchePanel`

- Finds the graph's nodes by `dynamic_cast` every frame (`find_node<T>()`).
- `apply_scenario()`: writes region, zoom, domain and release into the nodes, resets, pauses,
  runs the graph.
- `apply_material_preset()`: see [07](07-constitutive-models.md#material-presets).
- `sync_clock()`: writes mode, speed, interpolation and budget into the solver's clock; Play and
  Pause exist only here. The node editor keeps Step and Reset.
- 3D view controls and `ParticleRenderNode::sync_snow_cover()`: [12](12-rendering.md).
- Settings stored with `QSettings("weBIGeo", "avalanche")` (`startup/*`, `playback/*`,
  `entrainment/*`, `sandbox/*`), not in the graph JSON. Web build: no settings store; the
  sandbox folder lives in IndexedDB (IDBFS).

| Location | Settings |
|---|---|
| Sidebar | Scenario, transport, playback, detail, substeps, dt, splat radius, domain and release position/size, material preset, friction, entrainment, 3D view |
| Node editor | All solver settings |
