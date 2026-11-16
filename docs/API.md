# MIRAGE 1.3.0 API

The distribution is mirage-lineaments; the import namespace is mirage. Python 3.11 and 3.12 are targets. The package import loads no raster, GUI, QGIS, neural runtime or weights. No route identifies the geological origin of a feature.

## Stable functions

mirage.routes() returns the route/method registry without optional imports. mirage.extract(image, route='geomatic', method=None, pixel_size=1, transform=None, threshold=None, minimum_cells=4, gap_cells=3, angle=20, heights=None, scales=None, model=None, cancelled=None, profile='geophysics') returns a Result. mirage.preview has the same contract and processes exactly the array/window supplied by the caller; the caller must preserve its transform. Neither function silently resamples a grid.

Input is a finite north-up square grid. Pixel size, heights, scales, coordinates and lengths are in metres. Rows increase southward. The transform is (pixel_size,0,xmin,0,-pixel_size,ymax), mapping pixel corners; returned curves pass through cell centres. Azimuth is clockwise from north modulo 180 degrees. Angles of degenerate/closed endpoint chords require interpretation; coherence near zero carries no reliable orientation.

Result.lines and Result.attributes have identical ordering. Every attribute row contains route, method, length, azimuth, strength, scale and height. Inapplicable scale/height values are null. strength is a normalized response, except neural probabilities; it is not calibrated geological confidence. Result.strength retains input dimensions. Anisotropy additionally returns Result.azimuth; worming retains x,y,continuation-height,unscaled-gradient-amplitude for every curve vertex in Result.points. Continuation height is not a depth estimate.

result.write(destination, crs, raster=None, transform=None) creates a new GeoPackage with lineaments, optionally worms points, and optionally a GeoTIFF response. Existing destinations are refused. GDAL from QGIS is preferred; install the io extra for standalone raster/vector I/O. Anisotropy GeoTIFF bands are azimuth/coherence in GDAL. A numerical array API does not infer whether the supplied CRS is actually metric; host adapters must enforce that contract.

mirage.recommend(image,pixel_size_m,input_kind='unknown',goal='continuity',minimum_length_m=280,smoothing_m=30,linking_gap_m=120,simplification_m=4) returns the established physical-scale recommendation plan, including three candidates. Recommendations assist human selection and do not classify geological origin.

## Methods and optional components

geomatic/legacy uses the original TDR/ridge skeleton, with the same curve functions used by the new routes. For exact v1.2 file-pipeline compatibility use mirage.pipeline.run_extraction_job with its original keyword arguments; the new array legacy method is not a replacement for every historical file-pipeline configuration.

For the array legacy method, normalized threshold maps to the historical GTHR parameter by multiplying by 100; its internal curvature threshold therefore follows the unchanged v1.2 definition. The legacy file API retains its original six explicit parameters. No threshold is applied to the cellwise anisotropy output.

geomatic/thdr extracts horizontal gradient ridges. geomatic/worming repeats these at specified upward continuation heights and retains amplitude per vertex. FFT continuation uses reflection padding and is not an infinite-domain solution. geomatic/wavelets uses separable undecimated Gaussian first-derivative continuous wavelets from the wavelets extra. Scales are physical sampling scales, not inferred depths or a reconstruction claim. geomatic/anisotropy returns structure-tensor tangent azimuth and coherence per cell.

neural/onnx is experimental. Install nn and explicitly select a model manifest. It requires an external ONNX path, SHA-256, code_license, weights_license, multiple, input_scale, mean and logits. SHA-256 is checked before ONNX Runtime CPU inference. No training framework is imported by runtime. mirage.neural.download_model is an explicit opt-in HTTPS downloader requiring an expected digest; no extraction or import downloads anything. Weights are excluded from wheels and plugin ZIPs. No regional tiling or out-of-core processing is claimed.

## Compatibility and development

mirage.provenance() returns the engine-owned installed version, source commit, dirty-source marker, direct-install metadata and numerical source hashes. Hosts use this public function rather than importing private MIRAGE modules or assuming a source layout. A build outside Git may have a null commit; hashes still identify the numerical files. A dirty build must be reviewed by source hash as well as commit.

The old source modules are compatibility imports into mirage. The standalone launcher continues using src/gui.py; the installed CLI is mirage or python -m mirage. The project's own QGIS plugin bundles byte-identical numerical modules under its established core namespace and excludes GUI/CLI modules. TerraWorkbench uses an installed distribution and never bundles this source.

The new routes, calibration and banks apply only to geophysics. Geological and archaeological file modes retain v1.2.0 behavior and were not reevaluated. See [profiles](SCIENTIFIC_PROFILES.md) for defaults and historical recipes.
