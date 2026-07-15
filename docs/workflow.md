# Workflow

1. Load the input GeoTIFF.
2. Read a single grayscale band directly or average RGB/RGBA color bands into a single grayscale image.
3. Normalize pixel values to a stable 0-1 range.
4. Detect whether the raster is already binary-like linework or a tonal image.
5. For binary-like rasters, skeletonize the mask directly.
6. For tonal rasters, smooth with `RADI`, then run Canny using `GTHR`.
7. Prune short skeleton fragments.
8. Extract the longest ordered path from each connected skeleton component.
9. Drop paths shorter than `LTHR`.
10. Link nearby segments using `ATHR` and `DTHR`.
11. Simplify output polylines using `FTHR`.
12. Export the result as a shapefile and GeoPackage.
