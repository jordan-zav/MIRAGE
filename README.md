# MIRAGE

<p align="center">
  <a href="https://github.com/jordan-zav/MIRAGE/releases/latest"><img alt="Release" src="https://img.shields.io/github/v/release/jordan-zav/MIRAGE?style=flat-square"></a>
  <a href="https://github.com/jordan-zav/MIRAGE/actions/workflows/tests.yml"><img alt="Tests" src="https://img.shields.io/github/actions/workflow/status/jordan-zav/MIRAGE/tests.yml?branch=main&label=tests&style=flat-square"></a>
  <img alt="Python 3.11" src="https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white">
  <a href="LICENSE.txt"><img alt="GNU GPLv3" src="https://img.shields.io/badge/License-GPLv3-blue?style=flat-square"></a>
</p>

**M**orphological **I**dentification and **R**emote **A**nalysis for **G**eospatial **E**xtraction

MIRAGE is a Python framework for automated extraction of geospatial signatures in geoscience and archaeology.

Instead of tracing generic lines, MIRAGE rescues interpretable signatures according to the operator's goal: Geological signature or Archaeological signature.

Input requirement: MIRAGE accepts single-band GeoTIFF files, RGB GeoTIFF files (3 bands), and RGBA GeoTIFF where band 4 is alpha (alpha is ignored).

## Download

Windows users can download the packaged application from the [latest GitHub release](https://github.com/jordan-zav/MIRAGE/releases/latest). The source workflow below remains available for development and reproducible execution.

## Features

- Multiscale edge detection
- Curve extraction and linking
- Support for grayscale and RGB GeoTIFFs
- Shapefile and GeoPackage output with line attributes
- GUI and command-line execution
- Per-run JSON report with output paths and summary metrics
- Interpretation modes for Geological signature and Archaeological signature

## Installation

```bash
git clone https://github.com/jordan-zav/MIRAGE.git
cd MIRAGE
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run the GUI

```bash
python src/gui.py
```

## Run the CLI

```bash
python src/cli.py -i input.tif -o output_folder --profile "Structural continuity"
```

The CLI writes `lineaments.shp`, `lineaments.gpkg`, and a `mirage_report.json` file in the output folder.

## Documentation

- [Processing workflow](docs/workflow.md)
- [Parameter reference](docs/parameters.md)
- [Technical report](docs/informe_mirage_paper.md)

## Development

Install the development requirements and execute the test suite:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

| Path | Contents |
| --- | --- |
| `src` | GUI, CLI, processing pipeline and extraction algorithms |
| `src/ai` | Automatic parameter recommendation |
| `tests` | Synthetic raster and geophysics tests |
| `docs` | Workflow, parameters and technical documentation |

## License

This project is licensed under the GNU General Public License v3.0. See [LICENSE.txt](LICENSE.txt).
