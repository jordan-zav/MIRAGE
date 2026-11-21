# MIRAGE 1.4.0 — release notes

A maintenance release. Extraction results are unchanged: no method, default, threshold or calibrated parameter differs from 1.3.0, and the scope of 1.3.0 still applies (new routes and calibration concern geophysics only; no route identifies geological origin).

Fixes:
- A GeoPackage write rejected before it starts no longer blocks the corrected retry, and a write that fails midway is recorded as failed.
- The run report of the calibrated geophysics profile lists the method, threshold and continuation heights actually applied.
- ONNX manifests accept an uppercase SHA-256; the CLI needs Rasterio only for --auto and names the io extra when it is missing; the mirage command ends expected failures with one error line and exit status 1.
- Host GDAL 3.11 or later uses the MEM vector driver.

Reproducibility and validation:
- Wheels built from the source distribution record their source commit.
- New tests: an end-to-end ONNX route, agreement of every declared version number and the console error path. CI also runs on Linux and Python 3.13.
- The public-region evaluation now reports a chance level and a rigid-placement null. At 500 m, concordance with the mapped faults does not exceed chance in Mount Isa or Broken Hill; Pilbara shows a nominal excess that does not survive Holm correction. The calibrated worming threshold of 0.50, relative to the scene maximum, returns few lines on large regional grids. See the [validation summary](../VALIDATION_1_3_0.md).

See the [changelog](../../CHANGELOG.md) and [citation](../../CITATION.cff). Assets: MIRAGE_QGIS_1.4.0.zip, mirage_geo-1.4.0-py3-none-any.whl, mirage_geo-1.4.0.tar.gz and SHA256SUMS.txt. Install with pip install mirage-geo.
