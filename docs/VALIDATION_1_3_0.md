# Validation record — 1.3.0

## Scope and evidence identity

The new routes, banks and calibration apply only to geophysics. Geological and archaeological modes retain v1.2.0 behavior and were not reevaluated. The prepared local 1.3.0 release does not imply publication, field accuracy or geological origin identification.

Scientific source is commit 126ba1bfaf0941789c7088a9727ca55ecae4dec2. Expanded campaign results were already computed on 15 November 2026; release preparation only reads their records and hashes. It does not train, run scientific benchmarks again or change results. The earlier 96-scene exploratory study is separate and is not pooled into the 3,000-scene bank.

[Expected hashes](research/expected_hashes.json) identify the bank manifest, frozen validation parameters, test summaries, paired comparisons, real-region metrics and external models. The calibration retains bank digest beea91f002d146256491b3a0a280c66bb82fdcae5d8f630aed5495b93a4a0096. Archived reports are identified as TW-MIRAGE-lineamientos-20261115_104530 and MIRAGE-bancos-mejora-20261115_123459; local storage paths are intentionally absent from this public document.

## Expanded synthetic bank (historical evidence)

Harmonica generated 3,000 independent 128 × 128 scenes, partitioned 1,800/600/600 by complete scene. Gravity, TMI, RTP and five body families include noise, corrugation and gaps. Reference: projected upper body traces. Primary tolerance: two cells, with one/four-cell sensitivity. Thresholds and seed selection use validation only. Bootstrap: 10,000 paired, field-stratified scene replicates, seed 88419. Empty predictions receive the scene diagonal as position penalty.

| Test method | Precision | Recall | F1 | Position error (cells) | Axial error (degrees) |
| --- | ---: | ---: | ---: | ---: | ---: |
| A THDR | 0.373 | 0.583 | 0.398 | 14.812 | 34.19 |
| A worming | 0.509 | 0.719 | 0.564 | 1.898 | 26.57 |
| A wavelets | 0.473 | 0.785 | 0.550 | 1.578 | 36.40 |
| B 20261115 | 0.824 | 0.662 | 0.715 | 8.569 | 18.83 |
| B 20261116 | 0.824 | 0.665 | 0.717 | 8.835 | 18.85 |
| B 20261117 | 0.824 | 0.666 | 0.718 | 7.737 | 19.16 |

Worming at threshold 0.50 was selected on validation (F1 0.553846). The B seed selected on validation BCE is 20261115, tested at 0.65. Its paired F1 gain versus worming is 0.150, CI95 [0.130, 0.171], but position worsens by 6.67 cells, CI95 [4.54, 9.05], beyond the 0.50-cell margin. All seeds fail the position criterion; selected B has 16 empty scored scenes versus zero for worming. B is experimental and does not meet the combined superiority rule.

Wavelet reflection, datum removal and concave ridge checks have a controlled localization/datum-invariance regression. The new 1.578-cell mean is on a different bank from the old approximately 32-cell exploratory result; do not treat their difference as a paired correction effect.

## Public Australian regions (historical evidence)

Pilbara, Mount Isa and Broken Hill share Geoscience Australia national RTP compilation and 1:1,000,000 mapped faults/shear zones under CC BY 4.0. They are geographically separate but not independent of source/processing/map scale. Grids were explicitly projected at 100 m. Coverage measures nearby mapped length; unmatched density measures detections distant from mapping. Neither is geological truth. Bootstrap uses paired spatial 5 km blocks, 10,000 replicates, seed 88420.

| Region, tolerance 500 m | Worming coverage | Selected B coverage | Worming unmatched km/km² | Selected B unmatched km/km² |
| --- | ---: | ---: | ---: | ---: |
| Pilbara | 1.58% | 7.52% | 0.0000 | 0.0084 |
| Mount Isa | 1.78% | 10.48% | 0.0246 | 0.0317 |
| Broken Hill | 3.03% | 8.33% | 0.0239 | 0.0409 |

Paired mapped coverage gain CI95: [4.79, 9.32] percentage points. Unmatched density increase CI95: [0.0037, 0.0173] km/km², exceeding the 0.0016 margin. Angular deterioration upper bound: 3.24 degrees. B fails the combined real-concordance criterion. Greater coverage accompanies more unmatched detections, not demonstrated geological superiority. No route determines origin. Full 250/500/1000 m evidence hashes are in expected_hashes.json.

## Software checks for this release preparation

Local results on Windows: 86 pytest tests passed, with one opt-in scene-bank audit skipped in the normal suite. That audit was then run separately against the already generated 3,000-scene bank: 1 passed, checking partitions and every scene hash without generating or scoring scenes. Ruff passed, including setup.py and the new archive inspector. The wheel and sdist built successfully, strict Twine checks passed for both, and archive inspection found no weights, datasets, caches, machine paths, build directories or egg-info. The sdist retains root PKG-INFO and successfully rebuilds a wheel.

Fresh isolated Python 3.11 and 3.12 installations of the wheel with io/wavelets/nn passed pip check, lazy import/version/location checks, the array API with GeoPackage output, installed CLI and module CLI, and analytic software-fixture extraction to GeoPackage with both geophysics and legacy-v120. These fixtures are software checks, not another scientific evaluation. QGIS 3.44.12 on its own Python 3.12 passed the packaged ZIP smoke offscreen with an isolated profile: manifest hashes, Processing, native GDAL, dock loading, physical previews, recipe selection/invalidation, masking/CRS rejection and unload during an active task. No desktop, mouse or keyboard was controlled.

Build provenance preserves the existing hook. A standard wheel built from the sdist outside Git may have a null source commit; its numerical source hashes remain available through mirage.provenance(). The QGIS ZIP records a clean source commit and a per-file SHA-256 manifest. Final artifact hashes and full execution logs belong to the release-preparation deliverable, rather than being embedded recursively into this document.

The release-preparation deliverable supplies pytest XML/logs, Ruff, wheel/sdist build, strict Twine checks, artifact inventories with SHA-256, clean Python 3.11/3.12 API/CLI/pip-check runs and a QGIS 3.44.12 offscreen ZIP smoke. See its Spanish INFORME.md for executed outcomes and limitations. The CI matrix installs .[dev,wavelets,nn,io]; a bank-integrity audit is opt-in and does not generate or score scenes. The tag-only OIDC workflow is prepared locally; remote CI, PyPI configuration and publication are not executed or claimed.

Historical baseline: 74 tests in the initial packaging review; 76 tests in the expanded campaign, including the preexisting-bank hash audit. Those are historical counts, not a claim that this preparation reran those campaigns. API import laziness, metric transforms, calibrated/legacy profiles, wavelet regression, QGIS ZIP byte parity and portable dependency placement are covered by software checks.

Limits: Windows/Python 3.11–3.12 and QGIS 3.44.12 offscreen only; no interactive desktop acceptance, regional scalability certification or external geological validation. Tk GUI is secondary. Model parity evidence is historical; no research model is shipped or reevaluated for this release. No new assessment of geological or archaeological modes was made.
