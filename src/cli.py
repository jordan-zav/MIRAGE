"""Compatibility import for pre-1.3 source callers."""
import importlib
import sys
_module = importlib.import_module("mirage.cli")
sys.modules[__name__] = _module
if __name__ == "__main__":
    raise SystemExit(_module.main())
