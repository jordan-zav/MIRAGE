"""Native QGIS interface, tasks and result review."""

from pathlib import Path

from qgis.PyQt.QtCore import QProcess, QProcessEnvironment, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QAction, QComboBox, QDockWidget, QDoubleSpinBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QProgressBar, QPushButton,
    QScrollArea, QSpinBox, QTextEdit, QVBoxLayout, QWidget,
)
from qgis.core import (
    QgsApplication, QgsMapLayerProxyModel, QgsProcessingAlgRunnerTask,
    QgsProcessingContext, QgsProcessingFeedback, QgsProject,
)
from qgis.gui import QgsCollapsibleGroupBox, QgsMapLayerComboBox

from .dependencies import installation_command, missing_libraries, temporary_root
from .processing_provider import MirageProvider


class MiragePlugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.dock = None

    def initGui(self):
        self.provider = MirageProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)
        self.action = QAction(QIcon(str(Path(__file__).with_name('icon.png'))), 'MIRAGE', self.iface.mainWindow())
        self.action.triggered.connect(self.show_panel)
        self.iface.addPluginToRasterMenu('MIRAGE', self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.dock:
            self.dock.closing = True
            self.dock.cancel()
            self.iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
            self.dock = None
        self.iface.removePluginRasterMenu('MIRAGE', self.action)
        self.iface.removeToolBarIcon(self.action)
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)

    def show_panel(self):
        if self.dock is None:
            self.dock = MirageDock(self.iface)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        self.dock.show()
        self.dock.raise_()


