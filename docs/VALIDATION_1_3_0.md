# Validation record — 1.3.0

## Scope and evidence identity

The new routes, banks and calibration apply only to geophysics. Geological and archaeological modes retain v1.2.0 behavior and were not reevaluated. The 1.3.0 release does not imply field accuracy or geological origin identification.

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

## Chance level and structural null (later review)

The concordance review adds a chance reference. At 500 m, 5.63% of the observed area of Pilbara, 28.66% of Mount Isa and 31.75% of Broken Hill lies near a mapped fault. These fractions are estimated at 100 m cell centres; they are not geological accuracy. The matched fraction is the share of detected length near mapped faults, distinct from the mapped-length coverage of the historical table.

A null of 1,000 realizations per detection set (seed 20261116) applies one shared rotation and translation to all lines, requires at least 60% of the length to remain in valid cells and scores the retained part. At 500 m:

| Region | Sealed method | Matched % | Null mean % | Excess pp | Reference interval 95% pp | One-sided p, unadjusted |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| Pilbara | Worming 0.50 | 98.20 | 4.62 | +93.59 | [+17.71, +98.20] | 0.0110 |
| Pilbara | B 20261115, 0.65 | 23.60 | 6.22 | +17.38 | [-4.86, +23.60] | 0.0490 |
| Mount Isa | Worming 0.50 | 11.55 | 28.59 | -17.04 | [-56.90, +11.55] | 0.6983 |
| Mount Isa | B 20261115, 0.65 | 38.82 | 30.35 | +8.46 | [-10.13, +25.06] | 0.1958 |
| Broken Hill | Worming 0.50 | 39.47 | 32.34 | +7.14 | [-15.29, +27.67] | 0.2617 |
| Broken Hill | B 20261115, 0.65 | 36.20 | 32.64 | +3.55 | [-10.92, +18.03] | 0.3087 |

Excess is the observed matched fraction minus the null mean. The interval subtracts the null 97.5th and 2.5th percentiles from the observed value; it is a reference against the null, not a confidence interval for field accuracy. The p value counts ties and adds one: (1 + number of null realizations at least as high as observed) / 1001. Mount Isa and Broken Hill show no significant excess at 500 m. Pilbara shows a nominal excess, but sealed worming detects only 2.75 km and covers 1.58% of the reference. After Holm correction of the six sealed-method comparisons at 500 m, none rejects the null at 5% (smallest adjusted p 0.0659). Geological superiority is not demonstrated. Map scale, clipping and the placement mechanism limit interpretation. The [review report](research/null-concordance/INFORME.md) (Spanish) gives the 0.20 diagnostic, the 250/1,000 m tolerances, the methods and the input identities.

The calibrated worming threshold of 0.50 is relative to the scene maximum. It was chosen on synthetic 128 by 128 scenes; on these large regional grids it returns very few lines: 0.00149, 0.02779 and 0.03955 km/km² in Pilbara, Mount Isa and Broken Hill. One dominant anomaly can suppress lower-amplitude structures. The 0.20 threshold was evaluated as a diagnostic only and does not replace the sealed value; adjusting the threshold or the area of interest requires independent evaluation.

## Software checks for this release preparation

Local results on Windows: 86 pytest tests passed, with one opt-in scene-bank audit skipped in the normal suite. That audit was then run separately against the already generated 3,000-scene bank: 1 passed, checking partitions and every scene hash without generating or scoring scenes. Ruff passed, including setup.py and the new archive inspector. The wheel and sdist built successfully, strict Twine checks passed for both, and archive inspection found no weights, datasets, caches, machine paths, build directories or egg-info. The sdist retains root PKG-INFO and successfully rebuilds a wheel.

Fresh isolated Python 3.11 and 3.12 installations of the wheel with io/wavelets/nn passed pip check, lazy import/version/location checks, the array API with GeoPackage output, installed CLI and module CLI, and analytic software-fixture extraction to GeoPackage with both geophysics and legacy-v120. These fixtures are software checks, not another scientific evaluation. QGIS 3.44.12 on its own Python 3.12 passed the packaged ZIP smoke offscreen with an isolated profile: manifest hashes, Processing, native GDAL, dock loading, physical previews, recipe selection/invalidation, masking/CRS rejection and unload during an active task. No desktop, mouse or keyboard was controlled.

Build provenance preserves the existing hook. A standard wheel built from the sdist outside Git may have a null source commit; its numerical source hashes remain available through mirage.provenance(). The QGIS ZIP records a clean source commit and a per-file SHA-256 manifest. Final artifact hashes and full execution logs belong to the release-preparation deliverable, rather than being embedded recursively into this document.

The release-preparation deliverable supplies pytest XML/logs, Ruff, wheel/sdist build, strict Twine checks, artifact inventories with SHA-256, clean Python 3.11/3.12 API/CLI/pip-check runs and a QGIS 3.44.12 offscreen ZIP smoke. See its Spanish INFORME.md for executed outcomes and limitations. The CI matrix installs .[dev,wavelets,nn,io]; a bank-integrity audit is opt-in and does not generate or score scenes. Publication to PyPI uses the tag-only OIDC workflow; the checks above are the local pre-release checks.

Historical baseline: 74 tests in the initial packaging review; 76 tests in the expanded campaign, including the preexisting-bank hash audit. Those are historical counts, not a claim that this preparation reran those campaigns. API import laziness, metric transforms, calibrated/legacy profiles, wavelet regression, QGIS ZIP byte parity and portable dependency placement are covered by software checks.

Limits: Windows/Python 3.11–3.12 and QGIS 3.44.12 offscreen only; no interactive desktop acceptance, regional scalability certification or external geological validation. Tk GUI is secondary. Model parity evidence is historical; no research model is shipped or reevaluated for this release. No new assessment of geological or archaeological modes was made.
