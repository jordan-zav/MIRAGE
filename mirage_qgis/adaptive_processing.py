"""Physical-scale recommendations and native-window comparative previews."""
import hashlib
import json
from pathlib import Path

import numpy as np
from osgeo import gdal
from qgis.core import (QgsProcessingAlgorithm, QgsProcessingException, QgsProcessingOutputFile,
    QgsProcessingParameterEnum, QgsProcessingParameterNumber,
    QgsProcessingParameterFileDestination, QgsProcessingParameterFolderDestination,
    QgsProcessingParameterRasterLayer, QgsProcessingParameterPoint)

from .dependencies import require_runtime

KINDS = ['unknown', 'terrain', 'magnetic', 'gravity', 'optical']
GOALS = ['continuity', 'detail', 'geometry']


def add_scale_parameters(algorithm):
    algorithm.addParameter(QgsProcessingParameterRasterLayer('INPUT', 'Input raster'))
    algorithm.addParameter(QgsProcessingParameterEnum('KIND', 'Declared input type',
        options=['Unknown / generic edges', 'Terrain / hillshade', 'Magnetic field', 'Gravity field', 'Optical imagery'], defaultValue=0))
    algorithm.addParameter(QgsProcessingParameterEnum('GOAL', 'Extraction goal (not origin)',
        options=['Structural continuity', 'More detail', 'Preserve geometry (explicit selection)'], defaultValue=0))
    for name, label, default, minimum in [
        ('MIN_LENGTH_M', 'Minimum length (m)', 280, .001),
        ('SMOOTHING_M', 'Smoothing radius (m)', 30, 0),
        ('GAP_M', 'Maximum linking gap (m)', 120, 0),
        ('SIMPLIFY_M', 'Simplification (m)', 4, 0)]:
        algorithm.addParameter(QgsProcessingParameterNumber(name, label,
            type=QgsProcessingParameterNumber.Double, defaultValue=default, minValue=minimum, maxValue=100000000))


def declared_options(algorithm, parameters, context):
    return dict(input_kind=KINDS[algorithm.parameterAsEnum(parameters, 'KIND', context)],
                goal=GOALS[algorithm.parameterAsEnum(parameters, 'GOAL', context)],
                minimum_length_m=algorithm.parameterAsDouble(parameters, 'MIN_LENGTH_M', context),
                smoothing_m=algorithm.parameterAsDouble(parameters, 'SMOOTHING_M', context),
                linking_gap_m=algorithm.parameterAsDouble(parameters, 'GAP_M', context),
                simplification_m=algorithm.parameterAsDouble(parameters, 'SIMPLIFY_M', context))


def raster_context(layer):
    from .core.adaptive import metric_resolution
    if layer is None or not layer.isValid() or layer.providerType() != 'gdal':
        raise ValueError('Choose a valid local GDAL raster.')
    dataset = gdal.Open(layer.source(), gdal.GA_ReadOnly)
    if dataset is None or dataset.RasterCount not in (1, 3, 4):
        raise ValueError('Use a single-band, RGB or RGBA file raster.')
    if dataset.RasterCount == 4 and dataset.GetRasterBand(4).GetColorInterpretation() != gdal.GCI_AlphaBand:
        raise ValueError('Fourth band must be explicitly marked as alpha.')
    gt = dataset.GetGeoTransform()
    pixel = metric_resolution(dataset.GetProjection(), (gt[1], gt[2], gt[0], gt[4], gt[5], gt[3]))
    if min(dataset.RasterXSize, dataset.RasterYSize) < 3:
        raise ValueError('The input must be at least 3 by 3 pixels.')
    return dataset, pixel


def sample_values(dataset, *, window=None, maximum=512):
    x, y, width, height = window or (0, 0, dataset.RasterXSize, dataset.RasterYSize)
    factor = min(1., maximum/max(width, height))
    out_w, out_h = max(1, round(width*factor)), max(1, round(height*factor))
    if min(out_w, out_h) < 3:
        raise ValueError('Sample is too narrow. Choose a wider raster/window.')
    count = min(3, dataset.RasterCount)
    values, masks = [], []
    for i in range(1, count+1):
        band = dataset.GetRasterBand(i)
        arr = band.ReadAsArray(x, y, width, height, buf_xsize=out_w, buf_ysize=out_h).astype(float)
        valid = band.GetMaskBand().ReadAsArray(x, y, width, height, buf_xsize=out_w, buf_ysize=out_h) > 0
        values.append(arr)
        masks.append(valid & np.isfinite(arr))
    if dataset.RasterCount == 4:
        masks.append(dataset.GetRasterBand(4).ReadAsArray(x, y, width, height, buf_xsize=out_w, buf_ysize=out_h) > 0)
    mask = np.all(masks, axis=0)
    if not mask.any():
        raise ValueError('No valid pixels in this sample. Pan to a valid area and preview again.')
    values = np.stack(values)
    values[:, ~mask] = np.nan
    return values if count > 1 else values[0], mask, width/out_w


