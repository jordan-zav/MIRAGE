"""GeoPackage writer shared by both routes; prefer host GDAL inside QGIS."""
from pathlib import Path
import json

import numpy as np


def write_result(result, destination, crs, *, raster=None, transform=None):
    destination = Path(destination)
    if destination.suffix.lower() != '.gpkg':
        raise ValueError('The vector destination must end in .gpkg.')
    for path in (destination, raster):
        if path is not None and Path(path).exists():
            raise FileExistsError(path)
    if raster is not None and transform is None:
        raise ValueError('A raster transform is required.')
    schema = {'route': 'str', 'method': 'str', 'length': 'float', 'azimuth': 'float',
              'strength': 'float', 'scale': 'float', 'height': 'float'}
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Keep a permanent reservation record: interrupted writes are inspectable.
    reservation = destination.with_suffix('.mirage-reservation.json')
    with reservation.open('x', encoding='utf-8') as handle:
        json.dump({'status': 'writing', 'output': str(destination)}, handle)
    if destination.exists():
        raise FileExistsError(destination)
    try:
        from osgeo import gdal, ogr, osr
    except ImportError:
        try:
            import fiona
            from shapely.geometry import mapping
        except ImportError as exc:
            raise RuntimeError('Install mirage-lineaments[io] outside QGIS.') from exc
        with fiona.open(destination, 'w', driver='GPKG', layer='lineaments',
                        crs=crs, schema={'geometry': 'LineString', 'properties': schema}) as layer:
            for line, record in zip(result.lines, result.attributes):
                layer.write({'geometry': mapping(line), 'properties': record})
        if result.points:
            with fiona.open(destination, 'w', driver='GPKG', layer='worms', crs=crs,
                            schema={'geometry': 'Point', 'properties': {'height': 'float', 'amplitude': 'float'}}) as layer:
                for x, y, height, amplitude in result.points:
                    layer.write({'geometry': {'type': 'Point', 'coordinates': (x, y)},
                                 'properties': {'height': height, 'amplitude': amplitude}})
        if raster is not None:
            import rasterio
            from affine import Affine
            bands = 1 if result.azimuth is None else 2
            with rasterio.open(raster, 'w', driver='GTiff', height=result.strength.shape[0],
                               width=result.strength.shape[1], count=bands, dtype='float32',
                               crs=crs, transform=Affine(*tuple(transform)[:6])) as dataset:
                if bands == 1:
                    dataset.write(result.strength.astype('float32'), 1)
                else:
                    dataset.write(result.azimuth.astype('float32'), 1)
                    dataset.write(result.strength.astype('float32'), 2)
    else:
        reference = osr.SpatialReference()
        if reference.SetFromUserInput(str(crs)) != 0:
            raise ValueError('Invalid output CRS.')
        reference.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        dataset = ogr.GetDriverByName('GPKG').CreateDataSource(str(destination))
        if dataset is None:
            raise OSError('Could not create GeoPackage.')
        layer = dataset.CreateLayer('lineaments', reference, ogr.wkbLineString)
        for name, kind in schema.items():
            layer.CreateField(ogr.FieldDefn(name, ogr.OFTString if kind == 'str' else ogr.OFTReal))
        for line, record in zip(result.lines, result.attributes):
            feature = ogr.Feature(layer.GetLayerDefn())
            feature.SetGeometry(ogr.CreateGeometryFromWkb(line.wkb))
            for key, value in record.items():
                if value is not None:
                    feature.SetField(key, value)
            if layer.CreateFeature(feature) != 0:
                raise OSError('Could not write lineament.')
        if result.points:
            points = dataset.CreateLayer('worms', reference, ogr.wkbPoint)
            for name in ('height', 'amplitude'):
                points.CreateField(ogr.FieldDefn(name, ogr.OFTReal))
            for x, y, height, amplitude in result.points:
                feature = ogr.Feature(points.GetLayerDefn())
                geometry = ogr.Geometry(ogr.wkbPoint)
                geometry.AddPoint_2D(x, y)
                feature.SetGeometry(geometry)
                feature.SetField('height', height)
                feature.SetField('amplitude', amplitude)
                if points.CreateFeature(feature) != 0:
                    raise OSError('Could not write worm vertex.')
        dataset = None
        if raster is not None:
            ny, nx = result.strength.shape
            array = result.strength if result.azimuth is None else np.stack([result.azimuth, result.strength])
            bands = 1 if array.ndim == 2 else 2
            dataset = gdal.GetDriverByName('GTiff').Create(str(raster), nx, ny, bands, gdal.GDT_Float32)
            a, b, c, d, e, f = tuple(transform)[:6]
            dataset.SetGeoTransform((c, a, b, f, d, e))
            dataset.SetProjection(reference.ExportToWkt())
            for index in range(bands):
                dataset.GetRasterBand(index+1).WriteArray(array if bands == 1 else array[index])
            dataset = None
    reservation.write_text(json.dumps({'status': 'complete', 'output': str(destination)}), encoding='utf-8')
    return str(destination)
