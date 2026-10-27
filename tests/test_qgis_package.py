"""The public ZIP must contain the shared core and no local resources."""

import configparser
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('package_qgis', ROOT/'scripts/package_qgis.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def test_qgis_archive_contains_identical_core_and_valid_manifest(tmp_path):
    output = builder.build(tmp_path/'MIRAGE_QGIS_1.2.0.zip')
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        assert all(name.startswith('mirage_qgis/') and '..' not in Path(name).parts for name in names)
        assert not any(token in name.lower() for name in names for token in ('dataset/', 'artifacts/', '.venv/', 'auth.json'))
        manifest = json.loads(archive.read('mirage_qgis/build_manifest.json'))
        for name, expected in manifest['files'].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == expected
        for name in ('adaptive.py', 'line_core.py', 'pipeline.py', 'raster_backend.py', 'config.py',
                     'version.py', 'ai/__init__.py', 'ai/parameter_advisor.py'):
            assert archive.read('mirage_qgis/core/'+name) == (ROOT/'src'/name).read_bytes()
        metadata = configparser.ConfigParser()
        metadata.read_string(archive.read('mirage_qgis/metadata.txt').decode())
        assert metadata['general']['version'] == manifest['version'] == '1.2.0'
        assert metadata['general']['hasProcessingProvider'] == 'yes'
        assert archive.read('mirage_qgis/LICENSE.txt') == (ROOT/'LICENSE.txt').read_bytes()


def test_packager_never_overwrites_an_existing_archive(tmp_path):
    output = tmp_path/'MIRAGE.zip'
    output.write_bytes(b'preserved')
    with pytest.raises(FileExistsError):
        builder.build(output)
    assert output.read_bytes() == b'preserved'
