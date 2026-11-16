# MIRAGE 1.3.0

[Español](README.es.md) · [API](docs/API.md) · [Validation](docs/VALIDATION_1_3_0.md)

MIRAGE extracts raster lineaments for human review. QGIS is the primary interface; the mirage-geo distribution exposes the mirage Python package and mirage CLI. GPL-3.0-or-later, Jordan Zavaleta.

**Scope of 1.3.0:** the new routes, benchmarks and calibration apply only to geophysical mode (magnetic and gravity grids). Geological and archaeological modes retain v1.2.0 behavior and were not reevaluated. Neither route identifies the geological origin of a feature, and texture or circular geometry does not establish archaeology.

## Installation

For QGIS, download MIRAGE_QGIS_1.3.0.zip from [release v1.3.0](https://github.com/jordan-zav/MIRAGE/releases/tag/v1.3.0), then Plugins → Manage and Install Plugins → Install from ZIP. Open the MIRAGE panel. Its explicit dependency installer uses the QGIS settings directory; MIRAGE_QGIS_DEPENDENCIES can override that directory. It retains the host GIS libraries. Tested with QGIS 3.44.12 on Windows, offscreen.

For Python 3.11 or 3.12, create an isolated environment with Git available:

~~~shell
python -m venv .venv
# Activate .venv using your shell, then:
pip install "mirage-geo @ git+https://github.com/jordan-zav/MIRAGE@v1.3.0"
pip install "mirage-geo[io,wavelets,nn] @ git+https://github.com/jordan-zav/MIRAGE@v1.3.0"
mirage --help
~~~

The second command adds standalone raster/vector I/O, PyWavelets and ONNX Runtime CPU. The gui extra adds standalone Tk interface dependencies; dev adds testing/build tools. No extra contains model weights or PyTorch. In a source checkout use pip install -e ".[dev,wavelets,nn,io]" for development.

## Geophysical routes and profiles

| Route/profile | Behavior |
| --- | --- |
| A: geomatic | THDR, multilevel worming, wavelets and tensor anisotropy; no neural weights |
| geophysics (default) | Calibrated worming, threshold 0.50; heights 0/2/4 and scales 1/2/4 times cell size |
| legacy-v120 | Historical v1.2.0 file pipeline through API, CLI and QGIS |
| legacy-array | Previous array defaults, THDR at 0.20; separate from v1.2 file parity |
| B: neural/onnx | Experimental external model inference; explicit manifest and SHA-256 required |

Calling mirage.profiles() exposes engine calibration. Explicit method and threshold overrides remain available. Old source-bound recipes retain legacy-v120 unless explicitly overridden. [Scientific profiles](docs/SCIENTIFIC_PROFILES.md) explains compatibility.

~~~python
import numpy as np
import mirage

image = np.tile(np.tanh((np.arange(64) - 31) / 3), (64, 1))
result = mirage.extract(image, pixel_size=25)
result.write("new_lineaments.gpkg", "EPSG:32750")
print(mirage.profiles(), mirage.provenance())
~~~

Geophysical grids must be finite, north-up, square and projected in metres. The array caller supplies a truthful metric transform; file/QGIS adapters enforce CRS requirements. Physical scales and continuation heights are not inferred geological depths. Processing is global in memory; regional or out-of-core scalability is not certified. Crop large rasters deliberately. Outputs include line geometry, route/method, length, azimuth, strength and applicable scale/height; worming retains amplitude per vertex. Strength is not geological confidence.

~~~shell
mirage -i input.tif -o new_output --feature-mode "Geophysics Potential Fields" --input-kind magnetic --geophysics-profile geophysics
mirage -i input.tif -o legacy_output --feature-mode "Geophysics Potential Fields" --input-kind magnetic --geophysics-profile legacy-v120
~~~

QGIS retains declared-input physical recommendations, three previews of the same native window, human selection and source-bound recipes. See [workflow](docs/workflow.md) and [parameters](docs/parameters.md).

## Evidence and limits

The expanded synthetic bank contains 3,000 independent 128 × 128 Harmonica scenes: 1,800 training, 600 validation, 600 test. Test reference geometry is the upper projected body trace, with a primary tolerance of two cells. Calibration and model selection used validation only.

| Test method | Precision | Recall | F1 | Position error (cells) |
| --- | ---: | ---: | ---: | ---: |
| A worming | 0.509 | 0.719 | 0.564 | 1.898 |
| A wavelets | 0.473 | 0.785 | 0.550 | 1.578 |
| B TEED, seed selected by validation | 0.824 | 0.662 | 0.715 | 8.569 |

B improves F1 here but worsens localization; empty predictions receive the preregistered diagonal penalty (16 B scenes versus zero worming scenes). It fails the joint superiority criterion. This table does not imply higher synthetic recall for B.

Pilbara, Mount Isa and Broken Hill compare predictions against Geoscience Australia RTP magnetics and 1:1,000,000 mapped faults/shear zones (CC BY 4.0). These regions share compilation, processing and map scale: they are not independent validation sources. At 500 m, B increases mapped-fault coverage (paired CI95 +4.79 to +9.32 percentage points) but also unmatched detection density (CI95 +0.0037 to +0.0173 km/km²), exceeding the allowed margin. B provides more cartographic coverage but worse synthetic position and fails the joint real concordance criterion. Cartographic agreement is not geological truth or origin identification. See [verifiable results](docs/VALIDATION_1_3_0.md) and [research](docs/research/README.md).

## Route B with your own model

Install the nn extra. Obtain or train your own licensed ONNX model and place a JSON manifest beside it. MIRAGE never downloads weights during import or extraction. The model must accept float32 NCHW, three repeated normalized grayscale channels scaled by input_scale with channel mean subtraction, and return one spatial probability map (or logits when declared). Reflection padding satisfies multiple; the output is cropped to the input shape. Validate this preprocessing and a threshold for your own survey.

~~~json
{
  "path": "my-model.onnx",
  "sha256": "REPLACE_WITH_THE_64_CHARACTER_SHA256_OF_YOUR_MODEL",
  "code_license": "MIT",
  "weights_license": "MIT",
  "multiple": 8,
  "input_scale": 255.0,
  "mean": [103.939, 116.779, 123.68],
  "logits": false
}
~~~

The license fields must record actual permissions, not the example labels: accepted code licenses are MIT, Apache-2.0 or BSD-3-Clause; weights also accept CC0-1.0. Compute the SHA-256 of the exact binary and replace the placeholder. A relative model path resolves beside the manifest.

~~~python
result = mirage.extract(image, route="neural", method="onnx",
                        model="my-model.json", pixel_size=25, threshold=0.5)
result.write("new_neural_lineaments.gpkg", "EPSG:32750")
~~~

This interface is the array API; the historical file CLI and own QGIS panel do not expose ONNX selection. No weights are distributed. TEED code is MIT, but a separately scoped permission for its original checkpoint is not confirmed. The previous research recorded repository-wide MIT as its basis; that is not an independently confirmed checkpoint grant. Review rights before redistributing any original or derived model. [Reproduction and hashes](docs/research/REPRODUCING_MODELS.md).

## Citation and development

Cite: Zavaleta, Jordan. MIRAGE: reproducible raster lineament extraction, version 1.3.0. https://github.com/jordan-zav/MIRAGE. [CITATION.cff](CITATION.cff) and [.zenodo.json](.zenodo.json) provide metadata. No DOI has been assigned here; add the actual Zenodo DOI after release.

~~~shell
python -m pytest
python -m ruff check src tests mirage_qgis scripts setup.py
python -m build
python scripts/package_qgis.py --output MIRAGE_QGIS_1.3.0.zip
~~~

[Changelog](CHANGELOG.md) · [Draft release notes](docs/research/release_notes_1.3.0.md) · [Author publishing guide (Spanish)](docs/PUBLICAR_PYPI.es.md) · [GPL-3.0-or-later](LICENSE.txt).
