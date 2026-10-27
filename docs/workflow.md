> MIRAGE 1.2.0: la interfaz principal es QGIS. Consulta el [README](../README.es.md) y la [validación vigente](VALIDATION_1_2_0.md). El texto inferior conserva el contexto técnico anterior y no acredita nuevas pruebas de campo.

# Workflow

1. Load the input GeoTIFF.
2. Read a single grayscale band directly or average RGB/RGBA color bands into a single grayscale image.
3. Normalize pixel values to a stable 0-1 range.
4. Detect whether the raster is already binary-like linework or a tonal image.
5. For binary-like rasters, skeletonize the mask directly.
6. For tonal rasters, smooth with <code>RADI</code>, then run Canny using <code>GTHR</code>.
7. Prune short skeleton fragments.
8. Extract the longest ordered path from each connected skeleton component.
9. Drop paths shorter than <code>LTHR</code>.
10. Link nearby segments using <code>ATHR</code> and <code>DTHR</code>.
11. Simplify output polylines using <code>FTHR</code>.
12. Export the result as a shapefile and GeoPackage.
