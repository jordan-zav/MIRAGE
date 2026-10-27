"""MIRAGE QGIS entry point. Scientific imports remain lazy."""


def classFactory(iface):
    from .plugin import MiragePlugin
    return MiragePlugin(iface)
