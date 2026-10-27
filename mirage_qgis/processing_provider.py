"""QGIS algorithms delegate to the same core as standalone execution."""

import json
from pathlib import Path

from qgis.core import (
    QgsProcessingAlgorithm, QgsProcessingException, QgsProcessingOutputFile,
    QgsProcessingOutputVectorLayer, QgsProcessingParameterEnum,
    QgsProcessingParameterFolderDestination, QgsProcessingParameterNumber,
    QgsProcessingParameterRasterLayer, QgsProcessingProvider,
)

from .dependencies import require_runtime


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
            feedback.pushInfo('MIRAGE processes morphology; its outputs do not certify interpretation.')
            feedback.setProgress(5)
            summary = run_extraction_job(geotiff=layer.source(),
                out_dir=self.parameterAsString(parameters, 'OUTPUT', context),
                extraction_mode=mode, geophys_filters=filter_name,
                geophys_extract_type=feature, workers=1,
                max_pixels=self.parameterAsInt(parameters, 'MAX_PIXELS', context),
                cancelled=feedback.isCanceled, **arguments)
            feedback.setProgress(100)
            return {'LINEAMENTS': summary['outputs']['geopackage'],
                    'REPORT': summary['outputs']['report'], 'OUTPUT': summary['output_dir']}
        except Exception as error:
            raise QgsProcessingException(str(error)) from error


class RecommendParameters(QgsProcessingAlgorithm):
    def name(self):
        return 'recommend_parameters'

    def displayName(self):
        return 'Recommend starting parameters'

    def group(self):
        return 'MIRAGE'

    def groupId(self):
        return 'mirage'

    def createInstance(self):
        return RecommendParameters()

    def shortHelpString(self):
        return 'Sample a raster for heuristic starting parameters. Scores are not geological probabilities.'

    def initAlgorithm(self, configuration=None):
        self.addParameter(QgsProcessingParameterRasterLayer('INPUT', 'Input raster'))
        from qgis.core import QgsProcessingParameterFileDestination
        self.addParameter(QgsProcessingParameterFileDestination('OUTPUT', 'Recommendations', fileFilter='JSON (*.json)'))

    def processAlgorithm(self, parameters, context, feedback):
        try:
            require_runtime()
            import numpy as np
            from osgeo import gdal
            from .core.ai.parameter_advisor import recommend_settings
            layer = self.parameterAsRasterLayer(parameters, 'INPUT', context)
            dataset = gdal.Open(layer.source())
            if dataset is None:
                raise ValueError('Cannot open the selected raster with GDAL.')
            factor = min(1.0, 512/max(dataset.RasterXSize, dataset.RasterYSize))
            width = max(3, int(dataset.RasterXSize*factor))
            height = max(3, int(dataset.RasterYSize*factor))
            bands = [dataset.GetRasterBand(i).ReadAsArray(buf_xsize=width, buf_ysize=height)
                     for i in range(1, min(dataset.RasterCount, 3)+1)]
            values = np.asarray(bands, dtype=float)
            if len(bands) == 1:
                values = values[0]
            mask = dataset.GetRasterBand(1).GetMaskBand().ReadAsArray(buf_xsize=width, buf_ysize=height) > 0
            if not mask.any():
                raise ValueError('No valid raster pixels available.')
            values[..., ~mask] = np.nanmedian(values[..., mask])
            result = recommend_settings(values, abs(dataset.GetGeoTransform()[1])/factor, compute_mode='cpu')
            result['method'] = 'heuristic starting parameters, not calibrated probabilities'
            path = Path(self.parameterAsFileOutput(parameters, 'OUTPUT', context))
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('x', encoding='utf-8') as handle:
                json.dump(result, handle, ensure_ascii=False, indent=2)
            return {'OUTPUT': str(path)}
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
