"""Use host GIS libraries; missing image libraries live outside the QGIS install."""

import importlib
import os
from pathlib import Path
import sys

PACKAGES = {
    'skimage': 'scikit-image>=0.25,<0.27',
    'imageio': 'imageio>=2.33,<3',
    'tifffile': 'tifffile>=2024.2,<2027',
    'lazy_loader': 'lazy-loader>=0.4,<1',
    'networkx': 'networkx>=3,<4',
    'PIL': 'pillow>=10,<14',
    'packaging': 'packaging>=23',
}


def dependency_directory():
    override = os.environ.get('MIRAGE_QGIS_DEPENDENCIES')
    if override:
        return Path(override)
    root = Path('D:/DevResources')
    version = f'py{sys.version_info.major}{sys.version_info.minor}'
    if root.is_dir():
        return root/'Shared'/'MIRAGE'/('qgis-'+version)
    from qgis.core import QgsApplication
    return Path(QgsApplication.qgisSettingsDirPath())/'python'/'mirage_dependencies'/version


def activate():
    path = dependency_directory()
    # Keep QGIS' NumPy/GDAL and other already available packages first.
    if path.is_dir() and str(path) not in sys.path:
        sys.path.append(str(path))
    importlib.invalidate_caches()


def temporary_root():
    root = Path('D:/DevResources')
    if root.is_dir():
        result = root/'Sessions'/'MIRAGE_QGIS'
    else:
        import tempfile
        result = Path(tempfile.gettempdir())/'MIRAGE_QGIS'
    result.mkdir(parents=True, exist_ok=True)
    return result


def missing_libraries():
    activate()
    missing = {}
    for module in ('numpy', 'scipy', 'shapely', 'pyproj', 'osgeo.gdal', *PACKAGES):
        try:
            importlib.import_module(module)
        except Exception as error:
            missing[module] = str(error)
    return missing


def installation_command():
    missing = missing_libraries()
    host_missing = set(missing)-set(PACKAGES)
    if host_missing:
        raise RuntimeError('Required QGIS libraries unavailable: '+', '.join(sorted(host_missing)))
    executable = Path(sys.prefix)/('python.exe' if os.name == 'nt' else 'bin/python3')
    if not executable.is_file():
        raise RuntimeError('Cannot find the Python interpreter of this QGIS installation.')
    packages = [PACKAGES[module] for module in missing]
    if not packages:
        return None
    directory = dependency_directory()
    directory.mkdir(parents=True, exist_ok=True)
    cache = Path('D:/DevResources/Shared/pip') if Path('D:/DevResources').is_dir() else directory.parent/'wheel-cache'
    arguments = ['-m', 'pip', 'install', '--disable-pip-version-check', '--no-deps', '--upgrade',
                 '--no-compile', '--only-binary=:all:', '--cache-dir', str(cache),
                 '--target', str(directory), *packages]
    return str(executable), arguments


def require_runtime():
    missing = missing_libraries()
    if missing:
        raise RuntimeError('Open MIRAGE and install its missing libraries: '+', '.join(missing))
