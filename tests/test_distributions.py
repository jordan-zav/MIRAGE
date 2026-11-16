"""Release inspection rejects data/weights and machine-specific payloads."""
import importlib.util
from pathlib import Path
import zipfile

import pytest

spec = importlib.util.spec_from_file_location(
    'check_distributions', Path(__file__).resolve().parents[1]/'scripts/check_distributions.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


@pytest.mark.parametrize('name', ['model.onnx', 'sample.tif', 'build/source.py',
                                 'lib.egg-info/SOURCES.txt', '__pycache__/module.pyc'])
def test_rejects_private_or_generated_archive_members(tmp_path, name):
    artifact = tmp_path/'candidate.whl'
    with zipfile.ZipFile(artifact, 'w') as archive:
        archive.writestr(name, b'payload')
    with pytest.raises(AssertionError, match=name.replace('.', r'\.')):
        checker.inspect(artifact)


def test_rejects_a_wheel_that_does_not_record_its_source_commit(tmp_path):
    artifact = tmp_path/'candidate.whl'
    with zipfile.ZipFile(artifact, 'w') as archive:
        archive.writestr('mirage/_build_info.py', b"SOURCE_COMMIT = 'abc123'\nSOURCE_DIRTY = False\n")
    assert checker.inspect(artifact)['files']
    with zipfile.ZipFile(artifact, 'w') as archive:
        archive.writestr('mirage/_build_info.py', b'SOURCE_COMMIT = None\nSOURCE_DIRTY = None\n')
    with pytest.raises(AssertionError, match='_build_info'):
        checker.inspect(artifact)


def test_rejects_machine_path_but_accepts_text_ending_in_colon(tmp_path):
    artifact = tmp_path/'candidate.whl'
    with zipfile.ZipFile(artifact, 'w') as archive:
        archive.writestr('module.py', b'message="saved in:\\n"')
    assert checker.inspect(artifact)['files']
    # Assemble an arbitrary absolute drive path without recording an author path.
    with zipfile.ZipFile(artifact, 'w') as archive:
        archive.writestr('module.py', bytes([68, 58, 47])+b'private/session')
    with pytest.raises(AssertionError, match='module.py'):
        checker.inspect(artifact)
