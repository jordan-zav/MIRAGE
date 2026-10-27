"""Synthetic checks for masking, spatial units and non-destructive execution."""

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from rasterio.enums import ColorInterp
from rasterio.transform import from_origin
from shapely.geometry import box

from line_core import _line_record, _normalize_image, first_vertical_derivative, second_vertical_derivative
from pipeline import run_extraction_job
from raster_backend import inspect_raster


def raster(path, values, *, crs='EPSG:32718', transform=None, nodata=None, alpha=False):
    values = np.asarray(values)
    if values.ndim == 2:
        values = values[None]
    with rasterio.open(path, 'w', driver='GTiff', width=values.shape[2], height=values.shape[1],
                       count=values.shape[0], dtype=values.dtype, crs=crs,
                       transform=transform or from_origin(300000, 8900000, 10, 10), nodata=nodata) as dataset:
        dataset.write(values)
        if alpha:
            dataset.colorinterp = (ColorInterp.red, ColorInterp.green, ColorInterp.blue, ColorInterp.alpha)
    return path


def stripe():
    result = np.zeros((96, 96), dtype='float32')
    result[46:50, 10:86] = 255
    return result


def run(path, output, **overrides):
    args = dict(geotiff=str(path), out_dir=str(output), radi=2, gthr=60, lthr=8,
                fthr=0, athr=20, dthr=10)
    args.update(overrides)
    return run_extraction_job(**args)


def test_valid_values_control_normalization_not_nodata_sentinel():
    image = np.array([[2., 4.], [np.nan, 6.]])
    result = _normalize_image(image)
    assert result[0, 0] == 0
    assert result[1, 1] == pytest.approx(1, abs=1e-6)
    assert result[0, 1] == result[1, 0]


def test_entirely_invalid_data_is_rejected():
    with pytest.raises(ValueError, match='no valid'):
        _normalize_image(np.full((8, 8), np.nan))


@pytest.mark.parametrize('nodata', [-9999., np.nan])
def test_nodata_is_not_exported_as_linework(tmp_path, nodata):
    values = stripe()
    values[:, 40:56] = nodata
    source = raster(tmp_path/'mask.tif', values, nodata=nodata)
    report = run(source, tmp_path/'out')
    lines = gpd.read_file(report['outputs']['geopackage'])
    invalid = box(300400.1, 8899040, 300559.9, 8900000)
    assert not lines.geometry.intersects(invalid).any()


def test_rgba_transparent_pixels_are_not_exported(tmp_path):
    values = stripe().astype('uint8')
    rgba = np.stack([values, values, values, np.full_like(values, 255)])
    rgba[3, :, 40:56] = 0
    source = raster(tmp_path/'alpha.tif', rgba, alpha=True)
    result = run(source, tmp_path/'out')
    lines = gpd.read_file(result['outputs']['geopackage'])
    assert not lines.geometry.intersects(box(300400.1, 8899040, 300559.9, 8900000)).any()


@pytest.mark.parametrize('crs,transform', [
    ('EPSG:4326', from_origin(-70, -10, .001, .001)),
    ('EPSG:32718', from_origin(300000, 8900000, 10, 20)),
    ('EPSG:2277', from_origin(300000, 8900000, 10, 10)),
])
def test_geophysics_rejects_unsupported_spatial_units(tmp_path, crs, transform):
    source = raster(tmp_path/'input.tif', stripe(), crs=crs, transform=transform)
    with pytest.raises(ValueError, match='projected metric|square pixels|metres'):
        run(source, tmp_path/'out', extraction_mode='geophysics')


def test_geophysics_rejects_gaps_instead_of_filling_fft_data(tmp_path):
    values = stripe()
    values[0, 0] = -9999
    source = raster(tmp_path/'gap.tif', values, nodata=-9999)
    with pytest.raises(ValueError, match='complete grid'):
        run(source, tmp_path/'out', extraction_mode='geophysics')


@pytest.mark.parametrize('change', [{'workers': 0}, {'workers': 17}, {'fthr': float('nan')},
                                   {'rgb_conversion': 'unknown'}, {'lthr': 1}, {'max_pixels': 20}] )
def test_invalid_settings_fail_clearly(tmp_path, change):
    source = raster(tmp_path/'input.tif', stripe())
    with pytest.raises(ValueError):
        run(source, tmp_path/'out', **change)


