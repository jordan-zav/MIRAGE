"""Embed the exact source revision in locally built wheels, without runtime Git."""
from pathlib import Path
import subprocess

from setuptools import setup
from setuptools.command.build_py import build_py


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


setup(cmdclass={'build_py': BuildPy})
