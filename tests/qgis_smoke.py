# ruff: noqa: E402
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import zipfile

parser = argparse.ArgumentParser(description='Exercise the packaged MIRAGE plugin in an offscreen QGIS application.')
parser.add_argument('zip', type=Path)
parser.add_argument('--workspace', type=Path, required=True)
args = parser.parse_args()
SESSION = args.workspace.resolve()
SESSION.mkdir(parents=True, exist_ok=True)
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['QGIS_CUSTOM_CONFIG_PATH'] = str(SESSION/'qgis_profile')
os.environ['QGIS_AUTH_DB_DIR_PATH'] = str(SESSION/'qgis_profile/auth')
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
archive = args.zip.resolve()
target = SESSION/(archive.stem+'_extracted_'+str(time.time_ns()))
target.mkdir()
with zipfile.ZipFile(archive) as package:
    assert all(name.startswith('mirage_qgis/') and '..' not in Path(name).parts for name in package.namelist())
    package.extractall(target)
manifest = json.loads((target/'mirage_qgis/build_manifest.json').read_text())
for name, digest in manifest['files'].items():
    assert hashlib.sha256((target/name).read_bytes()).hexdigest() == digest
sys.path.insert(0, str(target))

import numpy as np
from osgeo import gdal, osr
from qgis.PyQt.QtWidgets import QMainWindow
from qgis.core import QgsApplication, QgsGeometry, QgsProject, QgsRasterLayer, QgsRectangle, QgsVectorLayer, Qgis

app = QgsApplication([], True)
app.initQgis()
from qgis.PyQt.QtGui import QFont, QFontDatabase
font = Path('C:/Windows/Fonts/arial.ttf')
if font.is_file():
    QFontDatabase.addApplicationFont(str(font))
    app.setFont(QFont('Arial', 10))
sys.path.insert(0, str(Path(QgsApplication.prefixPath())/'python/plugins'))
from processing.core.Processing import Processing
Processing.initialize()
import processing
from mirage_qgis import classFactory
from mirage_qgis.dependencies import require_runtime


class Iface:
    def __init__(self):
        self.window = QMainWindow()
        self.layers = []

    def mainWindow(self):
        return self.window

    def addPluginToRasterMenu(self, *args):
        pass

    def addToolBarIcon(self, *args):
        pass

    def removePluginRasterMenu(self, *args):
        pass

    def removeToolBarIcon(self, *args):
        pass

    def addDockWidget(self, area, widget):
        self.window.addDockWidget(area, widget)

    def removeDockWidget(self, widget):
        self.window.removeDockWidget(widget)

    def addVectorLayer(self, path, name, provider):
        layer = QgsVectorLayer(path, name, provider)
        assert layer.isValid()
        QgsProject.instance().addMapLayer(layer)
        self.layers.append(layer)
        return layer


require_runtime()
iface = Iface()
plugin = classFactory(iface)
plugin.initGui()
assert len(QgsApplication.processingRegistry().providerById('mirage').algorithms()) == 2
folder = target/'checks'
folder.mkdir()
source = folder/'source.tif'
dataset = gdal.GetDriverByName('GTiff').Create(str(source), 96, 96, 1, gdal.GDT_Byte)
dataset.SetGeoTransform((300000, 10, 0, 8900000, 0, -10))
crs = osr.SpatialReference()
crs.ImportFromEPSG(32718)
dataset.SetProjection(crs.ExportToWkt())
values = np.zeros((96, 96), dtype='uint8')
values[46:50, 10:86] = 255
dataset.GetRasterBand(1).WriteArray(values)
dataset = None
layer = QgsRasterLayer(str(source), 'Synthetic stripe')
assert layer.isValid()
QgsProject.instance().addMapLayer(layer)
parameters = dict(INPUT=layer, MODE=0, RADI=2, GTHR=60, LTHR=8, FTHR=0,
                  ATHR=20, DTHR=10, MAX_PIXELS=16000000, FILTER=0, FEATURE=0,
                  OUTPUT=str(folder/'processing'))
result = processing.run('mirage:extract_signatures', parameters)
vector = QgsVectorLayer(result['LINEAMENTS']+'|layername=lineaments', 'Result', 'ogr')
assert vector.isValid() and vector.featureCount() > 0
assert vector.crs().authid() == 'EPSG:32718'
for kind in ('nodata', 'alpha'):
    path = folder/(kind+'.tif')
    bands = 4 if kind == 'alpha' else 1
    dtype = gdal.GDT_Byte if bands == 4 else gdal.GDT_Float32
    dataset = gdal.GetDriverByName('GTiff').Create(str(path), 96, 96, bands, dtype)
    dataset.SetGeoTransform((300000, 10, 0, 8900000, 0, -10))
    dataset.SetProjection(crs.ExportToWkt())
    if kind == 'nodata':
        masked = values.astype('float32')
        masked[:, 40:56] = -9999
        dataset.GetRasterBand(1).WriteArray(masked)
        dataset.GetRasterBand(1).SetNoDataValue(-9999)
    else:
        for index, interpretation in enumerate((gdal.GCI_RedBand, gdal.GCI_GreenBand,
                                               gdal.GCI_BlueBand, gdal.GCI_AlphaBand), 1):
            band = dataset.GetRasterBand(index)
            band.SetColorInterpretation(interpretation)
            if index < 4:
                band.WriteArray(values)
            else:
                alpha = np.full((96, 96), 255, dtype='uint8')
                alpha[:, 40:56] = 0
                band.WriteArray(alpha)
    dataset = None
    masked_layer = QgsRasterLayer(str(path), kind)
    masked_result = processing.run('mirage:extract_signatures', dict(parameters, INPUT=masked_layer,
                                  OUTPUT=str(folder/(kind+'_result'))))
    masked_vector = QgsVectorLayer(masked_result['LINEAMENTS']+'|layername=lineaments', kind, 'ogr')
    assert masked_vector.isValid() and masked_vector.featureCount() > 0
    invalid = QgsGeometry.fromRect(QgsRectangle(300400.1, 8899040, 300559.9, 8900000))
    assert all(not feature.geometry().intersects(invalid) for feature in masked_vector.getFeatures())