def make_plan(layer, options, *, window=None):
    from .core.adaptive import recommend_adaptive, source_identity
    dataset, pixel = raster_context(layer)
    values, mask, factor = sample_values(dataset, window=window)
    plan = recommend_adaptive(values, pixel, analysis_pixel_size_m=pixel*factor, **options)
    plan['source'] = source_identity(layer.source())
    plan['source_grid'] = dict(width=dataset.RasterXSize, height=dataset.RasterYSize,
                               transform=list(dataset.GetGeoTransform()), crs=dataset.GetProjection())
    plan['sample'] = dict(window=window, valid_fraction=float(mask.mean()), downsampling_factor=factor)
    # Compatibility keys for callers of the original recommendations tool.
    plan['params'] = plan['candidates'][0]['params']
    plan['profile'] = 'Adaptive balanced'
    return plan


def render_overlay(source, vector, destination):
    from osgeo import ogr
    from qgis.PyQt.QtCore import QPointF
    from qgis.PyQt.QtGui import QColor, QImage, QPainter, QPen, QPolygonF
    dataset = gdal.Open(str(source))
    values, valid, _ = sample_values(dataset)
    if values.ndim == 2:
        values = np.repeat(values[None], 3, axis=0)
    lo = np.nanpercentile(values, 2, axis=(1, 2))[:, None, None]
    hi = np.nanpercentile(values, 98, axis=(1, 2))[:, None, None]
    rgb = np.nan_to_num(np.clip((values-lo)/(hi-lo+1e-12), 0, 1)*255).astype('uint8')
    rgb[:, ~valid] = 70
    rgb = np.ascontiguousarray(rgb.transpose(1, 2, 0))
    image = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format_RGB888).copy()
    if vector:
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor('#ff38ce'), 1.5))
        inverse = gdal.InvGeoTransform(dataset.GetGeoTransform())
        datasource = ogr.Open(str(vector))
        try:
            for feature in datasource.GetLayerByName('lineaments'):
                geometry = feature.GetGeometryRef()
                lines = [geometry] if geometry.GetGeometryType() in (ogr.wkbLineString, ogr.wkbLineString25D) else list(geometry)
                for line in lines:
                    points = [QPointF(*gdal.ApplyGeoTransform(inverse, point[0], point[1])) for point in line.GetPoints()]
                    painter.drawPolyline(QPolygonF(points))
        finally:
            painter.end()
            datasource = None
    if not image.save(str(destination)):
        raise ValueError('Could not write preview PNG.')


class AdaptiveBase(QgsProcessingAlgorithm):
    def group(self):
        return 'MIRAGE'

    def groupId(self):
        return 'mirage'


class RecommendParameters(AdaptiveBase):
    def name(self):
        return 'recommend_parameters'

    def displayName(self):
        return 'Recommend physical-scale candidates'

    def createInstance(self):
        return RecommendParameters()

    def shortHelpString(self):
        return 'Declare input type and scale in metres. Texture adjusts thresholds only; it cannot identify origin. Square metric pixels required.'

    def initAlgorithm(self, configuration=None):
        add_scale_parameters(self)
        self.addParameter(QgsProcessingParameterFileDestination('OUTPUT', 'Candidate plan', fileFilter='JSON (*.json)'))

    def processAlgorithm(self, parameters, context, feedback):
        try:
            require_runtime()
            layer = self.parameterAsRasterLayer(parameters, 'INPUT', context)
            plan = make_plan(layer, declared_options(self, parameters, context))
            output = Path(self.parameterAsFileOutput(parameters, 'OUTPUT', context))
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open('x', encoding='utf-8') as handle:
                json.dump(plan, handle, indent=2)
            return {'OUTPUT':str(output)}
        except Exception as error:
            raise QgsProcessingException(str(error)) from error


