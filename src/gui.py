"""Compatibility launcher for the standalone GUI."""
if __name__ == "__main__":
    import runpy
    runpy.run_module("mirage.gui", run_name="__main__")
else:
    from mirage.gui import LineamentGUI as LineamentGUI
