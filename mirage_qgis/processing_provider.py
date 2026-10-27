"""QGIS algorithms delegate to the same core as standalone execution."""

import json
from pathlib import Path

from qgis.core import (
    QgsProcessingAlgorithm, QgsProcessingException, QgsProcessingOutputFile,
    QgsProcessingOutputVectorLayer, QgsProcessingParameterEnum,
    QgsProcessingParameterFolderDestination, QgsProcessingParameterNumber,
    QgsProcessingParameterRasterLayer, QgsProcessingProvider, QgsProcessingParameterFile,
)

from .dependencies import require_runtime
from .adaptive_processing import RecommendParameters, PreviewCandidates


class ExtractSignatures(QgsProcessingAlgorithm):
    def name(self):
        return 'extract_signatures'

    def displayName(self):
        return 'Extract raster signatures'

    def group(self):
        return 'MIRAGE'

    def groupId(self):
        return 'mirage'

    def createInstance(self):
        return ExtractSignatures()

    def shortHelpString(self):
        return ('Extract connected morphology into a GeoPackage and Shapefile. '
                'Use a fresh output folder. Geophysical mode requires a complete, '
                'north-up square grid in a projected CRS with metre units. '
                'Results need independent geological or archaeological review.')

    def initAlgorithm(self, configuration=None):
        self.addParameter(QgsProcessingParameterRasterLayer('INPUT', 'Input raster'))
        self.addParameter(QgsProcessingParameterFile('RECIPE', 'Selected adaptive recipe (optional)', extension='json', optional=True))
        self.addParameter(QgsProcessingParameterEnum('MODE', 'Interpretation goal',
            options=['Geological signature', 'Archaeological geometry', 'Geophysics'], defaultValue=0))
        for name, label, default, minimum, maximum, integer in [
            ('RADI', 'Smoothing radius (pixels)', 3, 0, 100, True),
            ('GTHR', 'Edge threshold', 66, 0, 100, True),
            ('LTHR', 'Minimum length (pixels)', 28, 2, 100000, True),
            ('FTHR', 'Simplification tolerance (source CRS units)', 4, 0, 100000, False),
            ('ATHR', 'Linking angle (degrees)', 16, 0, 180, False),
            ('DTHR', 'Linking distance (pixels)', 12, 0, 100000, False),
            ('MAX_PIXELS', 'Maximum input pixels', 16000000, 9, 1000000000, True),
        ]:
            kind = QgsProcessingParameterNumber.Integer if integer else QgsProcessingParameterNumber.Double
            self.addParameter(QgsProcessingParameterNumber(name, label, type=kind,
                defaultValue=default, minValue=minimum, maxValue=maximum))
        self.addParameter(QgsProcessingParameterEnum('FILTER', 'Geophysical filter',
            options=['TDR', 'AS', 'VDR1', 'VDR2', 'THDR', 'NONE'], defaultValue=0))
        self.addParameter(QgsProcessingParameterEnum('FEATURE', 'Geophysical feature',
            options=['trough', 'ridge'], defaultValue=0))
        self.addParameter(QgsProcessingParameterFolderDestination('OUTPUT', 'New output folder'))
        self.addOutput(QgsProcessingOutputVectorLayer('LINEAMENTS', 'MIRAGE lineaments'))
        self.addOutput(QgsProcessingOutputFile('REPORT', 'Run report'))

    def processAlgorithm(self, parameters, context, feedback):
        try:
            require_runtime()
            from .core.pipeline import run_extraction_job
            layer = self.parameterAsRasterLayer(parameters, 'INPUT', context)
            if layer is None or not layer.isValid() or layer.providerType() != 'gdal':
                raise ValueError('Choose a valid file raster supported by GDAL, not a web service.')
            arguments = {name.lower(): self.parameterAsDouble(parameters, name, context)
                         for name in ('RADI', 'GTHR', 'LTHR', 'FTHR', 'ATHR', 'DTHR')}
            for name in ('radi', 'gthr', 'lthr'):
                arguments[name] = int(arguments[name])
            mode = ['signature', 'geometry', 'geophysics'][self.parameterAsEnum(parameters, 'MODE', context)]
            filter_name = ['TDR', 'AS', 'VDR1', 'VDR2', 'THDR', 'NONE'][self.parameterAsEnum(parameters, 'FILTER', context)]
            feature = ['trough', 'ridge'][self.parameterAsEnum(parameters, 'FEATURE', context)]
            recipe = None
            if parameters.get('RECIPE'):
                from .core.adaptive import validate_recipe
                recipe = json.loads(Path(self.parameterAsFile(parameters, 'RECIPE', context)).read_text(encoding='utf-8'))
                candidate = validate_recipe(recipe, layer.source())
                arguments = {k.lower():v for k, v in candidate['params'].items()}
                mode, filter_name, feature = candidate['mode'], candidate['filter'], candidate['feature']
            feedback.pushInfo('MIRAGE processes morphology; its outputs do not certify interpretation.')
            feedback.setProgress(5)
            summary = run_extraction_job(geotiff=layer.source(),
                out_dir=self.parameterAsString(parameters, 'OUTPUT', context),
                extraction_mode=mode, geophys_filters=filter_name,
                geophys_extract_type=feature, workers=1,
                max_pixels=self.parameterAsInt(parameters, 'MAX_PIXELS', context),
                cancelled=feedback.isCanceled, adaptive_recipe=recipe, **arguments)
            feedback.setProgress(100)
            return {'LINEAMENTS': summary['outputs']['geopackage'],
                    'REPORT': summary['outputs']['report'], 'OUTPUT': summary['output_dir']}
        except Exception as error:
            raise QgsProcessingException(str(error)) from error


class MirageProvider(QgsProcessingProvider):
    def id(self):
        return 'mirage'

    def name(self):
        return 'MIRAGE'

    def loadAlgorithms(self):
        self.addAlgorithm(ExtractSignatures())
        self.addAlgorithm(RecommendParameters())
        self.addAlgorithm(PreviewCandidates())
