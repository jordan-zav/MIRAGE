"""Inspect release archives without extracting or importing their contents."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
import zipfile


FORBIDDEN_SUFFIXES = {'.onnx', '.pth', '.pt', '.ckpt', '.npz', '.npy', '.tif', '.tiff',
                      '.gpkg', '.sqlite', '.pyc', '.pyo'}
FORBIDDEN_PARTS = {'build', '__pycache__', '.pytest_cache', '.ruff_cache', '.git',
                   '.venv', 'venv', 'datasets', 'data', 'weights', 'models'}
LOCAL_PATH = re.compile(rb'(?i)(?<![a-z0-9_])([DNO]:[/\\]|C:[/\\]Users[/\\])')


def inspect(path):
    if path.suffix in ('.whl', '.zip'):
        with zipfile.ZipFile(path) as archive:
            assert archive.testzip() is None, path
            files = {name: archive.read(name) for name in archive.namelist() if not name.endswith('/')}
    else:
        with tarfile.open(path, 'r:gz') as archive:
            assert all(member.isfile() or member.isdir() for member in archive.getmembers()), path
            files = {m.name: archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}
    assert files, path
    for name, data in files.items():
        posix = PurePosixPath(name)
        assert not posix.is_absolute() and '..' not in posix.parts, name
        assert not any(p.lower() in FORBIDDEN_PARTS or p.endswith('.egg-info') for p in posix.parts), name
        assert posix.suffix.lower() not in FORBIDDEN_SUFFIXES, name
        # Scan textual content; bitmap branding is allowed by the packaging allowlist.
        if posix.suffix.lower() not in {'.png', '.jpg', '.jpeg'}:
            assert not LOCAL_PATH.search(data), name
        # A release must say which commit it was built from.
        if posix.name == '_build_info.py':
            assert b'SOURCE_COMMIT = None' not in data, name
    return dict(artifact=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                files={name:hashlib.sha256(data).hexdigest() for name,data in sorted(files.items())})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    paths = sorted(p for p in args.directory.iterdir() if p.name.endswith(('.whl','.tar.gz','.zip')))
    assert paths, 'No release archives found'
    print(json.dumps([inspect(p) for p in paths], indent=2))


if __name__ == '__main__':
    main()
