"""Keep source provenance in wheels and generated egg-info out of sdists.

The sdist retains root PKG-INFO and pyproject.toml. Setuptools regenerates its
working metadata when a wheel is built from the source distribution.
"""
from pathlib import Path, PurePath
import subprocess

from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist


class BuildPy(build_py):
    def run(self):
        super().run()
        root = Path(__file__).resolve().parent
        try:
            commit = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
            dirty = bool(subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain'], text=True).strip())
        except (OSError, subprocess.CalledProcessError):
            commit, dirty = None, None
        (Path(self.build_lib)/'mirage'/'_build_info.py').write_text(
            f'SOURCE_COMMIT = {commit!r}\nSOURCE_DIRTY = {dirty!r}\n', encoding='utf-8')


class SourceDistribution(sdist):
    def make_release_tree(self, base_dir, files):
        files = [name for name in files
                 if not any(part.endswith('.egg-info') for part in PurePath(name).parts)]
        super().make_release_tree(base_dir, files)


setup(cmdclass={'build_py': BuildPy, 'sdist': SourceDistribution})
