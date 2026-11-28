"""Keep source provenance in wheels and generated egg-info out of sdists.

The sdist retains root PKG-INFO and pyproject.toml. Setuptools regenerates its
working metadata when a wheel is built from the source distribution. The sdist
also carries the commit it was cut from, because a wheel built from an sdist
(the default of python -m build) has no Git checkout to ask.
"""
from pathlib import Path, PurePath
import subprocess

from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist

ROOT = Path(__file__).resolve().parent
BUILD_INFO = PurePath('mirage', '_build_info.py')


def git_state():
    """Commit and dirty flag of this checkout, or None outside its own repository."""
    def git(*arguments):
        return subprocess.check_output(['git', '-C', str(ROOT), *arguments], text=True,
                                       stderr=subprocess.DEVNULL).strip()
    try:
        # An unpacked sdist inside some other repository must not adopt its commit.
        if Path(git('rev-parse', '--show-toplevel')).resolve() != ROOT:
            return None
        # Only tracked changes make a build dirty; build staging trees are untracked.
        return git('rev-parse', 'HEAD'), bool(git('status', '--porcelain', '--untracked-files=no'))
    except (OSError, subprocess.CalledProcessError):
        return None


def write_build_info(path, state):
    commit, dirty = state or (None, None)
    path.write_text(f'SOURCE_COMMIT = {commit!r}\nSOURCE_DIRTY = {dirty!r}\n', encoding='utf-8')


class BuildPy(build_py):
    def run(self):
        super().run()
        target = Path(self.build_lib)/BUILD_INFO
        state = git_state()
        # Without a checkout, keep the record an sdist brought along.
        if state is not None or not target.is_file():
            write_build_info(target, state)


class SourceDistribution(sdist):
    def make_release_tree(self, base_dir, files):
        files = [name for name in files
                 if not any(part.endswith('.egg-info') for part in PurePath(name).parts)]
        super().make_release_tree(base_dir, files)
        target = Path(base_dir)/'src'/BUILD_INFO
        state = git_state()
        if state is not None or not target.is_file():
            # Release trees may hard-link sources; replace, never write through.
            target.unlink(missing_ok=True)
            write_build_info(target, state)


setup(cmdclass={'build_py': BuildPy, 'sdist': SourceDistribution})