geophysical = dict(parameters, MODE=2, OUTPUT=str(folder/'geophysical'))
geophysical_result = processing.run('mirage:extract_signatures', geophysical)
assert QgsVectorLayer(geophysical_result['LINEAMENTS']+'|layername=lineaments', 'Geophysics', 'ogr').isValid()
# An analytic trough exercises physical curvature extraction independently of
# an enhancement filter that may legitimately produce no accepted lineaments.
trough_path = folder/'trough.tif'
trough = 255-200*np.exp(-0.5*((np.arange(96)-48)/6)**2)
dataset = gdal.GetDriverByName('GTiff').Create(str(trough_path), 96, 96, 1, gdal.GDT_Float32)
dataset.SetGeoTransform((300000, 10, 0, 8900000, 0, -10))
dataset.SetProjection(crs.ExportToWkt())
dataset.GetRasterBand(1).WriteArray(np.repeat(trough[None, :], 96, axis=0))
dataset = None
trough_layer = QgsRasterLayer(str(trough_path), 'Analytic trough')
trough_result = processing.run('mirage:extract_signatures', dict(parameters, INPUT=trough_layer,
                              MODE=2, FILTER=5, OUTPUT=str(folder/'analytic_trough')))
trough_vector = QgsVectorLayer(trough_result['LINEAMENTS']+'|layername=lineaments', 'Trough', 'ogr')
assert trough_vector.isValid() and trough_vector.featureCount() > 0
advisor = processing.run('mirage:recommend_parameters', {'INPUT':layer, 'OUTPUT':str(folder/'recommendation.json')})
recommendation = json.loads(Path(advisor['OUTPUT']).read_text(encoding='utf-8'))
assert set(recommendation['params']) == {'RADI','GTHR','LTHR','FTHR','ATHR','DTHR'}
plugin.show_panel()
import mirage_qgis.plugin as plugin_module
from mirage_qgis import dependencies
real_missing = dependencies.missing_libraries
dependencies.missing_libraries = lambda: {'skimage': 'synthetic missing dependency'}
install_command = dependencies.installation_command()
dependencies.missing_libraries = real_missing
assert '--no-deps' in install_command[1] and '--only-binary=:all:' in install_command[1]
assert '--target' in install_command[1]
installer = plugin_module.installation_command
plugin_module.installation_command = lambda: (install_command[0], ['-c', 'print("isolated installer process smoke check")'])
plugin.dock.install_libraries()
plugin_module.installation_command = installer
deadline = time.monotonic()+30
while plugin.dock.process.state() != plugin.dock.process.NotRunning and time.monotonic() < deadline:
    app.processEvents()
    time.sleep(.02)
app.processEvents()
assert plugin.dock.install.isEnabled()
plugin.dock.raster.setLayer(layer)
plugin.dock.output.setText(str(folder/'panel_task'))
for name, value in dict(RADI=2, GTHR=60, LTHR=8, FTHR=0, ATHR=20, DTHR=10).items():
    plugin.dock.parameters[name].setValue(value)
plugin.dock.start_extraction()
deadline = time.monotonic()+90
while plugin.dock.task is not None and time.monotonic() < deadline:
    app.processEvents()
    time.sleep(0.02)
assert iface.layers, plugin.dock.status.text()
assert plugin.dock.run.isEnabled()
iface.window.resize(500, 850)
iface.window.show()
plugin.dock.resize(480, 820)
app.processEvents()
plugin.dock.grab().save(str(SESSION/'qgis_panel.png'))
assert 'rasterio' not in sys.modules and 'fiona' not in sys.modules
record = {'qgis':Qgis.QGIS_VERSION, 'python':sys.version, 'algorithms':2,
          'processing_features':vector.featureCount(), 'panel_loaded_result':True,
          'advisor':True, 'geophysics':True, 'analytic_trough':True,
          'native_nodata':True, 'native_alpha':True,
          'installer_command_policy':True, 'installer_process_callback':True,
          'uses_native_gdal':True, 'rasterio_imported':False,
          'manifest_hashes':True, 'zip':str(archive)}
plugin.unload()
assert QgsApplication.processingRegistry().providerById('mirage') is None
plugin.initGui()
assert len(QgsApplication.processingRegistry().providerById('mirage').algorithms()) == 2
plugin.unload()
print(json.dumps(record, indent=2), flush=True)
(SESSION/'qgis_smoke_result.json').write_text(json.dumps(record,indent=2), encoding='utf-8')
QgsProject.instance().clear()
# Let Python/QGIS release their wrappers together at interpreter shutdown.
