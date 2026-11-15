"""Compatibility import for pre-1.3 source callers."""
import importlib
import sys
_module = importlib.import_module("mirage.version")
sys.modules[__name__] = _module
globals().update(vars(_module))
