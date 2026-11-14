# Material and friction models

The constitutive model (inside the snow) and the basal friction model (snow against terrain)
are selected independently, at runtime, through two uniform enums:

```cpp
enum ConstitutiveModel  : uint32_t { STOMAKHIN_2013 = 0, DRUCKER_PRAGER = 1, COHESIVE_CAM_CLAY = 2 };
enum BasalFrictionModel : uint32_t { COULOMB = 0, VOELLMY = 1 };
```

`MpmSolverSettings::constitutive_model` / `basal_friction_model`, serialised as ints. The WGSL
dispatchers (`mpm_material.wgsl`, `mpm_friction.wgsl`) `switch` on the same values. Switching
needs no pipeline rebuild; a model change reseeds.

## Constitutive models

| Model | File | Elasticity | Plasticity | `plastic_state` | Reference |
|---|---|---|---|---|---|
| Stomakhin | `mpm_material_stomakhin.wgsl` | Fixed corotated | Singular-value clamp, exponential hardening | J_P (starts at 1) | Stomakhin 2013 §5 Eq. 1–2, §7, Table 2 |
| Drucker–Prager | `mpm_material_drucker_prager.wgsl` | Hencky | Cohesionless friction cone, closed-form return (Cases I–III); fixed friction angle | accumulated plastic strain (starts at 0) | Klár 2016 §6.3, §7.1 Eq. 27–28 |
| Cohesive Cam Clay | `mpm_material_ccc.wgsl` | Hencky | Cam Clay ellipse with sinh hardening; non-associated return with shear hardening | plastic volumetric strain α (starts so that p₀ = `ccc_p0_initial`) | Gaume 2018 Eq. 1–4; Wolper 2019 §6.2 Eq. 14, §6.2.3 |

Interface of a model (see [05-tuning.md](05-tuning.md#adding-a-constitutive-model)):

```
<name>_initial_state() -> f32
<name>_plasticity(F_trial, state) -> PlasticReturn   // F, state, kirchhoff (τ = P·Fᵀ), yielded
```

`material_initial_state()` is called by `mpm_seed`, `material_plasticity()` by `mpm_g2p` and
`mpm_refresh_stress`.

### Parameters

| Setting | Models | Default |
|---|---|---|
| `youngs_modulus`, `poissons_ratio` | all | 1.4·10⁵ Pa, 0.2 |
| `snow_density` | all | 400 kg/m³ |
| `hardening`, `critical_compression`, `critical_stretch` | Stomakhin | 10, 2.5·10⁻², 7.5·10⁻³ |
| `dp_friction_angle` | Drucker–Prager | 30° |
| `ccc_m`, `ccc_beta`, `ccc_xi`, `ccc_p0_initial` | Cam Clay | 0.7, 0.2, 0.002, 3000 Pa |

## Basal friction

`resolve_terrain_collision(v, n, apply_basal_drag, flow_depth)` in `mpm_friction.wgsl`.

| Model | Terms | Reference |
|---|---|---|
| Coulomb | Contact impulse with friction `terrain_friction` (μ) | Stomakhin 2013 §8 |
| Voellmy | Coulomb plus turbulent drag with `voellmy_xi` (ξ) and the local flow depth of the column | Voellmy 1955 |

| Call site | `apply_basal_drag` | `flow_depth` |
|---|---|---|
| `mpm_grid_update`, nodes below the terrain | `true` | column mass × `seeded_particle_volume()` / dx², floored at 0.1 m |
| `mpm_g2p`, particles below the terrain after advection | `false` | 0 |

Defaults: μ = 0.47, ξ = 4000 m/s².

## Material presets

`AvalanchePanel` "Material preset" writes model, E, ν, ρ, μ and the model parameters into the
solver settings, reseeds and lowers `dt` under `max_stable_dt()`. Editing a parameter shows
"(custom)".

| Preset | Model | E | ν | ρ [kg/m³] | μ | Model parameters |
|---|---|---|---|---|---|---|
| Stomakhin 2013 (film snow) | Stomakhin | 1.4·10⁵ Pa | 0.2 | 400 | 0.47 | ξ 10, θc 2.5·10⁻², θs 7.5·10⁻³ |
| Cold dense (Li 2021 I) | Cam Clay | 3 MPa | 0.3 | 250 | 0.47 | M 0.5, β 0, ξ 1, p₀ 3 kPa |
| Warm shear (Li 2021 II) | Cam Clay | 3 MPa | 0.3 | 250 | 0.47 | M 1.5, β 0.3, ξ 1, p₀ 30 kPa |
| Sliding slab (Li 2021 III) | Cam Clay | 3 MPa | 0.3 | 250 | 0.47 | M 1.5, β 0.5, ξ 1, p₀ 42 kPa |
| Warm plug (Li 2021 IV) | Cam Clay | 3 MPa | 0.3 | 250 | 0.47 | M 0.5, β 1.0, ξ 0.1, p₀ 12 kPa |
| Vallée de la Sionne 2003 (Li 2021 V) | Cam Clay | 3 MPa | 0.3 | 200 | 0.49 | M 0.7, β 0.2, ξ 0.002, p₀ 3 kPa |
| Cold dense, cohesionless | Drucker–Prager | 3 MPa | 0.3 | 250 | 0.47 | φ 13.3° |

The Li 2021 presets take the parameters of Li 2021 Table 1.

## Not implemented

- Friction-angle hardening of Drucker–Prager (Klár 2016 §7.3).
- The associative Cam Clay return (Gaume 2018).
- CK-MPM transfers.
