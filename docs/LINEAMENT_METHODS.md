# Lineament routes: methods, provenance and limits

## Abstract

Version 1.3.0 packages the existing MIRAGE numerical implementation and adds array-first geomatic and experimental neural routes. A small physical synthetic benchmark compares curve position and direction; it is not geological classification or external field validation. Neither route identifies the geological origin of a feature.

## Mathematical methods and source origin

| Function or family | Definition and origin | Source incorporated |
| --- | --- | --- |
| Existing line_core and adaptive modules | MIRAGE v1.2.0 numerical implementation | Author's GPL-3.0-or-later source, preserved |
| engine.upward | Fourier harmonic continuation multiplier exp(-height times radial angular wavenumber); reflected padding | New implementation; no SGTool source |
| engine._ridges | Hessian normal and interpolated nonmaximum suppression of horizontal gradient amplitude | New implementation; no bsdwormer source |
| engine.anisotropy | Smoothed gradient structure tensor; eigenvalue contrast divided by trace; tangent orientation | New implementation of the tensor definition |
| Wavelet branch | PyWavelets separable continuous Gaussian derivative coefficients at physical scales | Calls optional PyWavelets API; no wavelet implementation copied |
| engine.curves | Existing MIRAGE extract_centerline and link_segments | Author's existing curve functions, identical for both routes |
| neural.infer and outputs | SHA-256 check, ONNX Runtime CPU execution, shared curves and GeoPackage writer | New host-independent orchestration; no neural network implementation bundled |
| Research-only TEED training | TEED network at pinned commit 40fa4b1391dc6424f88989d0ca75d5b592c8681d | Downloaded to a separate research source directory on explicit invocation; never included in runtime |

Potential-field continuation and derivative methods follow the standard Fourier formulation in Richard J. Blakely, Potential Theory in Gravity and Magnetic Applications, Cambridge University Press (1995), https://doi.org/10.1017/CBO9780511549816 . Multiscale derivative-wavelet edges relate to Stéphane Mallat and Sifen Zhong, Characterization of Signals from Multiscale Edges (1992), https://doi.org/10.1109/34.142909 . These are mathematical references, not claims of equivalent software or copied implementations.

SGTool by Mark Jessell declares MIT at its root. Its included BSDWorms notice separately identifies Franklin G. Horowitz, 2013–2021, under BSD-2-Clause terms. The root MIT label alone does not describe every included function. The MIRAGE methods above incorporate neither implementation. Reference: https://github.com/swaxi/SGTool/tree/805ac7d39c99690143367f62affc0e3c5a7a97cd .

## Neural license review

TEED by Xavier Soria and collaborators has an MIT code license. Its selected checkpoint checkpoints/BIPED/7/7_model.pth is a tracked file in that same pinned repository; the repository-wide MIT notice is the recorded weight-license basis, with no separate exception found at that path. This basis is recorded separately from the code license in each external model manifest. It is not a claim that an independent weight-specific grant was provided. The author should review this basis before distributing any derived model. No weights are shipped in source, wheels, TerraWorkbench or the deliverable copy.

PiDiNet is rejected as a permissive candidate because its license begins with a research-only/commercial-contact restriction. DexiNed declares MIT for code but its external weight terms were not separately established in this evaluation; it is not used. The inference API refuses manifests lacking separate permissive code and weight license identifiers. Research sources and checkpoint downloads are checked against pinned Git blob identities and then hashed with SHA-256. A repository hash identifies bytes; it does not itself establish a license.

## Historical exploratory benchmark protocol (96 scenes)

scripts/benchmark_lineaments.py creates 96 independent 64 by 64 prism scenes, with 48 training, 24 validation and 24 held-out test cases. Each complete physical scene belongs to exactly one partition; rotations, depths, noise and RTP variants are not reused across partitions. Harmonica analytically models each rectangular prism. Eight stacked prisms approximate inclined contacts, faults and dikes; this discretization is not an analytic dipping-sheet solution. Coordinates rotate before evaluating prism fields and magnetization directions rotate consistently. Some magnetic fields undergo an actual Harmonica RTP filter after noise is added. Source depths are 50 or 125 metres; dip from vertical is 0 or 30 degrees. Cells are 25 metres. The benchmark is deliberately small and uses induced magnetization with one field direction; remanence, realistic survey errors and complex intersecting bodies are absent.

Threshold candidates 0.1, 0.2, 0.35 and 0.5 are selected by mean validation F1. Geomatic methods keep their explicit physical heights/scales. Neural optimization uses training scenes only, chooses the epoch by validation weighted BCE, and runs at most 12 epochs or 180 seconds with two CPU threads, seed 20261115 and patience three. Pretrained and adjusted models export to ONNX with numerical agreement checked against the development network. All benchmark inference uses ONNX Runtime CPU, including model/session creation time in reported per-scene inference times. PyTorch is development-only.

Position scoring densifies returned curves to half-cell spacing, rasterizes them and computes precision and recall within two cells of projected known top traces. Mean position error averages truth-to-prediction distances; an empty prediction receives the grid diagonal. Azimuth error is axial, modulo 180 degrees, evaluated for matched curves. Continuity reports the longest matched curve's unique-cell count divided by the total truth-mask size, capped at one; it is a descriptive metric and treats a dike's two traces together. This is not a geological connectivity measure. Metrics are averaged per scene. Crossings and closed curves need more sophisticated local tangent metrics in a larger benchmark.

## Historical exploratory results and interpretation

The session evidence contains the sealed scene manifest with SHA-256, per-scene metrics, validation thresholds, training curves, model URLs/digests and the comparison table. The legacy numerical engine is unchanged. The later expanded campaign deliberately changed the geophysics default to calibrated worming; legacy-v120 remains explicit. The geological and archaeological modes retain v1.2.0 behavior and were not reevaluated. A higher F1 alone cannot demonstrate overall superiority when position error, continuity or time worsen. The neural route remains experimental. External open-grid illustrations have no known structural ground truth and therefore provide qualitative evidence only.

## Publication review

Before publishing v1.3.0, the author must review the namespace/distribution name, public API, optional dependency bounds and platform support; the new methods and their finite-grid assumptions; the small synthetic benchmark and its limited external validity; and the repository-wide MIT basis for TEED checkpoint use. Local commits do not authorize push, tags, releases or model redistribution. TerraWorkbench's prepared v1.3.0 pin must remain inactive until that immutable release is approved and exists.

## Expanded campaign and 1.3.0 scope

The new routes, calibration and banks apply only to geophysics. The expanded 3,000-scene bank and three Australian map-concordance regions supersede the small exploratory bank for default selection. They are separate campaigns and are not pooled. See [validation](VALIDATION_1_3_0.md), [research records](research/README.md) and [profiles](SCIENTIFIC_PROFILES.md). B failed the joint criteria in both expanded banks and remains experimental.
