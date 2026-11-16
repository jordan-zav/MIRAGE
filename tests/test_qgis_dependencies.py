"""Dependency placement must work without any author-specific filesystem."""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest

spec = importlib.util.spec_from_file_location(
    'mirage_dependencies', Path(__file__).resolve().parents[1]/'mirage_qgis/dependencies.py')
dependencies = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dependencies)


def test_explicit_directory_needs_no_qgis(monkeypatch, tmp_path):
    monkeypatch.setenv('MIRAGE_QGIS_DEPENDENCIES', str(tmp_path/'external'))
    monkeypatch.setitem(sys.modules, 'qgis.core', None)
    assert dependencies.dependency_directory() == tmp_path/'external'


@pytest.mark.parametrize('override', [None, ''])
def test_settings_directory_fallback(monkeypatch, tmp_path, override):
    monkeypatch.delenv('MIRAGE_QGIS_DEPENDENCIES', raising=False)
    if override is not None:
        monkeypatch.setenv('MIRAGE_QGIS_DEPENDENCIES', override)
    core = ModuleType('qgis.core')
    core.QgsApplication = SimpleNamespace(qgisSettingsDirPath=lambda: str(tmp_path))
    monkeypatch.setitem(sys.modules, 'qgis.core', core)
    version = f'py{sys.version_info.major}{sys.version_info.minor}'
    assert dependencies.dependency_directory() == tmp_path/'python'/'mirage_dependencies'/version


def test_temporary_root_uses_session_environment(monkeypatch, tmp_path):
    import tempfile
    monkeypatch.setattr(tempfile, 'gettempdir', lambda: str(tmp_path))
    assert dependencies.temporary_root() == tmp_path/'MIRAGE_QGIS'
    assert dependencies.temporary_root().is_dir()


def test_installer_places_cache_beside_dependency_directory(monkeypatch, tmp_path):
    # QGIS places its interpreter directly in its prefix on Windows, unlike a venv.
    import os
    host = tmp_path/'host'
    interpreter = host/('python.exe' if os.name == 'nt' else 'bin/python3')
    interpreter.parent.mkdir(parents=True)
    interpreter.write_bytes(b'host interpreter fixture')
    monkeypatch.setattr(sys, 'prefix', str(host))
    directory = tmp_path/'dependencies'/'py-test'
    monkeypatch.setenv('MIRAGE_QGIS_DEPENDENCIES', str(directory))
    monkeypatch.setattr(dependencies, 'missing_libraries', lambda: {'skimage': 'missing'})
    executable, arguments = dependencies.installation_command()
    assert Path(executable).is_file()
    assert arguments[arguments.index('--target')+1] == str(directory)
    assert arguments[arguments.index('--cache-dir')+1] == str(directory.parent/'wheel-cache')
    assert '--no-deps' in arguments
