"""Create a QGIS ZIP from an explicit allowlist and the single source core."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build(output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError('Choose a new ZIP path; previous builds are preserved.')
    files = {}
    for file in (ROOT/'mirage_qgis').glob('*.py'):
        files['mirage_qgis/'+file.name] = file.read_bytes()
    files['mirage_qgis/metadata.txt'] = (ROOT/'mirage_qgis/metadata.txt').read_bytes()
    files['mirage_qgis/icon.png'] = (ROOT/'assets/branding/logo_clean.png').read_bytes()
    files['mirage_qgis/core/__init__.py'] = b'"""Shared MIRAGE numerical core, bundled without modification."""\n'
    for name in ('adaptive.py', 'line_core.py', 'pipeline.py', 'raster_backend.py', 'config.py', 'version.py',
                 'ai/__init__.py', 'ai/parameter_advisor.py'):
        files['mirage_qgis/core/'+name] = (ROOT/'src'/name).read_bytes()
    for name in ('LICENSE.txt', 'README.md', 'README.es.md'):
        source = ROOT/name if name == 'LICENSE.txt' else ROOT/'mirage_qgis'/name
        files['mirage_qgis/'+name] = source.read_bytes()
    try:
        commit = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
        dirty = bool(subprocess.check_output(['git', '-C', str(ROOT), 'diff', '--name-only'], text=True).strip())
    except subprocess.CalledProcessError:
        commit, dirty = None, None
    manifest = {'version': '1.2.0', 'source_commit': commit, 'tracked_changes_at_build': dirty,
                'files': {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())},
                'core_source': 'src; the plugin contains byte-identical copies',
                'scientific_validation': 'Software and synthetic checks do not establish field validity.'}
    files['mirage_qgis/build_manifest.json'] = json.dumps(manifest, indent=2).encode()
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(name, data)
    print(json.dumps({'zip': str(output), 'files': len(files),
                      'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}))
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    build(parser.parse_args().output)
