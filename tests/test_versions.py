"""Every public declaration of the release number must agree before a tag."""
import configparser
import json
from pathlib import Path
import re
import tomllib

import mirage

ROOT = Path(__file__).resolve().parents[1]


def test_all_version_declarations_agree():
    version = mirage.__version__
    assert re.fullmatch(r'\d+\.\d+\.\d+', version)
    project = tomllib.loads((ROOT/'pyproject.toml').read_text(encoding='utf-8'))['project']
    metadata = configparser.ConfigParser()
    metadata.read(ROOT/'mirage_qgis/metadata.txt', encoding='utf-8')
    citation = re.search(r'^version:\s*(\S+)\s*$', (ROOT/'CITATION.cff').read_text(encoding='utf-8'), re.M)
    declared = {
        'pyproject.toml': project['version'],
        'mirage_qgis/metadata.txt': metadata['general']['version'],
        'CITATION.cff': citation.group(1).strip('"\''),
        '.zenodo.json': json.loads((ROOT/'.zenodo.json').read_text(encoding='utf-8'))['version'],
    }
    for name in ('README.md', 'README.es.md', 'mirage_qgis/README.md', 'mirage_qgis/README.es.md'):
        title = (ROOT/name).read_text(encoding='utf-8').splitlines()[0]
        declared[name] = title.rsplit(' ', 1)[-1]
    assert declared == dict.fromkeys(declared, version)


def test_changelog_documents_the_current_version():
    changelog = (ROOT/'CHANGELOG.md').read_text(encoding='utf-8')
    assert re.search(r'^## '+re.escape(mirage.__version__)+r'\b', changelog, re.M)
