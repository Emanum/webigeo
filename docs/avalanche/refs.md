# References

The papers the implementation uses, with the parts used. The shader headers cite the same
entries by section and equation.

| Short name | Reference | Used for |
|---|---|---|
| Hu 2018 | Y. Hu, Y. Fang, Z. Ge, Z. Qu, Y. Zhu, A. Pradhana, C. Jiang. *A moving least squares material point method with displacement discontinuity and two-way rigid body coupling.* ACM TOG 37(4), Art. 146, 2018. | MLS-MPM transfers (§3.4 Eq. 15–18, §4): `mpm_p2g`, `mpm_g2p` |
| Jiang 2015 | C. Jiang, C. Schroeder, A. Selle, J. Teran, A. Stomakhin. *The affine particle-in-cell method.* ACM TOG 34(4), Art. 51, 2015. [doi:10.1145/2766996](https://doi.org/10.1145/2766996) | APIC affine matrix C, quadratic B-spline kernel: `mpm_common`, `mpm_p2g`, `mpm_g2p` |
| Stomakhin 2013 | A. Stomakhin, C. Schroeder, L. Chai, J. Teran, A. Selle. *A material point method for snow simulation.* ACM TOG 32(4), Art. 102, 2013. | Fixed-corotated elasticity, singular-value clamp, hardening (§5 Eq. 1–2, §7), Table 2 defaults, collisions (§8): `mpm_material_stomakhin`, `mpm_friction` |
| Klár 2016 | G. Klár, T. Gast, A. Pradhana, C. Fu, C. Schroeder, C. Jiang, J. Teran. *Drucker-Prager elastoplasticity for sand animation.* ACM TOG 35(4), Art. 103, 2016. | Hencky elasticity (§6.3), return mapping (§7.1 Eq. 27–28); §7.3 hardening not used: `mpm_material_drucker_prager` |
| Gaume 2018 | J. Gaume, T. Gast, J. Teran, A. van Herwijnen, C. Jiang. *Dynamic anticrack propagation in snow.* Nat. Commun. 9, 3047, 2018. | Cohesive Cam Clay yield surface and hardening (Eq. 1–4): `mpm_material_ccc` |
| Wolper 2019 | J. Wolper, Y. Fang, M. Li, J. Lu, M. Gao, C. Jiang. *CD-MPM: Continuum damage material point methods for dynamic fracture animation.* ACM TOG 38(4), Art. 119, 2019. | Non-associated return mapping "NACC" (§6.2 Eq. 14) and its hardening (§6.2.3): `mpm_material_ccc` |
| Li 2021 | X. Li, B. Sovilla, C. Jiang, J. Gaume. *Three-dimensional and real-scale modeling of flow regimes in dense snow avalanches.* Landslides 18, 3393–3406, 2021. [doi:10.1007/s10346-021-01692-8](https://doi.org/10.1007/s10346-021-01692-8) | Material presets and basal μ (Table 1), plastic ratio |
| Voellmy 1955 | A. Voellmy. *Über die Zerstörungskraft von Lawinen.* Schweizerische Bauzeitung 73, 1955. | Voellmy basal friction (as in the AvaFrame documentation): `mpm_friction` |
| Tonnel 2023 | M. Tonnel, A. Wirbel, F. Oesterle, J.-T. Fischer. *AvaFrame com1DFA (v1.3): a thickness-integrated computational avalanche module – theory, numerics, and testing.* Geosci. Model Dev. 16, 7013–7035, 2023. [doi:10.5194/gmd-16-7013-2023](https://doi.org/10.5194/gmd-16-7013-2023) | Energy-line test (§5.2, App. A), stop criterion, peak fields, entrainment (plowing, erosion) |
| Fischer 2013 | J.-T. Fischer. *A novel approach to evaluate and compare computational snow avalanche simulation.* NHESS 13, 1655–1667, 2013. [doi:10.5194/nhess-13-1655-2013](https://doi.org/10.5194/nhess-13-1655-2013) | AIMEC, the evaluation used with the AvaFrame sandbox export |
| Komon 2025 | P. Komon, G. Kimmersdorfer, A. Celarek, M. Waldner. *Data-Driven Compute Overlays for Interactive Geographic Simulation and Visualization.* IEEE VIS 2025, 186–190. [doi:10.1109/VIS60296.2025.00043](https://doi.org/10.1109/VIS60296.2025.00043) | The compute node graph the solver is a node of |
| AvaFrame | Open-source avalanche modelling framework, release 2.1. <https://github.com/OpenNHM/AvaFrame>, <https://docs.avaframe.org> | Test avalanches, release and entrainment areas, com1DFA reference results |

Implementation reference: `mls-mpm88`, Hu's reference MLS-MPM code, for the P2G/G2P factor
placement.
