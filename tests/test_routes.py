"""Scientific contracts and optional-engine safety of the common route API."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

import mirage
from mirage.engine import anisotropy, upward


def test_lazy_namespace_has_no_gui_or_optional_runtime_side_effects():
    # A source checkout is importable through pytest's pythonpath only; give the
    # child interpreter the same package, whether or not MIRAGE is installed.
    source = str(Path(mirage.__file__).resolve().parents[1])
    environment = dict(os.environ, PYTHONPATH=os.pathsep.join(
        filter(None, [source, os.environ.get('PYTHONPATH')])))
    subprocess.run([sys.executable,'-c',
                    'import mirage,sys; assert not {"tkinter","qgis","torch","onnxruntime","numpy"}.intersection(sys.modules); assert "worming" in mirage.routes()["geomatic"]'],check=True,env=environment)


def test_continuation_preserves_constant_and_reduces_roughness():
    constant = np.full((32,32),7.)
    np.testing.assert_allclose(upward(constant,20),constant,atol=1e-12)
    noise = np.random.default_rng(1).normal(size=(32,32))
    assert upward(noise,4).std() < noise.std()
    np.testing.assert_allclose(upward(noise,0),noise,atol=1e-12)


def test_anisotropy_tangent_is_north_for_eastward_gradient():
    image = np.tile(np.arange(32),(32,1))
    azimuth,strength = anisotropy(image)
    np.testing.assert_allclose(azimuth[5:-5,5:-5],0,atol=1e-6)
    np.testing.assert_allclose(strength[5:-5,5:-5],1,atol=1e-6)
    _,constant = anisotropy(np.ones((32,32)))
    np.testing.assert_array_equal(constant,0)


@pytest.mark.parametrize('method',['legacy','thdr','worming','wavelets'])
def test_common_curves_attributes_georeferencing_and_worm_points(method):
    if method == 'wavelets':
        pytest.importorskip('pywt')
    image = np.tile(np.tanh((np.arange(64)-31)/3),(64,1))
    result = mirage.extract(image,method=method,pixel_size=10.,
                            transform=(10,0,500000,0,-10,8000000),
                            heights=(0,20),scales=(10,20))
    assert len(result.lines) == len(result.attributes)
    assert result.strength.shape == image.shape
    assert np.isfinite(result.strength).all()
    for line,record in zip(result.lines,result.attributes):
        assert line.length == record['length']
        assert record['method'] == method
        assert line.bounds[0] >= 500000
        assert 0 <= record['azimuth'] < 180
    assert callable(mirage.routes)
    if method == 'worming':
        assert len(result.points) > 0
        assert set(point[2] for point in result.points) <= {0,20}


def test_invalid_or_cancelled_inputs_fail_before_processing():
    with pytest.raises(ValueError):
        mirage.extract(np.full((32,32),np.nan))
    with pytest.raises(ValueError):
        mirage.extract(np.ones((32,32)),transform=(1,1,0,0,-1,0))
    with pytest.raises(InterruptedError):
        mirage.extract(np.ones((32,32)),cancelled=lambda:True)


def test_wavelet_contact_is_localized_and_invariant_to_field_datum():
    pytest.importorskip('pywt')
    image = np.tile(np.tanh((np.arange(128) - 63) / 3), (128, 1))
    results = [mirage.extract(image + offset, method='wavelets', pixel_size=50,
                             scales=(50, 100, 200), threshold=.35) for offset in (0, 10000)]
    np.testing.assert_allclose(results[0].strength, results[1].strength, atol=1e-10)
    for result in results:
        assert result.lines
        coordinates = np.concatenate([np.asarray(line.coords) for line in result.lines])
        assert np.median(np.abs(coordinates[:, 0] / 50 - 63.5)) <= 2
        assert result.strength[10:-10, 60:67].max() > .9


def test_scientific_profiles_keep_calibration_and_legacy_separate():
    first = mirage.profiles()
    assert first == mirage.profiles()
    assert {'geophysics', 'legacy-array', 'legacy-v120'} == set(first)
    image = np.tile(np.tanh((np.arange(128) - 63) / 3), (128, 1))
    default = mirage.extract(image, pixel_size=50)
    assert default.lines
    assert all(row['method'] == first['geophysics']['method'] for row in default.attributes)
    previous = mirage.extract(image, pixel_size=50, profile='legacy-array')
    assert previous.lines and all(row['method'] == 'thdr' for row in previous.attributes)
    with pytest.raises(ValueError, match='file pipeline'):
        mirage.extract(image, profile='legacy-v120')


def test_neural_requires_explicit_license_and_verified_external_hash(tmp_path):
    from mirage.neural import infer
    image = np.ones((32,32))
    with pytest.raises(ValueError,match='explicitly'):
        infer(image,None)
    model = tmp_path/'untrusted.onnx'
    model.write_bytes(b'not an ONNX graph')
    manifest = {'path':str(model),'sha256':'0'*64,'code_license':'MIT','weights_license':'MIT'}
    with pytest.raises(ValueError,match='SHA-256'):
        infer(image,manifest)
    manifest['sha256'] = hashlib.sha256(model.read_bytes()).hexdigest()
    manifest['weights_license'] = 'research only'
    with pytest.raises(ValueError,match='separately'):
        infer(image,manifest)


def test_common_geopackage_roundtrip_refuses_overwrite(tmp_path):
    fiona = pytest.importorskip('fiona')
    image = np.tile(np.tanh((np.arange(64)-31)/3),(64,1))
    result = mirage.extract(image,method='worming',heights=(0,2))
    destination = tmp_path/'lineaments.gpkg'
    result.write(destination,'EPSG:32618')
    assert set(fiona.listlayers(destination)) == {'lineaments','worms'}
    with fiona.open(destination,layer='lineaments') as layer:
        assert len(layer) == len(result.lines)
        assert 'height' in layer.schema['properties']
    with pytest.raises(FileExistsError):
        result.write(destination,'EPSG:32618')


def test_neural_digest_comparison_ignores_letter_case(tmp_path):
    from mirage.neural import infer
    model = tmp_path/'untrusted.onnx'
    model.write_bytes(b'not an ONNX graph')
    digest = hashlib.sha256(model.read_bytes()).hexdigest().upper()
    manifest = {'path':str(model),'sha256':digest,'code_license':'MIT','weights_license':'MIT'}
    # Verification passes; the failure comes later, from the invalid graph or
    # from a missing ONNX Runtime, never from the digest.
    with pytest.raises(Exception) as caught:
        infer(np.ones((32,32)),manifest)
    assert 'SHA-256' not in str(caught.value)


def test_neural_route_runs_an_external_model_end_to_end(tmp_path):
    onnx = pytest.importorskip('onnx')
    pytest.importorskip('onnxruntime')
    from onnx import TensorProto, helper
    from mirage.neural import infer
    # Channel mean followed by a sigmoid: small enough to state the expected
    # output exactly, and it exercises scaling, mean subtraction, padding and crop.
    graph = helper.make_graph(
        [helper.make_node('ReduceMean', ['input'], ['mean'], axes=[1], keepdims=1),
         helper.make_node('Sigmoid', ['mean'], ['probability'])], 'ridge',
        [helper.make_tensor_value_info('input', TensorProto.FLOAT, [1, 3, 'rows', 'columns'])],
        [helper.make_tensor_value_info('probability', TensorProto.FLOAT, [1, 1, 'rows', 'columns'])])
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid('', 13)])
    model.ir_version = 8
    onnx.checker.check_model(model)
    (tmp_path/'ridge.onnx').write_bytes(model.SerializeToString())
    digest = hashlib.sha256((tmp_path/'ridge.onnx').read_bytes()).hexdigest()
    manifest = tmp_path/'ridge.json'
    manifest.write_text(json.dumps({'path':'ridge.onnx','sha256':digest,'code_license':'MIT',
                                    'weights_license':'CC0-1.0','multiple':8,'input_scale':12.,
                                    'mean':[6.,6.,6.]}))
    # 50 by 70 is not a multiple of 8, so the model sees a padded grid.
    image = np.tile(np.exp(-((np.arange(70)-30)/2.)**2),(50,1))
    probability = infer(image,manifest)
    assert probability.shape == image.shape
    np.testing.assert_allclose(probability,1/(1+np.exp(-(12*image-6))),atol=1e-5)
    result = mirage.extract(image,route='neural',method='onnx',model=manifest,
                            pixel_size=10.,threshold=.5)
    np.testing.assert_allclose(result.strength,probability,atol=1e-6)
    assert result.lines and all(row['route'] == 'neural' for row in result.attributes)
    coordinates = np.concatenate([np.asarray(line.coords) for line in result.lines])
    assert np.median(np.abs(coordinates[:,0]/10-30.5)) <= 1


def test_rejected_write_does_not_block_the_corrected_retry(tmp_path):
    pytest.importorskip('fiona')
    image = np.tile(np.tanh((np.arange(64)-31)/3),(64,1))
    result = mirage.extract(image,pixel_size=25)
    destination = tmp_path/'lineaments.gpkg'
    with pytest.raises(ValueError,match='CRS'):
        result.write(destination,'NOT-A-CRS')
    assert not list(tmp_path.iterdir())
    result.write(destination,'EPSG:32618')
    reservation = json.loads(destination.with_suffix('.mirage-reservation.json').read_text())
    assert reservation['status'] == 'complete'


def test_scene_partitions_and_file_hashes_are_disjoint():
    # Generation is exercised by the full physical benchmark, not mocked grids.
    import os
    bank = os.environ.get('MIRAGE_BENCHMARK_BANK')
    if not bank:
        pytest.skip('Set MIRAGE_BENCHMARK_BANK to audit the physical scene bank.')
    from pathlib import Path
    bank = Path(bank)
    records = json.loads((bank/'manifest.json').read_text())['records']
    groups = [record['group'] for record in records]
    assert len(set(groups)) == len(groups)
    assert {record['split'] for record in records} == {'train','validation','test'}
    for record in records:
        assert hashlib.sha256((bank/record['file']).read_bytes()).hexdigest() == record['sha256']
