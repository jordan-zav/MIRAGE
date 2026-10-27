# MIRAGE 1.2.0 validation scope

English first; resumen en espanol al final.

63 source tests cover the extraction core, physical distances at different native resolutions, declaration-preserving recommendations on identical rings, explicit geometry goal, invalid scale/grid rejection, source identity, recipe persistence, physical minimum length and CLI reuse. Ruff checks source, plugin, packager and tests. Existing extraction regressions remain included.

The final ZIP is checked in QGIS 3.44.12-Solothurn / Python 3.12 on Windows, with an isolated profile and Qt offscreen. The smoke harness checks three Processing tools, native NoData/alpha masking, an analytic trough, three-window previews, explicit UI selection, full extraction using the selected recipe, invalidation on changed settings, and native versus sampled resolution. It also checks dependency-installer callbacks and unload/reload. The host GDAL/OSR CRS path avoids mixing PyProj CRS contexts across QGIS worker tasks.

A separate local inspection uses private terrain, optical and magnetic rasters. Those datasets, derived images, local paths, counts and results are excluded from the public package and are not public benchmarks. Software tests and visual plausibility do not establish field accuracy, feature origin or optimal parameters.

Candidates retain the requested physical minimum length and gap, and vary smoothing/threshold. They are starting points selected by a human, not an optimizer or calibrated probabilities. Metric recipes require projected metre CRS and square orthogonal cells; FFT extraction also requires complete north-up windows. A native crop can differ from regional extraction at its boundaries. Large rasters still require deliberate cropping or adequate memory; there is no out-of-core tiling. The default full-input limit is 16 million pixels. The historical Tkinter GUI remains secondary and does not expose the new comparative panel.

The plugin remains experimental and distributed as a GitHub ZIP, without claiming approval in the official QGIS Plugin Repository. Only QGIS 3.44.12 on Windows is directly checked here. The archive manifest records source commit, dirty state and per-file SHA-256. Private inputs and credentials are excluded by the package allowlist.

## Resumen en espanol

Se comprueban escala fisica, tipo declarado, comparacion de tres variantes, seleccion humana, receta reproducible y ejecucion completa en QGIS real. Los datos privados y sus resultados permanecen locales. Las pruebas no acreditan precision geologica ni seleccion automatica del mejor parametro. Se conservan limites de memoria y sensibilidad a bordes de recorte; la edicion sigue siendo experimental.
