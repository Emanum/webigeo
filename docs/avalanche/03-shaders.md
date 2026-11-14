# Solver shaders

All in `webgpu/compute/shaders/`. Every kernel `///use`s `mpm_common`, so all declare the same
bindings and share one bind group layout and bind group.

## Dispatch order

One chunk = one command buffer with one compute pass:

```
[clear buffers] density raster; on reset also grid, grid_velocity, tile_flags, column_stats
begin compute pass
  reset:                        mpm_prepare → mpm_seed
  stress parameters changed:    mpm_refresh_stress
  chunk has substeps:           mpm_sort_count → mpm_sort_scan → mpm_sort_scatter
  per substep:                  mpm_p2g → mpm_grid_update → mpm_g2p [→ mpm_column_stats, sandbox only]
  last chunk:                   mpm_splat → mpm_rasterize
end compute pass
last chunk: copy SimState → readback buffer
submit → work-done callback → next chunk, or map the readback
```

There is no grid clear kernel: `mpm_grid_update` zeroes the accumulators it reads.

## Bindings

| # | Binding | Type |
|---|---|---|
| 0 | `settings` | uniform `MpmSettings` |
| 1 | `height_texture` | R32Float, unfilterable |
| 2 | `release_point_texture` | RGBA8Unorm mask (map) or R32Float depth (release grid mode) |
| 3 | `particles` | storage `array<Particle>` |
| 4 | `grid` | storage `array<GridNode>` (atomics) |
| 5 | `state` | storage `SimState` (atomics) |
| 6 | `density_raster` | storage `array<atomic<u32>>` |
| 7 | `output_texture` | storage texture rgba8unorm, write |
| 8 | `column_floor` | storage `array<i32>` |
| 9 | `grid_velocity` | storage `array<vec4f>` |
| 10 | `tile_flags` | storage `array<atomic<u32>>`: tile flags, then the particle sort |
| 11 | `column_stats` | storage `array<ColumnStats>` |
| 12 | `entrainment_texture` | R32Float cover depth, unfilterable; 1×1 placeholder without one |

