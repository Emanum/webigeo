# 3D rendering

`AvalancheRenderer` draws the solver's particles on the map. Map graph only
(`mpm_avalanche_simulation.json`, node "Particles 3D"); the sandbox uses its 2D view.

## Layers

| Layer | Content | Default |
|---|---|---|
| Flow surface | Blanket over the flow from a B-spline mass splat on a render grid finer than the solver's | on |
| Track | Layer wherever the peak depth since the reset reached the threshold | on |
| Entrainable snow | Entrainment cover still on the ground | on |
| Snow cover | "Avalanche snow cover" `ScreenSpaceSnowOverlay` around the avalanche | on |
| Particles | Powder, spheres or strain-rate ellipsoids | Powder |

The 2D density overlay is disabled (`Overlay::enabled`) while "3D particles" is on.

## Files

| File | Role |
|---|---|
| `webgpu/compute/nodes/MpmSolverNode.h` | `MpmParticleView` (the "particle view" socket) |
| `apps/webgpu_app/compute/ParticleRenderNode.h/.cpp` | Hands the view to the renderer, serialises `AvalancheRenderer::Settings`, `sync_snow_cover()` |
| `webgpu/engine/avalanche/AvalancheRenderer.h/.cpp` | `Settings`, `Frame`, `prepare()`, `draw()`, `draw_transparent()` |
| `webgpu/engine/Window.cpp` | Calls the three renderer stages |
| `webgpu/engine/shaders/render_avalanche.wgsl` | Sphere and ellipsoid impostors, detail particles |
| `webgpu/engine/shaders/render_avalanche_powder.wgsl` | Powder |
| `webgpu/engine/shaders/avalanche_surface_splat.wgsl` | Surface pass 1: particles → render grid |
| `webgpu/engine/shaders/avalanche_surface_field.wgsl` | Surface pass 2: depth, height, speed, peak depth, cover depth |
| `webgpu/engine/shaders/render_avalanche_surface.wgsl` | Surface pass 3: blanket, track, entrainable snow |
| `webgpu/engine/shaders/avalanche_surface_common.wgsl` | `SurfaceConfig`, `AVALANCHE_MARKER` |
| `webgpu/engine/shaders/avalanche_surface_terrain.wgsl` | Solver terrain texture, Catmull-Rom |
| `webgpu/engine/overlay/ScreenSpaceSnowOverlay.*`, `shaders/overlays/screen_space_snow.wgsl` | Skips avalanche pixels; `patches` setting |

## Frame order (`Window::paint`)

1. Atmosphere.
2. `prepare()`: surface splat and field (compute).
3. G-buffer pass: tiles, then `draw()` (solid particles, flow surface).
4. Clouds.
5. Overlays (including the avalanche snow cover, pre-shading bucket).
6. Compose.
7. `draw_transparent()`: powder.
8. Track lines.

## Solver interface

- `ParticleRenderNode` sets an owner-tagged `Source` callback that reads its input socket every
  frame; `clear_source(owner)` clears only its own source.
- Placement: world xy = `world_from_metres` × (x, y, 1); world z = altitude / cos(latitude);
  camera-relative offset computed in double.
- Interpolation: shaders reading particles draw `mix(previous.xyz, current.xyz, interpolation)`.
  Without previous particles the current buffer is bound in their place with factor 1. Slots
  with mass 0 in the previous buffer are drawn at their current position.
- Layout: see [04-data-layout.md](04-data-layout.md#layout-version).

## Solid particles (`render_avalanche.wgsl`)

- Instanced camera-facing quads with vertex pulling; ray–sphere or ray–ellipsoid intersection,
  `frag_depth` (reverse-Z), packed albedo and normal.
- Radius: "Particle size" × particle spacing, at least 1.5 px.
- Colour: Snow, or Speed (viridis, 0–60 m/s).
- Strain-rate ellipsoids: shape from the symmetric part of the APIC matrix C over "Strain
  window", each axis change limited to 70 %, volume normalised.
- Detail particles (1, 8 or 27): instance i is child i mod K of parent i / K; offsets hashed
  from (parent, child) within 2 parent radii (`CHILD_SPREAD`); radius × K^(−1/3) × jitter
  0.7–1.3; merged into the parent below 1.5–3 px (`CHILD_FADE_PIXELS`).

## Powder (`render_avalanche_powder.wgsl`)

- Blob radius "Powder size" × spacing, peak alpha "Powder opacity".
- 3-octave value noise per blob at a hashed per-particle offset.
- Premultiplied "over" blending, no depth attachment, no sort.
- Alpha scaled by the part of the ray inside the blob in front of the G-buffer depth
  (linearised with `inv_proj_matrix`).
- Ambient + wrapped diffuse sun; atmosphere transmittance and inscatter per vertex.

## Flow surface

1. **Splat** (compute, over particles): particle volume onto a render grid "Surface detail"
   times finer than the solver's, with the solver's quadratic B-spline at the solver's dx;
   fixed-point Σw, Σw·speed, Σw·height above terrain. Particles 1–2 dx above the terrain fade out.
2. **Field** (compute, over render nodes): depth (volume per area); blanket height from the
   weighted mean particle height plus the radius, tapered to the depth between 1× and 4×
   min_depth; persistent peak depth (cleared when `reset_count` changes); cover depth
   `column_stats.cover / dx²`, bilinear between solver columns. min_depth = max(8 particle
   volumes over 3×3 columns, 5 cm).
3. **Draw** (G-buffer): one quad per render cell, rejected in the vertex shader unless a corner
   reaches min_depth or 2 cm of cover; normals by central differences. Order: flow over track
   over cover; the surface uses the higher of flow and cover.

Track: 0.3 m layer where peak ≥ min_depth, `TRACK_ALBEDO`; the blanket rim blends into it
from 1× to 3× min_depth. Entrainable snow: cover ≥ `COVER_MIN_DEPTH` (2 cm), `COVER_ALBEDO`.

## Snow cover

`ParticleRenderNode::sync_snow_cover()`, called by the panel every frame, adds the overlay on
first use and removes it with the node.

- z_index below all other overlays (pre-shading).
- All avalanche fragments write `AVALANCHE_MARKER` (`0x00FFFFFF`) into the G-buffer overlay
  slot; `screen_space_snow.wgsl` skips those pixels.
- Snow line from the solver's terrain range: full cover above 55 % of the relief, 0 at 15 % of
  the relief below the lowest point, ±8 % variation, slopes up to 50°. Refitted when the
  terrain range changes.
- `patches` (1 for this overlay, 0 by default): the falloff is the covered share of ground,
  thresholded against two-octave world-space noise (40 world units).

## Panel controls

| Control | Setting | Default |
|---|---|---|
| 3D particles, colour (Snow / Speed) | `enabled`, `colour_mode` | on, Snow |
| Flow surface | `surface` | on |
| Look at the flow | camera 400 m from the centre of mass | — |
| Track | `track` | on |
| Entrainable snow | `entrainment_cover` | on |
| Snow cover | `snow_cover` | on |
| Surface detail (1–4) | `surface_refine` | 3 |
| Particle shape (Spheres / Strain-rate ellipsoids / Powder) | `shape` | Powder |
| Powder size (1–10), Powder opacity | `powder_size`, `powder_opacity` | 8, 0.3 |
| Particle size, Detail particles | `radius_scale`, `children` | 0.6, 8 |
| Strain window | `strain_window` | 0.15 s |
