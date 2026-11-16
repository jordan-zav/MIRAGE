"""Installed build identity owned by MIRAGE, independent of host adapters."""
from importlib import metadata
import hashlib
import json
from pathlib import Path

from .version import __version__


def build_provenance():
    try:
        from ._build_info import SOURCE_COMMIT, SOURCE_DIRTY
    except ImportError:
        SOURCE_COMMIT, SOURCE_DIRTY = None, None
    files = {}
    for name in ('engine.py','line_core.py','adaptive.py','neural.py','outputs.py',
                 'raster_backend.py','pipeline.py','config.py','_profiles.py','geophysics_calibration.json'):
        source = Path(__file__).parent/name
        files[name] = hashlib.sha256(source.read_bytes()).hexdigest()
    try:
        direct = metadata.distribution('mirage-geo').read_text('direct_url.json')
        direct = json.loads(direct) if direct else None
    except metadata.PackageNotFoundError:
        direct = None
    if direct and direct.get('vcs_info',{}).get('commit_id'):
        SOURCE_COMMIT = direct['vcs_info']['commit_id']
    return {'distribution':'mirage-geo','version':__version__,
            'commit':SOURCE_COMMIT,'source_dirty_at_build':SOURCE_DIRTY,
            'source_sha256':files,'direct_url':direct,
            'geological_origin_inference':False}
