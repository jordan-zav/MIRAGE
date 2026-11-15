"""Stable, lazy MIRAGE API. Importing this module performs no I/O."""
from .version import __version__

__all__ = ['__version__', 'extract', 'recommend', 'preview', 'routes', 'provenance']


def routes():
    """Return methods and their optional dependency requirements."""
    return {'geomatic': {'legacy': None, 'thdr': None, 'worming': None,
                         'wavelets': 'wavelets', 'anisotropy': None},
            'neural': {'onnx': 'nn; experimental; explicit model manifest required'}}


def extract(*args, **kwargs):
    """Extract arrays into a common result; see docs/API.md."""
    from .engine import extract as execute
    return execute(*args, **kwargs)


def recommend(*args, **kwargs):
    """Recommend physical-scale candidates using the established v1.2 engine."""
    from .adaptive import recommend_adaptive
    return recommend_adaptive(*args, **kwargs)


def preview(*args, **kwargs):
    """Run the same extraction on an explicitly supplied preview array/window."""
    return extract(*args, **kwargs)


def provenance():
    """Return the installed version, build commit, dirty marker and source hashes."""
    from ._provenance import build_provenance
    return build_provenance()

