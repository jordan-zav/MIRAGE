# MIRAGE 1.1.0 — validation scope

This edition makes QGIS the primary interface while retaining the standalone
API, CLI and Tkinter source interface. The plugin is experimental; installation
is from the GitHub release ZIP, not an approved QGIS repository listing.

## Implemented and checked behaviour

- Single numerical core copied byte for byte into the plugin with a build manifest.
- Native GDAL/OGR execution inside QGIS without importing Rasterio or Fiona.
- Two Processing algorithms and a dockable panel with an asynchronous extraction task.
- GeoPackage loading into the project after successful extraction.
- Heuristic recommendation, provider registration, unload and reload.
- NoData/alpha exclusion, CRS checks, geophysical square-grid/metre requirements.
- Input pixel cap, serial QGIS execution, run reservation and protected outputs.
- A completed, empty vector result for a valid run with no accepted signatures.
- Distinct pixel-space and source-map line lengths.
- Analytic spectral derivatives, synthetic stripes and an analytic trough.

## Environments

Recorded checks: 45 source tests passed, Ruff passed and pip check reported no
broken requirements. Real QGIS checks passed for provider lifecycle, both
Processing tools, the dock task, native NoData/alpha exclusion, an analytic
trough and the packaged manifest. The final release archive is checked again
from its committed source before publication.

The source regression suite uses isolated Python 3.11 with the pinned
requirements. The QGIS smoke test uses QGIS 3.44.12-Solothurn on Windows,
Python 3.12.13, GDAL 3.13.1, NumPy 2.4.6, SciPy 1.17.1 and Shapely 2.1.2.
Missing image libraries are isolated from the host; the checked QGIS image
stack includes scikit-image 0.26.0. Source tests also exercise scikit-image 0.22.

The QGIS test installs the archive into a clean, temporary search path, checks
manifest hashes, runs Processing, invokes the dock task, reopens its output,
and verifies that Rasterio/Fiona were not imported. Qt uses its offscreen
platform; no user's desktop or existing project is controlled.

## Interpretation and limits

These are software and synthetic checks. They do not establish field accuracy,
geological identity, archaeological origin, or universal parameter settings.
Recommendation scores are heuristic, not calibrated probabilities.

The geophysical branch normalizes input before morphological extraction; its
output is linework, not calibrated derivative-amplitude grids. The spectral
operators use positive wavenumber magnitude and its square. Their analytic
tests verify that convention; they do not validate an interpretation of a survey.

Only the recorded QGIS/Windows environment has a real application check in
this release. Other QGIS 3.40–3.x environments need additional verification.
Full out-of-core processing, field-scale performance, immediate cancellation
within third-party numerical calls and an updated standalone Windows EXE are
not established by this package. The old v1.0.0 desktop ZIP remains historical.

## Reproduction

Use the source regression suite and tests/qgis_smoke.py described in the root
README. The release asset and SHA256SUMS identify the checked package. Keep the
full plugin directory together when installing; its manifest identifies each
bundled source file. No private project data or results are included.