class PreviewCandidates(AdaptiveBase):
    def name(self):
        return 'preview_candidates'

    def displayName(self):
        return 'Compare three candidates on a native window'

    def createInstance(self):
        return PreviewCandidates()

    def shortHelpString(self):
        return ('Extract three variants on the same native-resolution window, at the optional source-CRS centre point. '
                'Review PNG overlays and counts; select a recipe manually. The crop is retained. '
                'FFT windows must be complete. Preview boundaries can differ from a full extraction.')

    def initAlgorithm(self, configuration=None):
        add_scale_parameters(self)
        self.addParameter(QgsProcessingParameterPoint('CENTER', 'Preview centre (source CRS)', optional=True))
        self.addParameter(QgsProcessingParameterNumber('WINDOW_PIXELS', 'Window side (native pixels)',
            type=QgsProcessingParameterNumber.Integer, defaultValue=256, minValue=32, maxValue=512))
        self.addParameter(QgsProcessingParameterFolderDestination('OUTPUT', 'New preview folder'))
        self.addOutput(QgsProcessingOutputFile('PLAN', 'Candidate plan with preview results'))

    def processAlgorithm(self, parameters, context, feedback):
        output = None
        try:
            require_runtime()
            from .core.pipeline import run_extraction_job
            from .core.adaptive import select_recipe, source_identity
            layer = self.parameterAsRasterLayer(parameters, 'INPUT', context)
            dataset, pixel = raster_context(layer)
            side = self.parameterAsInt(parameters, 'WINDOW_PIXELS', context)
            width, height = min(side, dataset.RasterXSize), min(side, dataset.RasterYSize)
            cx, cy = dataset.RasterXSize/2, dataset.RasterYSize/2
            if parameters.get('CENTER') is not None and str(parameters['CENTER']).strip():
                point = self.parameterAsPoint(parameters, 'CENTER', context, layer.crs())
                cx, cy = gdal.ApplyGeoTransform(gdal.InvGeoTransform(dataset.GetGeoTransform()), point.x(), point.y())
                if not (0 <= cx < dataset.RasterXSize and 0 <= cy < dataset.RasterYSize):
                    raise ValueError('Map centre is outside the raster. Pan over the raster and try again.')
            window = [max(0, min(dataset.RasterXSize-width, int(cx-width/2))),
                      max(0, min(dataset.RasterYSize-height, int(cy-height/2))), width, height]
            options = declared_options(self, parameters, context)
            plan = make_plan(layer, options, window=window)
            if plan['candidates'][0]['mode'] == 'geophysics':
                from .core.raster_backend import GDALSource, validate_geophysics_grid
                with GDALSource(layer.source()) as source:
                    validate_geophysics_grid(source)
                _, mask, _ = sample_values(dataset, window=window)
                if not mask.all():
                    raise ValueError('Geophysical preview needs a complete valid window. Pan away from gaps or repair explicitly.')
            output = Path(self.parameterAsString(parameters, 'OUTPUT', context))
            output.mkdir(parents=True, exist_ok=False)
            crop = output/'preview_input.tif'
            cropped = gdal.Translate(str(crop), dataset, srcWin=window, creationOptions=['COMPRESS=DEFLATE'])
            if cropped is None:
                raise ValueError('Could not create native preview window.')
            cropped = None
            plan['preview'] = {'window':window, 'crop_sha256':hashlib.sha256(crop.read_bytes()).hexdigest(),
                               'background':'Input raster; geophysical traces may derive from a transformed field.'}
            render_overlay(crop, None, output/'original.png')
            plan_path = output/'candidates.json'
            plan_path.write_text(json.dumps(plan, indent=2), encoding='utf-8')
            for i, candidate in enumerate(plan['candidates']):
                if feedback.isCanceled():
                    raise InterruptedError('Preview cancelled.')
                feedback.setProgress(i*100/3)
                crop_recipe = select_recipe(plan, candidate['id'])
                crop_recipe['source'] = source_identity(crop)
                summary = run_extraction_job(geotiff=str(crop), out_dir=str(output/candidate['id']),
                    extraction_mode=candidate['mode'], geophys_filters=candidate['filter'],
                    geophys_extract_type=candidate['feature'], workers=1, cancelled=feedback.isCanceled, adaptive_recipe=crop_recipe,
                    **{k.lower():v for k, v in candidate['params'].items()})
                candidate['preview_summary'] = summary['lineaments']
                candidate['preview_png'] = candidate['id']+'.png'
                render_overlay(crop, summary['outputs']['geopackage'], output/candidate['preview_png'])
            plan['preview']['status'] = 'complete'
            plan_path.write_text(json.dumps(plan, indent=2), encoding='utf-8')
            feedback.setProgress(100)
            return {'OUTPUT':str(output), 'PLAN':str(plan_path)}
        except Exception as error:
            if output is not None and output.is_dir() and 'plan_path' in locals():
                plan['preview']['status'] = 'cancelled' if feedback.isCanceled() else 'failed'
                plan['preview']['error'] = str(error)
                plan_path.write_text(json.dumps(plan, indent=2), encoding='utf-8')
            raise QgsProcessingException(str(error)) from error
