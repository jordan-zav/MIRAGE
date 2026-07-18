## MIRAGE

**M**orphological **I**dentification and **R**emote **A**nalysis for **G**eospatial **E**xtraction

MIRAGE is a Python framework for automated extraction of geospatial signatures in geoscience and archaeology.

Instead of tracing generic lines, MIRAGE rescues interpretable signatures according to the operator's goal: Geological signature or Archaeological signature.

Input requirement: MIRAGE accepts single-band GeoTIFF files, RGB GeoTIFF files (3 bands), and RGBA GeoTIFF where band 4 is alpha (alpha is ignored).

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
pip install -r requirements.txt
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

## License

This project is licensed under the GNU General Public License v3.0. See [LICENSE.txt](LICENSE.txt).
