# Raw grid view

`MpmSolverNode::raw_view()` returns an `MpmRawView` (`webgpu/compute/nodes/MpmSolverNode.h`):
the solver's grid velocity and its layout, for visualisations and exports.

## Fields

| Field | Content |
|---|---|
| `particles` | The `MpmParticleView`: particle buffers, `domain_origin`, `dx`, `columns`, `world_from_metres`, terrain texture, `reset_count` |
| `grid_velocity` | One `vec4f` per node: `xyz` velocity [m/s], `w` node mass in normalised particle-mass units; 0 without flow; `nullptr` before the first run |
| `column_floor` | Per column, the first stored layer in cells above the origin (`i32`) |
| `grid_resolution` | Columns in x and y, layers per column |
| `kg_per_mass_unit`, `snow_density` | Mass of one node-mass unit [kg] (0 until the first diagnostics readback), density [kg/m³] |
| `interpolation` | Real-time blend factor of the particles (the grid has no previous state) |
| `simulated_time` | Seconds since the last reset |
| `generation` | Changes whenever `grid_velocity` changes (per chunk) |
| `resource_generation` | Changes when the solver reallocates buffers: rebuild bind groups |
| `layout_version` | `MPM_LAYOUT_VERSION` ([04](04-data-layout.md#layout-version)) |

Velocities are in the solver's metre frame, z up; the linear part of
`particles->world_from_metres` maps directions to the map.

## Layout

Layer-major, terrain-following ([04](04-data-layout.md#the-terrain-following-grid)). Node of
column `c = y · columns.x + x` in layer `l`:

```
grid_velocity[l · columns.x · columns.y + c]
position = (domain_origin + (x, y) · dx, (column_floor[c] + l) · dx)
```

Flow depth of a column: Σ_l `w` · `kg_per_mass_unit` / (`snow_density` · dx²).

## Guarantees

- `w` holds the node mass.
- Tiles the flow has left are processed once more and zeroed (`TILE_WAS_ACTIVE` flag).
- A reset clears `grid_velocity`.
- The buffer reflects the last substep of the last submitted chunk.

## Reading

- Bind the buffer read-only in a separate bind group; the solver's bind group already uses all
  eight storage buffers. No copy or extra synchronisation is needed (one queue per device).
- Nodes at the edge of the flow can have very small mass and large velocity; weight by `w`.
- For smooth playback keep a copy per chunk (16 B per node).