class MirageDock(QDockWidget):
    def __init__(self, iface):
        super().__init__('MIRAGE', iface.mainWindow())
        self.iface = iface
        self.setObjectName('MirageDock')
        self.task = None
        self.closing = False
        self.feedback = None
        widget = QWidget()
        layout = QVBoxLayout(widget)
        intro = QLabel('Extract raster signatures, then review them with your reference layers.')
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.raster = QgsMapLayerComboBox()
        self.raster.setFilters(QgsMapLayerProxyModel.RasterLayer)
        form = QFormLayout()
        form.addRow('Raster', self.raster)
        self.mode = QComboBox()
        self.mode.addItems(['Geological signature', 'Archaeological geometry', 'Geophysics'])
        form.addRow('Goal', self.mode)
        self.profile = QComboBox()
        self.profile.addItems(['Structural continuity', 'Geo-arch balance', 'Anthropogenic detail', 'Magnetometry', 'Gravimetry'])
        form.addRow('Profile', self.profile)
        layout.addLayout(form)
        row = QHBoxLayout()
        self.output = QLineEdit()
        self.output.setPlaceholderText('Choose a new output folder')
        browse = QPushButton('Browse')
        browse.clicked.connect(self.choose_output)
        row.addWidget(self.output)
        row.addWidget(browse)
        layout.addLayout(row)
        advanced = QgsCollapsibleGroupBox('Advanced parameters')
        advanced.setCollapsed(True)
        parameters = QFormLayout(advanced)
        self.parameters = {}
        for key, label, value, maximum in [
            ('RADI', 'Smoothing (pixels)', 3, 100), ('GTHR', 'Edge threshold', 66, 100),
            ('LTHR', 'Minimum length (pixels)', 28, 100000),
            ('FTHR', 'Simplification (CRS units)', 4, 100000),
            ('ATHR', 'Linking angle (degrees)', 16, 180), ('DTHR', 'Linking distance (pixels)', 12, 100000),
        ]:
            spin = QDoubleSpinBox()
            spin.setRange(2 if key == 'LTHR' else 0, maximum)
            spin.setDecimals(0 if key in ('RADI', 'GTHR', 'LTHR') else 2)
            spin.setValue(value)
            self.parameters[key] = spin
            parameters.addRow(label, spin)
        self.filter = QComboBox()
        self.filter.addItems(['TDR', 'AS', 'VDR1', 'VDR2', 'THDR', 'NONE'])
        parameters.addRow('Geophysical filter', self.filter)
        self.feature = QComboBox()
        self.feature.addItems(['trough', 'ridge'])
        parameters.addRow('Geophysical feature', self.feature)
        self.limit = QSpinBox()
        self.limit.setRange(9, 1000000000)
        self.limit.setValue(16000000)
        parameters.addRow('Maximum pixels', self.limit)
        layout.addWidget(advanced)
        self.profile.currentTextChanged.connect(self.apply_profile)
        self.mode.currentIndexChanged.connect(self.update_mode)
        self.raster.layerChanged.connect(self.update_raster)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.install = QPushButton('Install missing image libraries')
        self.install.clicked.connect(self.install_libraries)
        layout.addWidget(self.install)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(110)
        self.log.hide()
        layout.addWidget(self.log)
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        buttons = QHBoxLayout()
        self.recommend = QPushButton('Recommend')
        self.recommend.clicked.connect(self.recommend_parameters)
        self.run = QPushButton('Extract')
        self.run.clicked.connect(self.start_extraction)
        stop = QPushButton('Cancel')
        stop.clicked.connect(self.cancel)
        buttons.addWidget(self.recommend)
        buttons.addWidget(self.run)
        buttons.addWidget(stop)
        layout.addLayout(buttons)
        note = QLabel('Morphology is evidence to review, not a geological classification. Scores are heuristic.')
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(widget)
        self.setWidget(scroll)
        self.update_mode()
        self.refresh_runtime()
        self.update_raster()

    def refresh_runtime(self):
        missing = missing_libraries()
        ready = not missing
        self.install.setVisible(not ready)
        self.run.setEnabled(ready)
        self.recommend.setEnabled(ready)
        self.status.setText('Ready. Choose a raster and a fresh output folder.' if ready
                            else 'Missing image libraries: '+', '.join(missing))

    def choose_output(self):
        path = QFileDialog.getExistingDirectory(self, 'Select an empty output folder')
        if path:
            self.output.setText(path)

    def update_mode(self, *args):
        geophysics = self.mode.currentIndex() == 2
        self.filter.setEnabled(geophysics)
        self.feature.setEnabled(geophysics)

    def apply_profile(self, name):
        from .core.config import PRESETS
        for key, spin in self.parameters.items():
            spin.setValue(PRESETS[name][key])
        self.update_raster()

    def update_raster(self, *args):
        layer = self.raster.currentLayer()
        if layer is not None and layer.crs().isGeographic():
            self.parameters['FTHR'].setValue(0)
            if hasattr(self, 'status'):
                self.status.setText('Geographic raster: simplification disabled. Reproject for metric tolerances or geophysics.')

    def install_libraries(self):
        try:
            command = installation_command()
            if command is None:
                self.refresh_runtime()
                return
            self.process = QProcess(self)
            import uuid
            temporary = temporary_root()/uuid.uuid4().hex
            temporary.mkdir(parents=True)
            environment = QProcessEnvironment.systemEnvironment()
            environment.insert('TEMP', str(temporary))
            environment.insert('TMP', str(temporary))
            self.process.setProcessEnvironment(environment)
            self.process.setProcessChannelMode(QProcess.MergedChannels)
            self.process.readyReadStandardOutput.connect(
                lambda: self.log.append(bytes(self.process.readAllStandardOutput()).decode('utf-8', errors='replace')))
            self.process.finished.connect(self.install_finished)
            self.log.show()
            self.install.setEnabled(False)
            self.status.setText('Installing libraries separately from QGIS. This can take several minutes.')
            self.process.start(*command)
        except Exception as error:
            self.status.setText(str(error))

    def install_finished(self, code, status):
        if self.closing:
            return
        self.install.setEnabled(True)
        self.refresh_runtime()
        if code:
            self.status.setText('Installation did not complete. Review the log and try again.')

    def parameters_for_run(self):
        layer = self.raster.currentLayer()
        if layer is None:
            raise ValueError('Choose a raster layer first.')
        if not self.output.text().strip():
            raise ValueError('Choose a fresh output folder.')
        return {'INPUT': layer, 'MODE': self.mode.currentIndex(),
                'OUTPUT': self.output.text().strip(), 'FILTER': self.filter.currentIndex(),
                'FEATURE': self.feature.currentIndex(), 'MAX_PIXELS': self.limit.value(),
                **{key: spin.value() for key, spin in self.parameters.items()}}

    def start_extraction(self):
        try:
            if self.task is not None:
                return
            parameters = self.parameters_for_run()
            algorithm = QgsApplication.processingRegistry().createAlgorithmById('mirage:extract_signatures')
            self.context = QgsProcessingContext()
            self.context.setProject(QgsProject.instance())
            self.feedback = QgsProcessingFeedback()
            self.feedback.progressChanged.connect(lambda value: self.progress.setValue(int(value)))
            self.task = QgsProcessingAlgRunnerTask(algorithm, parameters, self.context, self.feedback)
            self.task.executed.connect(self.finished)
            self.run.setEnabled(False)
            self.recommend.setEnabled(False)
            self.status.setText('Extracting signatures…')
            QgsApplication.taskManager().addTask(self.task)
        except Exception as error:
            self.status.setText(str(error))

    def finished(self, succeeded, result):
        if self.closing:
            self.task = None
            return
        self.run.setEnabled(True)
        self.recommend.setEnabled(True)
        if succeeded and result.get('LINEAMENTS'):
            layer = self.iface.addVectorLayer(result['LINEAMENTS']+'|layername=lineaments', 'MIRAGE signatures', 'ogr')
            if layer is not None and layer.isValid():
                self.status.setText(f'Complete: {layer.featureCount()} signatures. Review the GeoPackage against the source raster.')
            else:
                self.status.setText('Processing completed, but the result layer could not be loaded.')
        else:
            self.status.setText('Cancelled.' if self.feedback.isCanceled() else 'Processing failed. See the Processing log.')
        self.task = None

    def cancel(self):
        if self.feedback:
            self.feedback.cancel()
            self.status.setText('Cancellation requested; finishing the current numerical stage.')

    def recommend_parameters(self):
        try:
            import tempfile
            from .processing_provider import RecommendParameters
            layer = self.raster.currentLayer()
            if layer is None:
                raise ValueError('Choose a raster layer first.')
            context = QgsProcessingContext()
            context.setProject(QgsProject.instance())
            with tempfile.TemporaryDirectory(prefix='mirage_advisor_', dir=temporary_root()) as temporary:
                path = Path(temporary)/'recommendation.json'
                algorithm = RecommendParameters()
                algorithm.initAlgorithm()
                algorithm.processAlgorithm({'INPUT': layer, 'OUTPUT': str(path)}, context, QgsProcessingFeedback())
                import json
                result = json.loads(path.read_text(encoding='utf-8'))
            self.profile.setCurrentText(result['profile'])
            modes = {'Geological signature': 0, 'Archaeological signature': 1, 'Geophysics Potential Fields': 2}
            self.mode.setCurrentIndex(modes.get(result['feature_mode'], self.mode.currentIndex()))
            for key, spin in self.parameters.items():
                spin.setValue(result['params'][key])
            self.update_raster()
            self.status.setText(result.get('reason', '')+' Review these heuristic starting parameters before extracting.')
        except Exception as error:
            self.status.setText(str(error))