def test_missing_crs_is_rejected_before_output_is_created(tmp_path):
    source = raster(tmp_path/'input.tif', stripe(), crs=None)
    with pytest.raises(ValueError, match='no CRS'):
        run(source, tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_existing_output_is_preserved(tmp_path):
    source = raster(tmp_path/'input.tif', stripe())
    output = tmp_path/'out'
    result = run(source, output)
    report = Path(result['outputs']['report']).read_bytes()
    with pytest.raises(FileExistsError):
        run(source, output)
    assert Path(result['outputs']['report']).read_bytes() == report


def test_manifest_and_report_include_finished_outputs_and_version(tmp_path):
    source = raster(tmp_path/'input.tif', stripe())
    result = run(source, tmp_path/'out', profile='Synthetic check', compute_mode='cpu')
    stored = json.loads(Path(result['outputs']['report']).read_text(encoding='utf-8'))
    state = json.loads((tmp_path/'out/mirage_run.json').read_text(encoding='utf-8'))
    assert stored['outputs']['report_markdown'] == result['outputs']['report_markdown']
    assert stored['profile'] == 'Synthetic check'
    assert len(stored['input_sha256']) == 64
    assert state['status'] == 'complete'


def test_cancellation_marks_run_without_publishing_outputs(tmp_path):
    source = raster(tmp_path/'input.tif', stripe())
    with pytest.raises(InterruptedError):
        run(source, tmp_path/'out', cancelled=lambda: True)
    assert json.loads((tmp_path/'out/mirage_run.json').read_text())['status'] == 'cancelled'
    assert not (tmp_path/'out/lineaments.gpkg').exists()


def test_periodic_vertical_derivatives_match_analytic_wavenumber():
    x = np.arange(64)*10
    wavenumber = 2*np.pi*4/(64*10)
    image = np.repeat(np.sin(wavenumber*x)[None, :], 48, axis=0)
    assert np.allclose(first_vertical_derivative(image, 10), wavenumber*image, atol=1e-12)
    assert np.allclose(second_vertical_derivative(image, 10), wavenumber**2*image, atol=1e-12)


def test_rotated_geophysics_is_rejected(tmp_path):
    from rasterio.transform import Affine
    source = raster(tmp_path/'input.tif', stripe(), transform=Affine(10, 1, 300000, 0, -10, 8900000))
    with pytest.raises(ValueError, match='north-up'):
        run(source, tmp_path/'out', extraction_mode='geophysics')


def test_raster_limit_can_be_checked_without_reading_pixel_values(tmp_path):
    source = raster(tmp_path/'input.tif', stripe())
    with pytest.raises(ValueError, match='pixel limit'):
        inspect_raster(source, max_pixels=100)


def test_no_detection_is_a_complete_empty_vector_result(tmp_path):
    source = raster(tmp_path/'constant.tif', np.ones((64, 64), dtype='float32'))
    report = run(source, tmp_path/'out')
    assert report['lineaments']['count'] == 0
    assert gpd.read_file(report['outputs']['geopackage']).empty
    assert gpd.read_file(report['outputs']['lineaments']).empty
    assert json.loads((tmp_path/'out/mirage_run.json').read_text())['status'] == 'complete'


def test_pixel_length_is_distinct_from_map_length_on_rectangular_grid():
    from rasterio.transform import Affine
    from shapely.geometry import LineString
    transform = Affine(10, 0, 300000, 0, -20, 8900000)
    line = LineString([transform*(0, 0), transform*(1, 1), transform*(2, 2)])
    record = _line_record(1, line, 'signature', 2, 60, 2, 0, 20, 10, 20, transform=transform)
    assert record['pix_len'] == pytest.approx(2*np.sqrt(2))
    assert record['map_len'] == pytest.approx(2*np.sqrt(10**2+20**2))


def test_geographic_simplification_requires_reprojection_or_zero_tolerance(tmp_path):
    source = raster(tmp_path/'geographic.tif', stripe(), crs='EPSG:4326',
                    transform=from_origin(-70, -10, .0001, .0001))
    with pytest.raises(ValueError, match='FTHR=0'):
        run(source, tmp_path/'out', fthr=4)
