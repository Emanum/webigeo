# AvaFrame release areas on the map

The map scenarios Kontertal, Gallreide, Hintertux, Wolfsgruben and Madlein release from
AvaFrame's release areas when the AvaFrame data is downloaded (panel, sandbox download).
Without the data they release a disc of the same area on the release centroid, masked by the
map's 30–45° release slopes; the panel says which.

## Pipeline

```
Select Tiles ── region aabb ──→ AvaFrame Release ── release area ──→ MPM Solver (release grid mode)
                                  ├ load_sandbox_terrain()
                                  ├ resample_release()
                                  └ R32Float depth texture over the region
```

1. **Load** (`load_sandbox_terrain()`, shared with `AvaFrameSandboxNode`): `dataset.json`, DEM,
   release raster as vertical depth (thickness / cos(slope) on AvaFrame's DEM), placement
   `sandbox_to_world`.
2. **Resample** (`resample_release()`): a grid over the map region at the dataset's cell size
   (≤ 4096 texels per side), laid out like the height texture (row 0 north). Each texel centre
   is mapped region metres → world → `inverse(sandbox_to_world)` → dataset grid and takes the
   nearest cell's depth. Also bounds, area, volume, max depth, centroid. The entrainment area
   is resampled the same way (`resample_depth()`, `ReleaseArea::entrainment_*`).
3. **Solve**: with a `ReleaseArea` on "release area" the solver seeds in release grid mode
   ([03](03-shaders.md#seeding)); the depth texture is bound in place of the release mask and
   every particle stands for volume / particles.

`AvaFrameReleaseNode` outputs null without a dataset (generic scenario, data not downloaded);
`status()` gives the reason.

## Coordinate chain

| Step | Implementation |
|---|---|
| AvaFrame grid → lat/lon | DEM corners from EPSG:31287 (MGI / Austria Lambert), Helmert "MGI to WGS 84 (8)"; in `AvaFrameData` (C++) |
| Grid → world (EPSG:3857) | Affine map least-squares fitted to the four corners (`sandbox_to_world`) |
| World → solver metres | World units × cos(latitude of the region centre) |
| Cells → texels | Nearest cell |
| Terrain | Particles lie on the map's terrain; outline and depth are AvaFrame's |

Release cells outside the solver domain are not seeded; the solver warns. Madlein's release
covers its three areas (relMal1to3); avaGar has a release picker (relGar, relGar2, relGar6).
