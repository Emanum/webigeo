# Entrainment

The flow picks up snow cover along its path with com1DFA's two entrainment modes, plowing and
erosion (Tonnel 2023; com1DFA 2.1 defaults).

| Context | Snow cover | Default mode |
|---|---|---|
| AvaFrame sandbox | AvaFrame's entrainment area (ENT shapefile, 0.3 m where a feature has none) | Off |
| Map, AvaFrame scenarios | The same area, resampled onto the map region | Erosion |
| Map, generic scenarios | `cover_thickness` (slope-normal) on slopes up to `cover_max_slope` | Erosion |

The release area is always excluded from the cover.

## Implementation

1. **Reset** (`mpm_prepare`): each column's cover from 4 × 4 samples of `cover_depth_at()` over
   its dx × dx cell (cover texture, or `cover_thickness` / cos(slope) up to the slope limit),
   without samples under the release (`under_release()`). Stored in `column_stats.cover` [m³],
   summed into `SimState.cover_volume`.
2. **Every substep** (`entrain_column()` in `mpm_grid_update`), for columns with flow at or above
   `entrainment_min_speed`, from the column's flow depth and mass-weighted node speed:
   - Plowing: the whole cover once the flow depth reaches `plowing_depth`.
   - Erosion: com1DFA's erosion rate with `erosion_energy` and the basal shear stress of the
     active friction model (Coulomb, or Coulomb + Voellmy drag).
3. **Particles**: eroded snow becomes pool particles (slots after the release particles), each
   with a release particle's mass; cover volume per particle =
   `seeded_particle_volume()` · ρ_snow / `entrainment_density`. Remainders below one particle
   wait in `column_stats.eroded`; at most 64 new particles per column and substep. New particles
   lie at rest on the column's ground, written with negative mass; G2P makes the mass positive,
   the next P2G adds it without momentum.
4. **Pool full**: the rest stays in the cover and is counted in `SimState.pool_exhausted`.

Pool slots are handed out by a global atomic counter, so runs with entrainment are not
bit-reproducible. There is no deposition back into the cover.

## Files

| File | Role |
|---|---|
| `apps/webgpu_app/avalanche/AvaFrameData.cpp` | Rasterises the ENT shapefile: `entrainment.asc` (slope-normal thickness), `"entrainment"` in `dataset.json` |
| `webgpu/compute/nodes/AvaFrameSandboxNode.h/.cpp` | `SandboxTerrain::entrainment_*`: vertical depth without the release cells; `entrainment_texture` |
| `webgpu/compute/nodes/AvaFrameReleaseNode.h/.cpp` | `resample_depth()`, `ReleaseArea::entrainment_*` |
| `webgpu/compute/nodes/MpmSolverNode.h/.cpp` | `EntrainmentMode`, settings, `plan_cover()` (cover source and pool size per reset), readback (`cover_volume`, `entrained_*`, `pool_exhausted_volume`) |
| `webgpu/compute/shaders/mpm_common.wgsl` | Uniform fields, `ENTRAINMENT_*` / `COVER_*`, `SimState` counters, `ColumnStats.cover` / `.eroded`, binding 12, `cover_depth_at()`, `under_release()` |
| `webgpu/compute/shaders/mpm_prepare.wgsl` | Cover per column |
| `webgpu/compute/shaders/mpm_grid_update.wgsl` | `entrain_column()` |
| `webgpu/compute/shaders/mpm_g2p.wgsl` | Negative → positive mass, at rest |
| `webgpu/compute/shaders/mpm_seed.wgsl` | Pool slots inactive |
| `webgpu/engine/shaders/avalanche_surface_field.wgsl`, `render_avalanche_surface.wgsl` | Entrainable snow on the map ([12](12-rendering.md)) |
| `apps/webgpu_app/avalanche/AvalanchePanel.cpp` | `draw_entrainment()`, `sync_entrainment()`, `"entrainment"` block in the export's `params.json` |

## Panel controls

| Control | Setting | Default |
|---|---|---|
| Entrainment (Off / Plowing / Erosion) | `entrainment_mode`, per context | map Erosion, sandbox Off |
| Erosion energy | `erosion_energy` | 5000 J/kg |
| Pick-up depth (plowing) | `plowing_depth` | 0.1 m |
| Minimum speed | `entrainment_min_speed` | 1 m/s |
| Cover thickness, Cover up to (generic map scenarios) | `cover_thickness`, `cover_max_slope` | 0.3 m, 50° |
| Cover density | `entrainment_density` | 100 kg/m³ |
| Pool size (node editor) | `pool_size`, particles per release particle | 2 |

Mode and cover changes reseed. Readout: cover in the domain, entrained volume (as cover) and
mass, a warning when the pool ran out.
