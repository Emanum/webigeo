# Settings and extending

## Solver settings

`MpmSolverSettings` in `MpmSolverNode.h`. Defaults; the map graph preset's values in brackets.
Material parameters: [07-constitutive-models.md](07-constitutive-models.md#parameters).

| Setting | Default | Meaning |
|---|---|---|
| `domain_center`, `domain_size_xy` | —, 1024 m [4000] | Simulated box in metres on the ground; clamped to the region |
| `grid_resolution_xy` | 64 [320] | Nodes along x and y; dx = `domain_size_xy` / `grid_resolution_xy` |
| `grid_layers` | 12 | Band layers per column; ceiling at `dx · (layers − 2.5)` above the band floor |
| `release_center`, `release_radius` | —, 120 m | Release disc |
| `num_particles` | 65536 | Release particles |
| `slab_thickness` | 1.5 m | Depth of the released snow (disc mode) |
| `dt` | 0.01 s [0.02] | Time step; lowered to 80 % of `max_stable_dt()` before any run that exceeds it |
| `substeps_per_run`, `substeps_per_submit` | 32 [24], 2 | Run and chunk size for Manual pacing and the node editor's Step; otherwise set by the clock ([13](13-simulation-driver.md)) |
| `gravity` | 9.81 m/s² | |
| `terrain_friction`, `voellmy_xi` | 0.47, 4000 m/s² | Basal friction ([07](07-constitutive-models.md#basal-friction)) |
| `raster_resolution`, `splat_radius` | 512, 6 m | 2D density raster |
| `random_seed` | 1 | |
| `stop_kinetic_fraction` | 0.01 | `at_rest()` threshold; 0 = never |
| `seed_anywhere` | false | Seed the whole domain |
| Entrainment settings | | [15-entrainment.md](15-entrainment.md#panel-controls) |

Particle count, grid resolution, grid layers, raster resolution, model, entrainment and cover
changes reseed.

### Detail presets (panel)

| Detail | Particles | Grid layers |
|---|---|---|
| Low (fast) | 32768 | 10 |
| Medium | 65536 | 12 |
| High | 131072 | 16 |

## Readouts

| Readout | Source |
|---|---|
| Particles, plastic %, max speed, terrain range | `last_state()` |
| μ_eff, set μ, difference, sparkline | `energy_line()`, `energy_line_friction()`; under Voellmy the difference includes the drag |
| "Box edge reached" | Share of particle-substeps touching the band ceiling or domain walls |
| CFL bound | `max_stable_dt()`; orange in the node editor when `dt` exceeds it |
| Speed, budget | Simulation clock ([13](13-simulation-driver.md#panel)) |

## Troubleshooting

| Symptom | Fix |
|---|---|
| Nothing seeded | Move the release onto a 30–45° release slope or tick Seed anywhere |
| Nothing visible | Raise `splat_radius` |
| Flow stops at an invisible wall | Enlarge or move the domain (and the region if clamped) |
| Flow flattens at a fixed height | Raise `grid_layers` |
| Controls greyed out | Run the graph once (`Shift+R`) |
| Momentum saturation | Keep particles per cell × speed below 2·10⁵ (fewer particles or a larger release) |

## Where to make changes

| To | Touch |
|---|---|
| Add a constitutive model | `mpm_material_<name>.wgsl` + `mpm_material.wgsl` ([below](#adding-a-constitutive-model)) |
| Add a basal friction model | A case in `mpm_friction.wgsl` + `enum BasalFrictionModel` |
| Change the transfer kernel | `compute_kernel()` and the P2G/G2P loops |
| Change the 2D visualisation | `mpm_splat`, `mpm_rasterize` |
| Add a scenario | A `Scenario` entry in the `AvalanchePanel` constructor |
| Add a setting | [Adding a uniform field](#adding-a-uniform-field) |

### Adding a uniform field

1. `MpmSolverSettings` (C++).
2. `MpmSolverSettingsUniform` and `MpmSettings` in `mpm_common.wgsl`, same offsets.
3. The `static_assert` size.
4. `update_gpu_settings()`.
5. `serialize_settings()` / `deserialize_settings()`.
6. Panel or node editor control.

### Adding a constitutive model

1. `webgpu/compute/shaders/mpm_material_<name>.wgsl` with `///use mpm_common`:
   `<name>_initial_state() -> f32` and `<name>_plasticity(F_trial, state) -> PlasticReturn`
   (returned F, state, `kirchhoff` = P·Fᵀ from the same SVD, `yielded`). Parameters from
   `settings.*`; E and ν (`mu_0`, `lambda_0`) are shared.
2. `mpm_material.wgsl`: `///use` the file, a `MATERIAL_<NAME>` constant, a case in both switches.
3. `MpmSolverNode.h`: a value in `enum ConstitutiveModel` equal to the WGSL constant.
4. `MpmSolverNodeRenderer.cpp`, `AvalanchePanel.cpp`: append to the model combo in enum order;
   show the model's parameters.
5. `webgpu/compute/CMakeLists.txt`: add the shader to the resource list.

Basal friction has the same shape. A contact-impulse term may run at both call sites; a
velocity-dependent drag runs only where `apply_basal_drag` is true (the grid update).
