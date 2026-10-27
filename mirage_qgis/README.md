# MIRAGE for QGIS 1.1.0

**English** · [Español](README.es.md)

Extract connected raster signatures and review them with your GIS reference
layers. This is the first experimental QGIS release; extracted morphology is
not an automatic geological or archaeological classification.

## Install

1. Extract nothing from the downloaded ZIP. In QGIS, open Plugins → Manage and
   Install Plugins → Install from ZIP and select the complete archive.
2. Enable MIRAGE, then open Raster → MIRAGE.
3. If image libraries are missing, use the panel's install button. Installation
   needs internet and uses an isolated directory; QGIS' GIS libraries are retained.
4. Restart QGIS if the library installation requests it.

Requires QGIS 3.40–3.x and Python 3.10 or newer. Tested in QGIS 3.44.12 on Windows
with Python 3.12. Host GDAL, NumPy, SciPy, Shapely and pyproj are used directly.
The image stack uses scikit-image 0.25–0.26 and its missing dependencies.
The first download may take several minutes. Normal extraction is local.

## Use

Load a GDAL-supported file raster. Select it in the panel, choose your goal and
profile, optionally request heuristic starting parameters, review Advanced
parameters and select a new or empty output folder. Extract runs in a QGIS task
and loads the resulting GeoPackage. Cancel takes effect between numerical stages.

Processing provides mirage:extract_signatures and mirage:recommend_parameters,
also available for batch jobs and models. Reuse a different output folder per job.

Single-band, RGB and RGBA input is supported. NoData and transparent pixels are
excluded. Geophysical filters require a complete north-up square grid, projected
in metres. Fill gaps or reproject explicitly before that mode; no silent repair
changes the source. Simplification tolerance uses source CRS units.

The default limit is 16 million pixels, with serial core execution inside QGIS.
Increasing the limit requires sufficient memory; there is no out-of-core tiling.
Runs preserve SHP, GeoPackage, JSON/Markdown reports and a completion manifest.
An existing result folder is never overwritten.

## Source, limits and licence

The package contains byte-identical copies of the shared source core and a
SHA-256 build manifest. The Python API, CLI and standalone interface remain
available in the [source repository](https://github.com/jordan-zav/MIRAGE).
Software and synthetic tests do not establish field validity. Review sensor,
scale, CRS, roads, drainage and independent evidence before interpretation.

[GNU GPL v3](https://github.com/jordan-zav/MIRAGE/blob/main/LICENSE.txt); the full
LICENSE.txt is included in the ZIP. Jordan Zavaleta — [GisGeo Dev](https://gisgeo.dev).
