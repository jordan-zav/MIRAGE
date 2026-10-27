"""Physical scale, declaration and provenance regressions independent of QGIS."""
import json
import numpy as np
import pytest
from adaptive import metric_resolution, recommend_adaptive, select_recipe, source_identity, validate_recipe
from pipeline import run_extraction_job
from test_raster_robustness import raster, stripe


def test_physical_lengths_use_native_resolution_not_analysis_resolution():
    image = np.zeros((32, 32))
    a = recommend_adaptive(image, 20, input_kind='terrain', minimum_length_m=1000,
                           linking_gap_m=200, analysis_pixel_size_m=2000)
    b = recommend_adaptive(image, 100, input_kind='terrain', minimum_length_m=1000,
                           linking_gap_m=200, analysis_pixel_size_m=2000)
    for x, y in zip(a['candidates'], b['candidates']):
        assert x['params']['LTHR'] == 50 and y['params']['LTHR'] == 10
        assert x['params']['DTHR'] == 10 and y['params']['DTHR'] == 2
        assert x['realized_scale_m']['minimum_length'] == y['realized_scale_m']['minimum_length'] == 1000


@pytest.mark.parametrize('kind,mode', [('unknown','signature'),('terrain','signature'),
                                      ('optical','signature'),('magnetic','geophysics'),('gravity','geophysics')])
def test_same_ring_cannot_override_declared_input(kind, mode):
    yy, xx = np.indices((64, 64))
    ring = (np.abs(np.hypot(yy-32, xx-32)-18) < 2).astype(float)
    plan = recommend_adaptive(ring, 10, input_kind=kind)
    assert all(c['mode'] == mode for c in plan['candidates'])
    assert plan['input_kind'] == kind


def test_geometry_requires_explicit_goal():
    plan = recommend_adaptive(np.eye(32), 10, input_kind='terrain', goal='geometry')
    assert all(c['mode'] == 'geometry' for c in plan['candidates'])


@pytest.mark.parametrize('kwargs', [dict(pixel_size_m=0),dict(minimum_length_m=-1),
                                    dict(smoothing_m=float('nan')),dict(input_kind='inferred'),
                                    dict(analysis_pixel_size_m=-1)])
def test_invalid_scale_is_rejected(kwargs):
    options = dict(pixel_size_m=10)
    options.update(kwargs)
    with pytest.raises(ValueError):
        recommend_adaptive(np.eye(32), **options)


@pytest.mark.parametrize('crs,transform', [('EPSG:4326',(1,0,0,0,-1,0)),
                                         ('EPSG:32718',(10,0,0,0,-20,0)),
                                         ('EPSG:32718',(10,5,0,0,-10,0))])
def test_metric_recipe_rejects_incompatible_grid(crs, transform):
    with pytest.raises(ValueError):
        metric_resolution(crs, transform)


def test_recipe_rejects_changed_source_and_is_independent_copy(tmp_path):
    source = tmp_path/'input.dat'
    source.write_bytes(b'original')
    plan = recommend_adaptive(np.eye(32), 10)
    plan['source'] = source_identity(source)
    recipe = select_recipe(plan, 'balanced')
    plan['candidates'][0]['params']['GTHR'] = 1
    assert validate_recipe(recipe, source)['params']['GTHR'] != 1
    source.write_bytes(b'changed source')
    with pytest.raises(ValueError, match='source changed'):
        validate_recipe(recipe, source)


def test_selected_recipe_records_and_enforces_physical_length(tmp_path):
    source = raster(tmp_path/'stripe.tif', stripe())
    plan = recommend_adaptive(stripe(), 10, minimum_length_m=900, smoothing_m=20,
                              linking_gap_m=100, simplification_m=0)
    plan['source'] = source_identity(source)
    recipe = select_recipe(plan, 'detail')
    candidate = validate_recipe(recipe, source)
    summary = run_extraction_job(geotiff=str(source), out_dir=str(tmp_path/'run'),
        **{k.lower():v for k,v in candidate['params'].items()},
        extraction_mode=candidate['mode'], adaptive_recipe=recipe)
    # The stripe is shorter than 900m, so returning it would violate user scale.
    assert summary['lineaments']['count'] == 0
    saved = json.loads((tmp_path/'run/mirage_report.json').read_text())
    assert saved['adaptive_recipe']['selected'] == 'detail'
    with pytest.raises(ValueError, match='differs'):
        run_extraction_job(geotiff=str(source), out_dir=str(tmp_path/'bad'),
            **{k.lower():v for k,v in dict(candidate['params'], GTHR=1).items()},
            extraction_mode=candidate['mode'], adaptive_recipe=recipe)
    assert not (tmp_path/'bad').exists()


def test_cli_reuses_recipe_and_rejects_parameter_overrides(tmp_path, capsys):
    from cli import main
    source = raster(tmp_path/'stripe.tif', stripe())
    plan = recommend_adaptive(stripe(), 10, minimum_length_m=60, smoothing_m=20,
                              linking_gap_m=100, simplification_m=0)
    plan['source'] = source_identity(source)
    recipe = select_recipe(plan, 'detail')
    recipe_file = tmp_path/'selected.json'
    recipe_file.write_text(json.dumps(recipe))
    assert main(['-i',str(source),'-o',str(tmp_path/'cli'),'--recipe',str(recipe_file)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['adaptive_recipe']['selected'] == 'detail'
    with pytest.raises(SystemExit):
        main(['-i',str(source),'-o',str(tmp_path/'bad'),'--recipe',str(recipe_file),'--radi','3'])
