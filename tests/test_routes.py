"""Scientific contracts and optional-engine safety of the common route API."""
import hashlib
import json
import subprocess
import sys

import numpy as np
import pytest

import mirage
from mirage.engine import anisotropy, upward


def test_lazy_namespace_has_no_gui_or_optional_runtime_side_effects():
    subprocess.run([sys.executable,'-c',
                    'import mirage,sys; assert not {"tkinter","qgis","torch","onnxruntime","numpy"}.intersection(sys.modules); assert "worming" in mirage.routes()["geomatic"]'],check=True)


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
