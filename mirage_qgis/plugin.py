"""Native QGIS interface, tasks and result review."""

import json
import uuid
from pathlib import Path

from qgis.PyQt.QtCore import QProcess, QProcessEnvironment, Qt
from qgis.PyQt.QtGui import QIcon, QPixmap
from qgis.PyQt.QtWidgets import (
    QAction, QCheckBox, QComboBox, QDialog, QDockWidget, QDoubleSpinBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QProgressBar, QPushButton,
    QScrollArea, QSpinBox, QTextEdit, QVBoxLayout, QWidget,
)
from qgis.core import (
    QgsApplication, QgsMapLayerProxyModel, QgsProcessingAlgRunnerTask,
    QgsProcessingContext, QgsProcessingFeedback, QgsProject, QgsCoordinateTransform, QgsReferencedPointXY,
)
from qgis.gui import QgsCollapsibleGroupBox, QgsMapLayerComboBox

from .dependencies import installation_command, missing_libraries, temporary_root
from .processing_provider import MirageProvider


# QGIS tasks borrow their processing context. Keep it alive through C++ task
# destruction, including when the dock/plugin is closed during processing.
_TASK_RESOURCES = {}


class MirageFeedback(QgsProcessingFeedback):
    def __init__(self):
        super().__init__()
        self.errors = []

    def reportError(self, error, fatalError=False):
        self.errors.append(str(error))
        super().reportError(error, fatalError)


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
        self.recipe_path = None
        self.applying_recipe = False
        self.preview_result = None
        widget = QWidget()
        layout = QVBoxLayout(widget)
        intro = QLabel('Extract raster signatures, then review them with your reference layers.')
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.raster = QgsMapLayerComboBox()
        self.raster.setFilters(QgsMapLayerProxyModel.RasterLayer)
        form = QFormLayout()
        form.addRow('Raster', self.raster)
        self.kind = QComboBox()
        self.kind.addItems(['Unknown / generic edges', 'Terrain / hillshade', 'Magnetic field', 'Gravity field', 'Optical imagery'])
        form.addRow('Declared input', self.kind)
        self.scale_goal = QComboBox()
        self.scale_goal.addItems(['Structural continuity', 'More detail', 'Preserve geometry'])
        form.addRow('Objective', self.scale_goal)
        self.scales = {}
        for key, label, default, minimum in [
            ('MIN_LENGTH_M', 'Minimum length (m)', 280, .001),
            ('SMOOTHING_M', 'Smoothing radius (m)', 30, 0),
            ('GAP_M', 'Linking gap (m)', 120, 0),
            ('SIMPLIFY_M', 'Simplification (m)', 4, 0)]:
            spin = QDoubleSpinBox()
            spin.setDecimals(3)
            spin.setRange(minimum, 100000000)
            spin.setValue(default)
            self.scales[key] = spin
            form.addRow(label, spin)
        self.mode = QComboBox()
        self.mode.addItems(['Geological signature', 'Archaeological geometry', 'Geophysics'])
        # Legacy expert controls are available only in the advanced group.
        self.profile = QComboBox()
        self.profile.addItems(['Structural continuity', 'Geo-arch balance', 'Anthropogenic detail', 'Magnetometry', 'Gravimetry'])

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
        parameters.addRow('Manual mode', self.mode)
        parameters.addRow('Manual profile', self.profile)
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
        self.manual = QCheckBox('Use manual advanced parameters (skip adaptive recipe)')
        layout.addWidget(self.manual)
        self.kind.currentIndexChanged.connect(self.invalidate_recipe)
        self.scale_goal.currentIndexChanged.connect(self.invalidate_recipe)
        for spin in self.scales.values():
            spin.valueChanged.connect(self.invalidate_recipe)
        for spin in self.parameters.values():
            spin.valueChanged.connect(self.invalidate_recipe)
        self.mode.currentIndexChanged.connect(self.invalidate_recipe)
        self.filter.currentIndexChanged.connect(self.invalidate_recipe)
        self.feature.currentIndexChanged.connect(self.invalidate_recipe)
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
        self.preview = QPushButton('Compare 3 previews')
        self.preview.clicked.connect(self.start_preview)
        self.run = QPushButton('Extract')
        self.run.clicked.connect(self.start_extraction)
        stop = QPushButton('Cancel')
        stop.clicked.connect(self.cancel)
        buttons.addWidget(self.recommend)
        layout.addWidget(self.preview)
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
        self.preview.setEnabled(ready)
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
        self.invalidate_recipe()
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
        if not self.manual.isChecked() and not self.recipe_path:
            raise ValueError('Compare previews and choose a candidate, or explicitly enable manual parameters.')
        if not self.output.text().strip():
            raise ValueError('Choose a fresh output folder.')
        return {'INPUT': layer, 'RECIPE': str(self.recipe_path) if not self.manual.isChecked() else None, 'MODE': self.mode.currentIndex(),
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
            self.feedback = MirageFeedback()
            self.feedback.progressChanged.connect(self.update_progress)
            self.task = QgsProcessingAlgRunnerTask(algorithm, parameters, self.context, self.feedback)
            token = id(self.task)
            _TASK_RESOURCES[token] = (algorithm, self.context, self.feedback, self.task)
            self.task.destroyed.connect(lambda *args, key=token: _TASK_RESOURCES.pop(key, None))
            self.task.executed.connect(self.finished)
            self.run.setEnabled(False)
            self.recommend.setEnabled(False)
            self.preview.setEnabled(False)
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
        self.preview.setEnabled(True)
        if succeeded and result.get('LINEAMENTS'):
            layer = self.iface.addVectorLayer(result['LINEAMENTS']+'|layername=lineaments', 'MIRAGE signatures', 'ogr')
            if layer is not None and layer.isValid():
                self.status.setText(f'Complete: {layer.featureCount()} signatures. Review the GeoPackage against the source raster.')
            else:
                self.status.setText('Processing completed, but the result layer could not be loaded.')
        else:
            self.status.setText('Cancelled.' if self.feedback.isCanceled() else 'Processing failed. See the Processing log.')
        self.task = None

    def update_progress(self, value):
        if not self.closing:
            self.progress.setValue(int(value))

    def cancel(self):
        if self.feedback:
            self.feedback.cancel()
            self.status.setText('Cancellation requested; finishing the current numerical stage.')

    def invalidate_recipe(self, *args):
        if not self.applying_recipe:
            self.recipe_path = None
            if hasattr(self, 'status'):
                self.status.setText('Settings changed. Compare previews and select a candidate before adaptive extraction.')

    def scale_options(self):
        layer = self.raster.currentLayer()
        if layer is None:
            raise ValueError('Choose a raster layer first.')
        return {'INPUT':layer, 'KIND':self.kind.currentIndex(), 'GOAL':self.scale_goal.currentIndex(),
                **{key:spin.value() for key, spin in self.scales.items()}}

    def scale_snapshot(self):
        options = self.scale_options()
        options['INPUT'] = options['INPUT'].source()
        return options

    def recommend_parameters(self):
        try:
            from .adaptive_processing import RecommendParameters
            root = temporary_root()/('adaptive_'+uuid.uuid4().hex)
            root.mkdir(parents=True)
            context = QgsProcessingContext()
            context.setProject(QgsProject.instance())
            algorithm = RecommendParameters()
            algorithm.initAlgorithm()
            algorithm.processAlgorithm(dict(self.scale_options(), OUTPUT=str(root/'candidates.json')),
                                       context, QgsProcessingFeedback())
            plan = json.loads((root/'candidates.json').read_text(encoding='utf-8'))
            self.status.setText('Three physical-scale candidates prepared. Compare previews to choose. '
                                + ' '.join(plan['warnings']))
        except Exception as error:
            self.status.setText(str(error))

    def start_preview(self):
        try:
            if self.task is not None:
                return
            parameters = self.scale_options()
            self.recipe_path = None
            self.preview_result = None
            if hasattr(self, 'review_dialog'):
                self.review_dialog.close()
            self.preview_snapshot = self.scale_snapshot()
            if hasattr(self.iface, 'mapCanvas'):
                canvas = self.iface.mapCanvas()
                center = canvas.center()
                transform = QgsCoordinateTransform(canvas.mapSettings().destinationCrs(),
                                                   parameters['INPUT'].crs(), QgsProject.instance())
                parameters['CENTER'] = QgsReferencedPointXY(transform.transform(center), parameters['INPUT'].crs())
            output = temporary_root()/('preview_'+uuid.uuid4().hex)
            parameters.update(OUTPUT=str(output), WINDOW_PIXELS=256)
            self.context = QgsProcessingContext()
            self.context.setProject(QgsProject.instance())
            self.feedback = MirageFeedback()
            self.feedback.progressChanged.connect(self.update_progress)
            algorithm = QgsApplication.processingRegistry().createAlgorithmById('mirage:preview_candidates')
            self.task = QgsProcessingAlgRunnerTask(algorithm, parameters, self.context, self.feedback)
            token = id(self.task)
            _TASK_RESOURCES[token] = (algorithm, self.context, self.feedback, self.task)
            self.task.destroyed.connect(lambda *args, key=token: _TASK_RESOURCES.pop(key, None))
            self.task.executed.connect(self.preview_finished)
            self.run.setEnabled(False)
            self.preview.setEnabled(False)
            self.recommend.setEnabled(False)
            self.status.setText('Comparing three candidates at the map centre, at native resolution…')
            QgsApplication.taskManager().addTask(self.task)
        except Exception as error:
            self.status.setText(str(error))

    def preview_finished(self, succeeded, result):
        self.task = None
        if self.closing:
            return
        self.run.setEnabled(True)
        self.preview.setEnabled(True)
        self.recommend.setEnabled(True)
        if not succeeded or not result.get('PLAN'):
            self.status.setText('Preview cancelled.' if self.feedback.isCanceled() else 'Preview failed: '+('; '.join(self.feedback.errors) or 'See Processing log; choose a valid window.'))
            return
        if self.scale_snapshot() != self.preview_snapshot:
            self.status.setText('Inputs changed while previewing. Run previews again.')
            return
        self.preview_result = result
        self.show_comparison(result['PLAN'])

    def show_comparison(self, path):
        plan = json.loads(Path(path).read_text(encoding='utf-8'))
        root = Path(path).parent
        dialog = QDialog(self)
        dialog.setWindowTitle('MIRAGE — same native window, three candidates')
        layout = QVBoxLayout(dialog)
        note = QLabel('Choose by comparison with independent evidence. More lines do not mean higher accuracy. '
                      +plan['preview']['background'])
        note.setWordWrap(True)
        layout.addWidget(note)
        row = QHBoxLayout()
        self.choice_buttons = {}
        for candidate in plan['candidates']:
            column = QVBoxLayout()
            column.addWidget(QLabel(candidate['id'].capitalize()+f" · {candidate['preview_summary']['count']} traces"))
            image = QLabel()
            image.setPixmap(QPixmap(str(root/candidate['preview_png'])).scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            column.addWidget(image)
            values = QLabel(' · '.join(f'{key}={value:g}' for key, value in candidate['params'].items()))
            values.setWordWrap(True)
            values.setMaximumWidth(300)
            column.addWidget(values)
            choose = QPushButton('Use '+candidate['id'])
            choose.clicked.connect(lambda checked=False, name=candidate['id']:self.choose_candidate(path, name))
            self.choice_buttons[candidate['id']] = choose
            column.addWidget(choose)
            row.addLayout(column)
        layout.addLayout(row)
        location = QLabel('Saved comparison: '+str(root))
        location.setWordWrap(True)
        layout.addWidget(location)
        self.review_dialog = dialog
        dialog.show()
        self.status.setText('Choose a candidate in the comparison window. No candidate is selected automatically.')

    def choose_candidate(self, path, candidate_id):
        try:
            from .core.adaptive import select_recipe, validate_recipe
            if self.scale_snapshot() != self.preview_snapshot:
                raise ValueError('Inputs changed. Preview again before selecting.')
            plan = json.loads(Path(path).read_text(encoding='utf-8'))
            recipe = select_recipe(plan, candidate_id)
            candidate = validate_recipe(recipe, self.raster.currentLayer().source())
            selected_path = Path(path).parent/('selected_'+uuid.uuid4().hex+'.json')
            with selected_path.open('x', encoding='utf-8') as handle:
                json.dump(recipe, handle, indent=2)
            self.applying_recipe = True
            try:
                self.mode.setCurrentIndex(['signature', 'geometry', 'geophysics'].index(candidate['mode']))
                self.filter.setCurrentText(candidate['filter'])
                self.feature.setCurrentText(candidate['feature'])
                for key, spin in self.parameters.items():
                    spin.setValue(candidate['params'][key])
                self.manual.setChecked(False)
                self.recipe_path = selected_path
            finally:
                self.applying_recipe = False
            self.review_dialog.close()
            self.status.setText('Selected '+candidate_id+'. Recipe saved. Extract will apply this choice to the full input.')
        except Exception as error:
            self.status.setText(str(error))
