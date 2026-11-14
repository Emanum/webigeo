# Methods and references

What each part of the solver implements and where it comes from. Full entries in
[refs.md](refs.md). Material and friction models in detail: [07-constitutive-models.md](07-constitutive-models.md).

## Substep

| Stage | Kernel | Method | Reference |
|---|---|---|---|
| Particle → grid | `mpm_p2g` | MLS-MPM transfer with APIC affine momentum; quadratic B-spline, 3×3×3 stencil | Hu 2018 §3.4 Eq. 15–18, §4; Jiang 2015 |
| Grid update | `mpm_grid_update` | Momentum → velocity, gravity, terrain collision with basal friction, domain walls | Hu 2018 §4; Stomakhin 2013 §8 |
| Grid → particle | `mpm_g2p` | APIC velocity and affine matrix, elastic predictor, return mapping, advection, particle-level terrain collision | Hu 2018 §4; Jiang 2015 |
| Constitutive model | `mpm_material*` | Stomakhin, Drucker–Prager or Cohesive Cam Clay | see [07](07-constitutive-models.md) |
| Basal friction | `mpm_friction` | Coulomb or Voellmy | Stomakhin 2013 §8; Voellmy 1955 |
| Entrainment | `mpm_grid_update` | com1DFA plowing and erosion | Tonnel 2023; [15](15-entrainment.md) |

Each particle carries position, velocity, APIC matrix C, elastic deformation gradient F, one
scalar plastic state and its Kirchhoff stress τ = P·Fᵀ. The grid holds no state between
substeps.

## Numerics

| Item | Implementation |
|---|---|
| Time integration | Explicit; `dt` is kept under `MpmSolverNode::max_stable_dt()` (CFL bound on the P-wave speed) before every run |
| SVD | `svd3()` in `mpm_common.wgsl`: Jacobi eigendecomposition of FᵀF (8 sweeps), signed third singular value; one SVD per particle and substep, in G2P |
| Stress | Computed by the return mapping in G2P, stored on the particle, read by the next P2G |
| Grid accumulation | Fixed-point atomics: 64-bit mass at 2²⁰, i32 momentum at 10⁴, both rounded ([04](04-data-layout.md)) |
| Mass units | Particle mass 1, particle volume 1/ρ ([04](04-data-layout.md)) |
| Terrain | Bilinear height from the R32Float height texture (`sample_height_uv()`); normal from central differences at grid scale |
| Collision | Grid level (nodes below the terrain) and particle level (after advection, projected onto the surface) |
| Vertical grid | Terrain-following band of `grid_layers` per column ([04](04-data-layout.md#the-terrain-following-grid)) |
| Units | Metres on the ground: Web Mercator world units × cos(latitude of the region centre) |

## Guards

Clamps that keep a diverging particle finite:

- Stomakhin: J_P and its hardening factor in [0.05, 20].
- Cam Clay: sinh argument ≤ 20; sinh and asinh as Taylor series below 0.1; M ≥ 10⁻³, ξ ≥ 10⁻⁶.
- Hencky models (Drucker–Prager, Cam Clay): singular values in [10⁻³, 10³] before the logarithm.
- Momentum contributions clamped to ±2·10⁹ before every atomic add.

## Diagnostics

| Diagnostic | Implementation | Reference |
|---|---|---|
| Energy line, `energy_line_friction()` | Energy height over the mass-averaged particle path, fitted past 10 % of the path | Tonnel 2023 §5.2, App. A |
| At rest, `at_rest()` | Mean kinetic energy below `stop_kinetic_fraction` of its peak | com1DFA stop criterion (Tonnel 2023) |
| Plastic ratio | Share of particles whose return mapping yielded in the last substep | Li 2021 |
| Peak depth / speed per column | `ColumnStats`, read by `read_back_peaks()` | com1DFA peak fields (Tonnel 2023 §5) |
