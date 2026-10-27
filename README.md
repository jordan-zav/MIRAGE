<p align="center"><strong>English</strong> · <a href="README.es.md">Español</a></p>

<div align="center">
  <img src="assets/branding/logo_clean.png" alt="MIRAGE" width="128">

# MIRAGE

**Morphological Identification and Remote Analysis for Geospatial Extraction**

Extract connected geological or archaeological signatures from georeferenced
rasters through an auditable multiscale image-processing workflow.

[![Release](https://img.shields.io/github/v/release/jordan-zav/MIRAGE?color=2563eb)](https://github.com/jordan-zav/MIRAGE/releases/latest)
[![Tests](https://img.shields.io/github/actions/workflow/status/jordan-zav/MIRAGE/tests.yml?branch=main&label=tests)](https://github.com/jordan-zav/MIRAGE/actions/workflows/tests.yml)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-0f766e)](LICENSE.txt)

</div>

> [!IMPORTANT]
> MIRAGE extracts image morphology, not geological truth. A detected curve can
> represent structure, drainage, roads, acquisition artifacts, illumination or
> noise. Interpretation requires the source raster, scale and independent field
> or geospatial evidence.

## Workflow at a glance

~~~text
Single-band / RGB / RGBA GeoTIFF
                │
                ▼
 Band preparation and selected interpretation profile
                │
                ▼
 Multiscale edge response ──► threshold and morphology
                │
                ▼
 Curve linking, filtering and attribute calculation
                │
                ▼
 Shapefile + GeoPackage + JSON run report
~~~

## Capabilities

| Area | Included workflow |
| --- | --- |
| Inputs | Single-band GeoTIFF, RGB GeoTIFF and RGBA GeoTIFF with alpha ignored |
| Detection | Multiscale edge response and morphological cleanup |
| Geometry | Curve extraction, linking, length/orientation attributes and filtering |
| Profiles | Geological and archaeological interpretation modes |
| Execution | Tkinter desktop GUI and command-line interface |
| Outputs | Shapefile, GeoPackage and per-run JSON report |
| Guidance | Automatic parameter recommendations as an operator starting point |

## Interpretation profiles

MIRAGE separates the operator's goal from the generic image-processing stages:

- **Geological signature** prioritizes connected lineaments and structural
  continuity such as faults, contacts, dykes or fracture traces.
- **Archaeological signature** permits more closed, angular or constructed
  morphologies that could correspond to cultural features.

Profiles alter processing parameters; they do not classify the geological or
archaeological origin of a feature automatically.

## Requirements

- Windows, Linux or macOS with Python 3.11 for source execution;
- a georeferenced GeoTIFF with valid transform and CRS;
- sufficient spatial resolution for the target feature; and
- NumPy, SciPy, scikit-image, Rasterio, Fiona, GeoPandas and related GIS wheels.

## Download

Windows users can download the packaged application from the
[latest GitHub release](https://github.com/jordan-zav/MIRAGE/releases/latest).
Source installation remains available for reproducibility and development.

## Install from source

~~~powershell
git clone https://github.com/jordan-zav/MIRAGE.git
cd MIRAGE
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
~~~

## Run the GUI

~~~powershell
python src/gui.py
~~~

Windows users can also run <code>run_mirage.bat</code>.

## Run the CLI

~~~powershell
python src/cli.py -i input.tif -o output_folder --profile "Structural continuity"
~~~

The output directory contains:

| File | Contents |
| --- | --- |
| <code>lineaments.shp</code> | ESRI Shapefile geometry and attributes |
| <code>lineaments.gpkg</code> | Equivalent GeoPackage layer |
| <code>mirage_report.json</code> | Inputs, parameters, output paths and summary metrics |

## Quality-control checklist

1. inspect CRS, pixel size, NoData and raster statistics;
2. confirm that the chosen profile matches the interpretation objective;
3. compare several scales instead of accepting one threshold;
4. overlay extracted curves on the original and auxiliary rasters;
5. identify roads, drainage, raster seams and acquisition-direction artifacts;
6. review length and orientation distributions; and
7. preserve the JSON report with the delivered vector layers.

## Scientific boundaries

- Output density changes with pixel size, contrast, smoothing and thresholds.
- RGB composites mix spectral and display information; bands should be chosen deliberately.
- Edge continuity is not proof of a fault, contact or archaeological structure.
- The same feature can fragment or merge when parameters or resolution change.
- Geological validation requires independent mapping, geophysics, imagery or field data.

## Documentation

- [Processing workflow](docs/workflow.md)
- [Parameter reference](docs/parameters.md)
- [Technical report](docs/informe_mirage_paper.md)

## Development and verification

~~~powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check .
~~~

The automated tests exercise the core extraction pipeline and geophysical
synthetic cases. Visual and geological validation remains a separate step.

## Repository map

| Path | Contents |
| --- | --- |
| <code>src/pipeline.py</code> | End-to-end processing and export workflow |
| <code>src/line_core.py</code> | Edge, morphology and curve-linking algorithms |
| <code>src/config.py</code> | Profiles and processing configuration |
| <code>src/ai</code> | Parameter recommendation logic |
| <code>src/gui.py</code> | Desktop interface |
| <code>src/cli.py</code> | Command-line interface |
| <code>tests</code> | Core and geophysical regression tests |
| <code>docs</code> | Workflow, parameters and technical report |

## Project status

MIRAGE v1.0.0 is the current public release. The implemented workflow is
functional and tested at the software level; its extracted features must still
be validated for each sensor, region, target scale and interpretation purpose.

## License and contact

MIRAGE is distributed under the [GNU General Public License v3.0](LICENSE.txt).

Jordan Zavaleta — GisGeo Dev<br>
[jordanzav@gisgeo.dev](mailto:jordanzav@gisgeo.dev) · [gisgeo.dev](https://gisgeo.dev)
