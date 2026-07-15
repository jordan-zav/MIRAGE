import json
from pathlib import Path

import geopandas as gpd
import rasterio
from rasterio.enums import ColorInterp

from line_core import lineament_extraction_multiband


def validate_rgb_geotiff(path):
    with rasterio.open(path) as src:
        count = int(src.count)
        if count == 1:
            return
        if count == 3:
            return
        if count == 4:
            interps = tuple(src.colorinterp or ())
            if len(interps) >= 4 and interps[3] == ColorInterp.alpha:
                return
            raise ValueError(
                f"MIRAGE accepts single-band, RGB GeoTIFF (3 bands), or RGBA where band 4 is alpha. "
                f"Detected 4 bands without alpha in: {path}"
            )
        raise ValueError(
            f"MIRAGE accepts single-band, RGB GeoTIFF (3 bands), or RGBA where band 4 is alpha. "
            f"Detected {count} band(s) in: {path}"
        )


def _summarize_lineaments(shapefile_path):
    gdf = gpd.read_file(shapefile_path)
    if gdf.empty:
        return {
            "count": 0,
            "total_length": 0.0,
            "mean_length": 0.0,
            "max_length": 0.0,
            "min_length": 0.0,
            "units": "N/A",
        }

    try:
        metric_crs = gdf.estimate_utm_crs()
    except Exception:
        metric_crs = None

    if metric_crs:
        lengths = gdf.to_crs(metric_crs).geometry.length.astype(float)
        units = "meters (UTM)"
    else:
        lengths = gdf.geometry.length.astype(float)
        units = str(gdf.crs.axis_info[0].unit_name) if gdf.crs and hasattr(gdf.crs, 'axis_info') and gdf.crs.axis_info else "CRS map units"

    return {
        "count": int(len(gdf)),
        "total_length": float(lengths.sum()),
        "mean_length": float(lengths.mean()),
        "max_length": float(lengths.max()),
        "min_length": float(lengths.min()),
        "units": units,
    }


def _write_markdown_report(report_path, summary):
    md_content = f"""# Reporte de Ejecución - MIRAGE

## Información General
*   **Ráster de Entrada:** `{summary["input_raster"]}`
*   **Carpeta de Salida:** `{summary["output_dir"]}`
*   **Archivo Shapefile:** `{summary["outputs"]["lineaments"]}`
*   **Archivo GeoPackage:** `{summary["outputs"]["geopackage"]}`

## Parámetros Utilizados
*   **Modo Interpretativo:** `{summary["parameters"]["extraction_mode"]}`
*   **Radio de Suavizado (RADI):** `{summary["parameters"]["radi"]}`
*   **Umbral de Borde Canny (GTHR):** `{summary["parameters"]["gthr"]}`
*   **Longitud Mínima en Píxeles (LTHR):** `{summary["parameters"]["lthr"]}`
*   **Tolerancia de Simplificación (FTHR):** `{summary["parameters"]["fthr"]}`
*   **Diferencia Angular Máxima (ATHR):** `{summary["parameters"]["athr"]}°`
*   **Distancia de Enlace Máxima (DTHR):** `{summary["parameters"]["dthr"]} px`
"""
    if summary["parameters"]["extraction_mode"] == "geophysics":
        md_content += f"""*   **Filtros Geofísicos:** `{summary["parameters"].get("geophys_filters", "")}`
*   **Tipo de Estructura:** `{summary["parameters"].get("geophys_extract_type", "")}`
*   **Paso de Curvatura (Stride):** `{summary["parameters"].get("geophys_stride", 1)}`
"""

    md_content += f"""
## Resumen de Lineamientos
*   **Cantidad Detectada:** `{summary["lineaments"]["count"]}`
*   **Unidades de Medida:** `{summary["lineaments"]["units"]}`
*   **Longitud Total:** `{summary["lineaments"]["total_length"]:.2f}`
*   **Longitud Promedio:** `{summary["lineaments"]["mean_length"]:.2f}`
*   **Longitud Máxima:** `{summary["lineaments"]["max_length"]:.2f}`
*   **Longitud Mínima:** `{summary["lineaments"]["min_length"]:.2f}`
"""
    report_path.write_text(md_content, encoding="utf-8")


def run_extraction_job(
    *,
    geotiff,
    out_dir,
    radi,
    gthr,
    lthr,
    fthr,
    athr,
    dthr,
    extraction_mode="signature",
    geophys_filters=None,
    geophys_extract_type="trough",
    geophys_stride=1,
):
    validate_rgb_geotiff(geotiff)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    out_base = out_dir / "lineaments"
    shapefile_path = lineament_extraction_multiband(
        geotiff=geotiff,
        out_base=str(out_base),
        radi=radi,
        gthr=gthr,
        lthr=lthr,
        fthr=fthr,
        athr=athr,
        dthr=dthr,
        extraction_mode=extraction_mode,
        geophys_filters=geophys_filters,
        geophys_extract_type=geophys_extract_type,
        geophys_stride=geophys_stride,
    )

    summary = {
        "input_raster": str(Path(geotiff)),
        "output_dir": str(out_dir),
        "outputs": {
            "lineaments": shapefile_path,
            "geopackage": str(out_base.with_suffix(".gpkg")),
        },
        "parameters": {
            "radi": int(radi),
            "gthr": int(gthr),
            "lthr": int(lthr),
            "fthr": float(fthr),
            "athr": float(athr),
            "dthr": float(dthr),
            "extraction_mode": extraction_mode,
            "geophys_filters": geophys_filters,
            "geophys_extract_type": geophys_extract_type,
            "geophys_stride": geophys_stride,
        },
        "lineaments": _summarize_lineaments(shapefile_path),
    }

    report_path = out_dir / "mirage_report.json"
    summary["outputs"]["report"] = str(report_path)
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    report_md_path = out_dir / "mirage_report.md"
    summary["outputs"]["report_markdown"] = str(report_md_path)
    _write_markdown_report(report_md_path, summary)

    return summary
