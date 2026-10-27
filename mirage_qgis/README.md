# MIRAGE for QGIS 1.2.0

**English** · [Español](README.es.md)

Extract connected raster signatures and review them with your GIS reference
layers. This is the experimental QGIS release; extracted morphology is
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


## Adaptive configuration in metres (1.2)

1. Declare the actual input: terrain, magnetic field, gravity, optical imagery or unknown. Texture does not establish origin.
2. Set objective, minimum length, smoothing radius, linking gap and simplification in metres. This workflow requires a projected metre CRS and square orthogonal pixels. Geophysics additionally needs a north-up grid and a gap-free window.
3. Pan the map centre over the area to inspect and click Compare 3 previews. Three sensitivities process the same native 256-by-256 cells. A reduced Recommend sample never changes the resolution used to convert metres to extraction pixels.
4. Compare overlays and parameters, then choose Use balanced, conservative or detail. No winner is inferred from trace count. The displayed directory retains the crop, PNGs, GeoPackages, candidate plan and selected recipe.
5. Choose a fresh folder for full extraction. Its JSON report embeds the recipe. Changing raster/settings invalidates selection. Crop boundaries can affect results; a crop and regional extraction are not guaranteed to match exactly.

Use manual advanced parameters retains the expert pixel-based workflow without a recipe. Recommend prepares candidates only; it does not infer archaeology or override the declared input. Unknown input uses generic edge extraction. Preserve geometry requires explicit user selection.

Processing: mirage:recommend_parameters creates a plan, mirage:preview_candidates compares a window (optional CENTER in source CRS, WINDOW_PIXELS 32 to 512), and mirage:extract_signatures accepts RECIPE pointing to a selected JSON. Shared API functions are recommend_adaptive, select_recipe and validate_recipe; the CLI accepts --recipe path.json. Recipes bind to source path, size and modification time, and do not transfer automatically to another file. Extraction reports also calculate the input SHA-256.

The physical minimum length is checked again on final geometry after simplification and mask clipping. Resolution may prevent representing lengths below two pixels. Variants change smoothing and threshold while retaining minimum length, linking gap, simplification and objective. PNGs show the original raster; TDR traces derive from the transformed field. Circular morphology and higher trace counts do not establish origin or accuracy.

## Source, limits and licence

The package contains byte-identical copies of the shared source core and a
SHA-256 build manifest. The Python API, CLI and standalone interface remain
available in the [source repository](https://github.com/jordan-zav/MIRAGE).
Software and synthetic tests do not establish field validity. Review sensor,
scale, CRS, roads, drainage and independent evidence before interpretation.

[GNU GPL v3](https://github.com/jordan-zav/MIRAGE/blob/main/LICENSE.txt); the full
LICENSE.txt is included in the ZIP. Jordan Zavaleta — [GisGeo Dev](https://gisgeo.dev).

RADI is rounded to native pixels. Tonal edges retain a minimum sigma of 1.2 pixels and geophysics 0.5; requesting zero smoothing does not disable this numerical filter. The JSON records the parameter conversion.
