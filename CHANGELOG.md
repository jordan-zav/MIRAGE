# Changelog

## Unreleased

- A GeoPackage write rejected before it starts (invalid CRS, missing io extra) no longer leaves a reservation that blocks the corrected retry; a write that fails midway is recorded as failed instead of writing.
- The Markdown run report of the calibrated geophysics profile lists the method, threshold and continuation heights actually applied, and states that the numeric legacy controls were not used.
- ONNX manifests accept an uppercase SHA-256, as printed by PowerShell Get-FileHash.
- The CLI needs Rasterio only for --auto; a missing raster backend names the io extra. The QGIS build manifest takes its version from metadata.txt.
- The lazy-import test runs from a source checkout without an installed distribution.
- Wheels built from a source distribution, as python -m build does, now record their source commit: the sdist carries it, and the release inspection rejects a wheel without one. Wheels of 1.3.0 report no commit.
- The mirage console command ends expected failures with a single error line and exit status 1 instead of a traceback; mirage.cli.main still raises for in-process callers.
- Host GDAL 3.11 or later uses the MEM vector driver instead of the deprecated Memory driver.
- Tests: an end-to-end run of the neural route against a small generated ONNX model (onnx joins the dev extra), agreement of every declared version number, and the console error path. CI also runs on Linux and Python 3.13.

- The public-region evaluation reports a chance level and a rigid-placement null. At 500 m, concordance with the 1:1M mapped faults does not exceed chance in Mount Isa or Broken Hill for worming or route B; Pilbara shows a nominal excess that does not survive Holm correction. The validation record states this and that the calibrated threshold, relative to the scene maximum, returns few lines on large regional grids.

## 1.3.0 — 2026-11-15

- Installable mirage-geo distribution, lazy mirage API, CLI and optional io, wavelets, nn and gui extras; historical source import adapters retained.
- Geophysics only: route A adds THDR, multilevel worming, continuous wavelets and tensor anisotropy. Route B supports explicit, hash-verified external ONNX models on CPU; no weights or automatic downloads.
- Calibrated geophysics defaults to worming at 0.50, selected on validation only. Explicit legacy-v120 preserves the historical file pipeline; legacy-array preserves THDR at 0.20. Existing source-bound recipes retain their execution contract.
- Wavelet boundary reflection, datum removal and concave ridge checks correct edge artifacts. Regression tests are separate from scientific effectiveness.
- Expanded bank: 3,000 synthetic scenes and three Australian public-map regions. B fails joint superiority criteria; greater cartographic coverage accompanies greater unmatched density and worse synthetic localization.
- Geological and archaeological modes preserve v1.2.0 behavior and were not reevaluated. No route identifies geological origin.
- Portable QGIS dependency placement, explicit training input paths, bilingual documentation, research index, citation metadata and tag-only OIDC publication workflow prepared.

## 1.2.0

- Declared input kind and physical-scale recipes on projected metre grids.
- Three sensitivities on the same native QGIS preview window, human recipe selection and source identity validation.
- Native resolution retained separately from recommendation samples; GDAL/OSR host CRS handling and successive-task/unload checks.
- Historical origin heuristics disabled; circular morphology does not establish archaeology.

## 1.1.0

- Primary QGIS dock and Processing provider with one shared numerical core; standalone Tk interface retained.
- Native GDAL/OGR I/O, raster/NoData/alpha controls, protected output directories and execution provenance.
- English and Spanish documentation and reproducible allowlisted plugin ZIP.

## 1.0.0

- Initial standalone raster signature extraction, Tk GUI and command-line workflow.
- Historical geological, archaeological and geophysical presets, line linking, curvature/chord controls and vector exports.
- Standalone Windows build and GPL licensing documentation.

History basis: initial implementation 771e8c1; QGIS 02a3add; physical recipes 032bb05 (v1.2.0 main 06b5d86); packaging f7124ae; expanded protocol 9574866; wavelet correction e3dda4d; calibrated defaults 2b4468a; public concordance 126ba1b. Research findings are summarized in [validation](docs/VALIDATION_1_3_0.md).
