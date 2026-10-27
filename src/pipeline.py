import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

if __package__:
    from .line_core import lineament_extraction_multiband
    from .raster_backend import inspect_raster, summarize_vectors
    from .version import __version__
else:
    from line_core import lineament_extraction_multiband
    from raster_backend import inspect_raster, summarize_vectors
    from version import __version__


def validate_rgb_geotiff(path):
    return inspect_raster(path)


def _summarize_lineaments(shapefile_path):
    return summarize_vectors(shapefile_path)


def _sha256(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as handle:
        while block := handle.read(1024*1024):
            result.update(block)
    return result.hexdigest()


def _write_markdown_report(report_path, summary):
    md_content = f"""# Reporte de Ejecución - MIRAGE

## Información General
*   **Ráster de Entrada:** {summary["input_raster"]}
*   **Carpeta de Salida:** {summary["output_dir"]}
*   **Archivo Shapefile:** {summary["outputs"]["lineaments"]}
*   **Archivo GeoPackage:** {summary["outputs"]["geopackage"]}
*   **Sistema de Referencia (CRS) de la fuente:** {summary["lineaments"].get("crs", "N/A")}

## Parámetros Utilizados
*   **Modo Interpretativo:** {summary["parameters"]["extraction_mode"]}
*   **Radio de Suavizado (RADI):** {summary["parameters"]["radi"]}
*   **Umbral de Borde Canny (GTHR):** {summary["parameters"]["gthr"]}
*   **Longitud Mínima en Píxeles (LTHR):** {summary["parameters"]["lthr"]}
*   **Tolerancia de Simplificación (FTHR):** {summary["parameters"]["fthr"]}
*   **Diferencia Angular Máxima (ATHR):** {summary["parameters"]["athr"]}°
*   **Distancia de Enlace Máxima (DTHR):** {summary["parameters"]["dthr"]} px
"""
    if summary["parameters"]["extraction_mode"] == "geophysics":
        md_content += f"""*   **Filtros Geofísicos:** {summary["parameters"].get("geophys_filters", "")}
*   **Tipo de Estructura:** {summary["parameters"].get("geophys_extract_type", "")}
*   **Paso de Curvatura (Stride):** {summary["parameters"].get("geophys_stride", 1)}
"""

    if "rgb_conversion" in summary["parameters"]:
        md_content += f"""*   **Método de Conversión RGB:** {summary["parameters"]["rgb_conversion"]}\n"""

    md_content += f"""
## Resumen de Lineamientos
*   **Cantidad Detectada:** {summary["lineaments"]["count"]}
*   **Unidades de Medida:** {summary["lineaments"]["units"]}
*   **Longitud Total:** {summary["lineaments"]["total_length"]:.2f}
*   **Longitud Promedio:** {summary["lineaments"]["mean_length"]:.2f}
*   **Longitud Máxima:** {summary["lineaments"]["max_length"]:.2f}
*   **Longitud Mínima:** {summary["lineaments"]["min_length"]:.2f}

> [!NOTE]
> **Control de CRS y Datum en Arqueología y Geofísica:**
> La precisión espacial centimétrica/métrica es crítica para correlacionar lineamientos con excavaciones y muros. Asegúrate de que el CRS del ráster de entrada coincida con el CRS maestro del proyecto. Si trabajas en Perú y utilizas cartografía antigua en PSAD56, realiza la transformación al marco moderno (WGS84 / SIRGAS UTM) para evitar desfases de posicionamiento.
"""
    report_path.write_text(md_content, encoding="utf-8")


def run_extraction_job(
    *, geotiff, out_dir, radi, gthr, lthr, fthr, athr, dthr,
    extraction_mode="signature", geophys_filters=None,
    geophys_extract_type="trough", geophys_stride=1, rgb_conversion="auto",
    workers=1, max_pixels=16_000_000, profile=None, compute_mode=None,
    cancelled=None, adaptive_recipe=None,
):
    if adaptive_recipe is not None:
        if __package__:
            from .adaptive import validate_recipe
        else:
            from adaptive import validate_recipe
        candidate = validate_recipe(adaptive_recipe, geotiff)
        actual = dict(RADI=radi, GTHR=gthr, LTHR=lthr, FTHR=fthr, ATHR=athr, DTHR=dthr)
        if candidate["params"] != actual or candidate["mode"] != extraction_mode or (
                extraction_mode == "geophysics" and (geophys_filters != candidate["filter"] or geophys_extract_type != candidate["feature"])):
            raise ValueError("Recipe differs from execution parameters. Preview/select again.")
    metadata = inspect_raster(geotiff, max_pixels=max_pixels)
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise FileExistsError("Choose a new or empty output folder; previous results are never overwritten.")
    reservation = output/'mirage_run.json'
    state = {"status": "running", "version": __version__,
             "started_utc": datetime.now(timezone.utc).isoformat()}
    # Exclusive creation also protects two tasks that observed an empty folder.
    with reservation.open('x', encoding='utf-8') as handle:
        json.dump(state, handle)
    try:
        out_base = output/'lineaments'
        shapefile_path = lineament_extraction_multiband(
            geotiff=geotiff, out_base=str(out_base), radi=radi, gthr=gthr,
            lthr=lthr, fthr=fthr, athr=athr, dthr=dthr,
            extraction_mode=extraction_mode, geophys_filters=geophys_filters,
            geophys_extract_type=geophys_extract_type, geophys_stride=geophys_stride,
            rgb_conversion=rgb_conversion, workers=workers, max_pixels=max_pixels,
            cancelled=cancelled, minimum_length_m=(adaptive_recipe["requested_scale_m"]["minimum_length"] if adaptive_recipe else None),
        )
        report_path = output/'mirage_report.json'
        markdown_path = output/'mirage_report.md'
        summary = {
            "version": __version__, "input_raster": str(Path(geotiff)),
            "input_sha256": _sha256(geotiff), "raster": metadata,
            "adaptive_recipe": adaptive_recipe,
            "output_dir": str(output), "profile": profile, "compute_mode": compute_mode,
            "outputs": {"lineaments": shapefile_path,
                        "geopackage": str(out_base.with_suffix('.gpkg')),
                        "report": str(report_path), "report_markdown": str(markdown_path)},
            "parameters": {"radi": int(radi), "gthr": int(gthr), "lthr": int(lthr),
                           "fthr": float(fthr), "athr": float(athr), "dthr": float(dthr),
                           "extraction_mode": extraction_mode, "geophys_filters": geophys_filters,
                           "geophys_extract_type": geophys_extract_type,
                           "geophys_stride": int(geophys_stride), "rgb_conversion": rgb_conversion,
                           "workers": workers, "max_pixels": max_pixels,
                           "fthr_units": "source CRS map units"},
            "lineaments": _summarize_lineaments(shapefile_path),
        }
        report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
        _write_markdown_report(markdown_path, summary)
        state.update(status='complete', finished_utc=datetime.now(timezone.utc).isoformat(),
                     input_sha256=summary['input_sha256'], outputs=summary['outputs'])
        reservation.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        return summary
    except Exception as error:
        state.update(status='cancelled' if isinstance(error, InterruptedError) else 'failed',
                     finished_utc=datetime.now(timezone.utc).isoformat(), error=str(error))
        reservation.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        raise