Eight storage buffers (WebGPU's default `maxStorageBuffersPerShaderStage`).

## Modules

| Module | Provides | Used by |
|---|---|---|
| `mpm_common` | Bindings, structs, constants, coordinate helpers, terrain sampling, B-spline kernel, `grid_slot()`, `svd3()`, fixed-point helpers | all |
| `mpm_material` | `material_initial_state()`, `material_plasticity()`: `switch` on `settings.constitutive_model` | seed, g2p, refresh_stress |
| `mpm_material_stomakhin`, `mpm_material_drucker_prager`, `mpm_material_ccc` | The three models ([07](07-constitutive-models.md)) | mpm_material |
| `mpm_friction` | `resolve_terrain_collision()`: `switch` on `settings.basal_friction_model` | grid_update, g2p |

## Kernels

| Kernel | Workgroup | Over | Does |
|---|---|---|---|
| `mpm_prepare` | 16×16×1 | grid columns | Once per reset: altitude range into `SimState` (`atomicMin`/`atomicMax`, cm), `column_floor` per column; with entrainment the cover per column ([15](15-entrainment.md)) |
| `mpm_seed` | 256×1×1 | particles | Once per reset: places particles in the release ([below](#seeding)); F = I, C = 0, `plastic_state = material_initial_state()`; pool slots stay inactive |
| `mpm_sort_count` | 256×1×1 | particles | Counts particles per sort tile (4×4 columns); inactive particles in the last bucket |
| `mpm_sort_scan` | 256×1×1 | one workgroup | Exclusive prefix sum into cursors; zeroes the counts |
| `mpm_sort_scatter` | 256×1×1 | particles | Writes particle indices in tile order |
| `mpm_p2g` | 256×1×1 | sorted particles | Particle → grid; flags the tiles (8×8 columns) the stencil reaches; zeroes the per-substep yield count |
| `mpm_grid_update` | 8×8×1 | one workgroup per flagged tile | Momentum → velocity, gravity, terrain collision with basal drag, walls; writes `grid_velocity`; zeroes the accumulators; column peaks; entrainment (`entrain_column()`) |
| `mpm_g2p` | 256×1×1 | particles, buffer order | Grid → particle, return mapping (stores τ), advection, particle-level terrain collision, clamp into the domain and under the band ceiling; diagnostics reduced per workgroup |
| `mpm_column_stats` | 256×1×1 | particles | Sandbox only: particle count and speed sum per column for the peak speed |
| `mpm_refresh_stress` | 256×1×1 | particles | Reruns the return mapping under new stress parameters without a reseed |
| `mpm_splat` | 256×1×1 | particles | 64-bit sums of position and \|v\|² into `SimState`; particles as discs of `splat_radius` (≤ 8 texels) into the density raster |
| `mpm_rasterize` | 16×16×1 | raster texels | Density → RGBA; empty texels transparent |

### P2G

Each workgroup takes 256 consecutive sorted indices. Its home tile is the sort tile of its first
particle; contributions to the home tile's window (6×6 columns × 16 band layers, 576 nodes) are
summed in workgroup memory and added to the grid once per node after a barrier. Other
contributions go to the grid directly. Mass is added with `add_node_mass_units()` (u32 lo/hi
with carry), momentum with `atomicAdd` on i32 ([04](04-data-layout.md#fixed-point-atomics)).

### Grid update

Thread 0 loads the tile's flag word. Tiles with neither `TILE_FLAGGED` nor `TILE_WAS_ACTIVE` return; the
flag is rewritten to `TILE_WAS_ACTIVE` if it was flagged, else 0. Each thread walks one column's
band layers. Nodes without mass get `grid_velocity = 0`. Nodes below the terrain get
`resolve_terrain_collision(…, true, flow_depth)`; outflow is blocked within 2 nodes of the walls.
`grid_velocity[cell] = (velocity, mass)`. After the layer loop the column's `peak_depth` and
`peak_speed` are updated and its speed sums zeroed.

### G2P

Gathers velocity and C from `grid_velocity`, applies `material_plasticity()`, advects, resolves
particle-level terrain contact with `resolve_terrain_collision(…, false, 0)` and clamps into
the domain box and below the band ceiling. A particle with negative mass (entrained in this
substep) gets positive mass and stays at rest. Per workgroup: max speed, yield count,
horizontal path, wall and ceiling contacts, then one global atomic each.

### Seeding

| Mode | `release_mode` | Sampling |
|---|---|---|
| Disc | 0 | Uniform in the release disc, inside the domain with a 2·dx margin; requires a release-mask hit unless `seed_anywhere`; up to 32 attempts |
| Release grid | 1 (sandbox, `ReleaseArea` on the map) | Uniform over the release bounds, kept with probability depth / `release_max_depth`; up to 256 attempts |

Failed particles stay inactive (`mass = 0`). Height: terrain + `rand · slab_thickness` (disc) or
`rand · depth` (release grid). First-sample hits are counted in `SimState.seed_first_hits`;
`seeded_particle_volume()` derives the real volume per particle from them (disc) or from
`release_volume` (release grid). Random numbers: `///use random` (PCG hash).

## Engine shaders

In `webgpu/engine/shaders/`, read-only on the solver's buffers ([12](12-rendering.md)):

| Shader | Stage |
|---|---|
| `avalanche_surface_splat` | compute 256×1×1, particles → render grid |
| `avalanche_surface_field` | compute 16×16×1, render grid → depth, height, speed, peak depth, cover |
| `render_avalanche_surface` | render, G-buffer |
| `render_avalanche` | render, G-buffer |
| `render_avalanche_powder` | render, after compose |
| `avalanche_surface_common`, `avalanche_surface_terrain` | modules |

All avalanche fragments write `AVALANCHE_MARKER` (`0x00FFFFFF`) into the G-buffer overlay slot.
