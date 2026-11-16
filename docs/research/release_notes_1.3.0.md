# MIRAGE 1.3.0 — draft release notes

Author review required; this file does not publish a release.

MIRAGE becomes installable as mirage-lineaments with the lazy mirage namespace, stable array API, provenance, CLI and separate optional dependencies. QGIS remains the primary interface.

The new routes, banks and calibration apply only to geophysics. Route A provides THDR, multilevel worming, wavelets and anisotropy. The geophysics profile defaults to validation-selected worming at 0.50. Explicit legacy-v120 retains the historical file pipeline; geological and archaeological modes retain v1.2.0 behavior and were not reevaluated. Source-bound old recipes retain their recorded contract.

Route B is experimental and requires an explicitly supplied, hash-verified external ONNX model. No weights are included. TEED's code is MIT, but a separate checkpoint-specific permission remains unconfirmed; review rights before distributing derivatives.

The expanded synthetic bank comprises 3,000 scenes (600 held-out test), and the real bank comprises three Australian regions sharing Geoscience Australia data compilation and mapping scale. B improves synthetic F1 and real mapped coverage but worsens synthetic position and real unmatched density. It fails the joint criteria in both banks. These are not independent geological validations; neither route identifies geological origin.

See [validation](../VALIDATION_1_3_0.md), [changelog](../../CHANGELOG.md) and [citation](../../CITATION.cff). Planned assets: MIRAGE_QGIS_1.3.0.zip, mirage_lineaments-1.3.0-py3-none-any.whl, mirage_lineaments-1.3.0.tar.gz and SHA256SUMS.txt. The author must review/merge, publish v1.3.0, attach verified assets, obtain the actual Zenodo DOI and configure Trusted Publishing before publication. No DOI is invented.
