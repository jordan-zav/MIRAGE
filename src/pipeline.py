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
            "crs": "Sin definir / No CRS",
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

    crs_str = "Sin definir / No CRS"
    if gdf.crs:
        try:
            crs_name = gdf.crs.name
            crs_epsg = gdf.crs.to_epsg()
            crs_str = f"{crs_name} (EPSG:{crs_epsg})" if crs_epsg else str(crs_name)
        except Exception:
            crs_str = str(gdf.crs)

    return {
        "count": int(len(gdf)),
        "total_length": float(lengths.sum()),
        "mean_length": float(lengths.mean()),
        "max_length": float(lengths.max()),
        "min_length": float(lengths.min()),
        "units": units,
        "crs": crs_str,
    }


def _write_markdown_report(report_path, summary):
    md_content = f"""# Reporte de Ejecución - MIRAGE

## Información General
*   **Ráster de Entrada:** `{summary["input_raster"]}`
*   **Carpeta de Salida:** `{summary["output_dir"]}`
*   **Archivo Shapefile:** `{summary["outputs"]["lineaments"]}`
*   **Archivo GeoPackage:** `{summary["outputs"]["geopackage"]}`
*   **Sistema de Referencia (CRS) de la fuente:** `{summary["lineaments"].get("crs", "N/A")}`

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

    if "rgb_conversion" in summary["parameters"]:
        md_content += f"""*   **Método de Conversión RGB:** `{summary["parameters"]["rgb_conversion"]}`\n"""

    md_content += f"""
## Resumen de Lineamientos
*   **Cantidad Detectada:** `{summary["lineaments"]["count"]}`
*   **Unidades de Medida:** `{summary["lineaments"]["units"]}`
*   **Longitud Total:** `{summary["lineaments"]["total_length"]:.2f}`
*   **Longitud Promedio:** `{summary["lineaments"]["mean_length"]:.2f}`
*   **Longitud Máxima:** `{summary["lineaments"]["max_length"]:.2f}`
*   **Longitud Mínima:** `{summary["lineaments"]["min_length"]:.2f}`

> [!NOTE]
> **Control de CRS y Datum en Arqueología y Geofísica:**
> La precisión espacial centimétrica/métrica es crítica para correlacionar lineamientos con excavaciones y muros. Asegúrate de que el CRS del ráster de entrada coincida con el CRS maestro del proyecto. Si trabajas en Perú y utilizas cartografía antigua en PSAD56, realiza la transformación al marco moderno (WGS84 / SIRGAS UTM) para evitar desfases de posicionamiento.
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
    rgb_conversion="auto",
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
        rgb_conversion=rgb_conversion,
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
            "rgb_conversion": rgb_conversion,
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
