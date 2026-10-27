"""Raster/vector I/O using host GDAL in QGIS or Rasterio/Fiona standalone.

Numerical routines share this interface; no QGIS imports enter the core.
"""

from enum import IntEnum
from typing import NamedTuple

import numpy as np
from pyproj import CRS
from shapely.geometry import LineString, shape
from shapely.ops import unary_union


class ColorInterp(IntEnum):
    red = 3
    green = 4
    blue = 5
    alpha = 6


class Transform(NamedTuple):
    a: float
    b: float
    c: float
    d: float
    e: float
    f: float


class GDALSource:
    def __init__(self, path):
        from osgeo import gdal

        self.dataset = gdal.Open(str(path), gdal.GA_ReadOnly)
        if self.dataset is None:
            raise ValueError(f"Cannot open raster: {path}")
        self.count = self.dataset.RasterCount
        self.width = self.dataset.RasterXSize
        self.height = self.dataset.RasterYSize
        gt = self.dataset.GetGeoTransform()
        self.transform = Transform(gt[1], gt[2], gt[0], gt[4], gt[5], gt[3])
        wkt = self.dataset.GetProjection()
        self.crs = CRS.from_wkt(wkt) if wkt else None
        self.colorinterp = tuple(self.dataset.GetRasterBand(i).GetColorInterpretation()
                                 for i in range(1, self.count+1))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.dataset = None

    def read(self, indexes=None, masked=False):
        single = isinstance(indexes, int)
        indexes = [indexes] if single else list(indexes or range(1, self.count+1))
        values = np.stack([self.dataset.GetRasterBand(i).ReadAsArray() for i in indexes])
        if masked:
            masks = np.stack([self.dataset.GetRasterBand(i).GetMaskBand().ReadAsArray() == 0
                              for i in indexes])
            values = np.ma.array(values, mask=masks)
        return values[0] if single else values


def open_raster(path):
    try:
        from osgeo import gdal  # noqa: F401
    except ImportError:
        import rasterio

        return rasterio.open(path)
    return GDALSource(path)


def inspect_raster(path, max_pixels=16_000_000):
    with open_raster(path) as source:
        if source.count not in (1, 3, 4):
            raise ValueError("Use a single-band, RGB or RGBA raster.")
        if source.count == 4 and int(source.colorinterp[3]) != ColorInterp.alpha:
            raise ValueError("A fourth band must be explicitly marked as alpha.")
        if source.crs is None:
            raise ValueError("The raster has no CRS. Define the correct source CRS before processing.")
        t = source.transform
        if not np.isfinite(tuple(t)[:6]).all() or abs(t.a*t.e-t.b*t.d) < 1e-20:
            raise ValueError("The raster transform is singular or non-finite.")
        if min(source.width, source.height) < 3:
            raise ValueError("The raster must be at least 3 by 3 pixels.")
        if source.width*source.height > max_pixels:
            raise ValueError(f"Raster exceeds the {max_pixels:,}-pixel limit. Crop it or explicitly raise max_pixels.")
        return {"width": source.width, "height": source.height, "bands": source.count,
                "crs": str(source.crs), "transform": [t.a, t.b, t.c, t.d, t.e, t.f]}


def validate_geophysics_grid(source):
    crs = CRS.from_user_input(source.crs)
    t = source.transform
    if not crs.is_projected:
        raise ValueError("Geophysics requires a projected metric CRS; reproject with GDAL Warp first.")
    factors = [axis.unit_conversion_factor for axis in crs.axis_info[:2]]
    if len(factors) != 2 or not np.allclose(factors, [1, 1]):
        raise ValueError("Geophysics requires horizontal units in metres.")
    if t.a <= 0 or t.e >= 0 or abs(t.b) > 1e-12 or abs(t.d) > 1e-12:
        raise ValueError("Geophysics requires a north-up grid without rotation or shear.")
    if not np.isclose(t.a, -t.e, rtol=1e-6):
        raise ValueError("Geophysics currently requires square pixels; warp to a square grid first.")


def valid_region(mask, transform):
    """Polygonize valid pixels with their original affine grid."""
    try:
        from osgeo import gdal, ogr
    except ImportError:
        from rasterio.features import shapes
        from rasterio.transform import Affine

        polygons = [shape(geometry) for geometry, _ in shapes(
            mask.astype('uint8'), mask=mask, transform=Affine(*transform))]
    else:
        from shapely import wkb

        memory = gdal.GetDriverByName('MEM').Create('', mask.shape[1], mask.shape[0], 1, gdal.GDT_Byte)
        memory.SetGeoTransform((transform.c, transform.a, transform.b, transform.f, transform.d, transform.e))
        band = memory.GetRasterBand(1)
        band.WriteArray(mask.astype('uint8'))
        datasource = ogr.GetDriverByName('Memory').CreateDataSource('valid')
        layer = datasource.CreateLayer('valid', geom_type=ogr.wkbPolygon)
        gdal.Polygonize(band, band, layer, -1, [], callback=None)
        polygons = [wkb.loads(bytes(feature.GetGeometryRef().ExportToWkb())) for feature in layer]
    return unary_union(polygons)


def clipped_lines(lines, mask, transform):
    if mask.all():
        return lines
    region = valid_region(mask, transform)
    result = []
    for line in lines:
        intersection = line.intersection(region)
        parts = list(intersection.geoms) if hasattr(intersection, 'geoms') else [intersection]
        result.extend(part for part in parts if isinstance(part, LineString) and not part.is_empty)
    return result


def write_vectors(out_base, records, lines, crs):
    prototype = records[0] if records else {
        'id': 0, 'mode': '', 'pix_len': 0., 'map_len': 0., 'chord': 0., 'straight': 0., 'elong': 0.,
        'angle': 0., 'nverts': 0, 'pixel_sz': 0., 'radii': 0, 'gthr': 0, 'lthr': 0,
        'fthr': 0., 'athr': 0., 'dthr': 0., 'gp_filt': '', 'gp_type': '', 'gp_stride': 0,
    }
    try:
        from osgeo import ogr, osr
    except ImportError:
        import geopandas as gpd

        if not records:
            import fiona
            properties = {key: 'str' if isinstance(value, str) else 'int' if isinstance(value, int) else 'float'
                          for key, value in prototype.items()}
            for driver, suffix in [('ESRI Shapefile', '.shp'), ('GPKG', '.gpkg')]:
                with fiona.open(str(out_base)+suffix, 'w', driver=driver,
                                schema={'geometry': 'LineString', 'properties': properties},
                                crs_wkt=CRS.from_user_input(crs).to_wkt(), layer='lineaments'):
                    pass
            return
        frame = gpd.GeoDataFrame(records, geometry=lines, crs=crs)
        frame.to_file(str(out_base)+'.shp')
        frame.to_file(str(out_base)+'.gpkg', layer='lineaments', driver='GPKG')
        return
    reference = osr.SpatialReference()
    reference.ImportFromWkt(CRS.from_user_input(crs).to_wkt())
    reference.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    for driver, suffix in [('ESRI Shapefile', '.shp'), ('GPKG', '.gpkg')]:
        dataset = ogr.GetDriverByName(driver).CreateDataSource(str(out_base)+suffix)
        layer = dataset.CreateLayer('lineaments', reference, ogr.wkbLineString)
        for key, value in prototype.items():
            kind = ogr.OFTInteger64 if isinstance(value, (int, np.integer)) else ogr.OFTReal
            if isinstance(value, str):
                kind = ogr.OFTString
            field = ogr.FieldDefn(key, kind)
            if kind == ogr.OFTString:
                field.SetWidth(200)
            layer.CreateField(field)
        for record, line in zip(records, lines):
            feature = ogr.Feature(layer.GetLayerDefn())
            for key, value in record.items():
                feature.SetField(key, value.item() if isinstance(value, np.generic) else value)
            feature.SetGeometry(ogr.CreateGeometryFromWkb(line.wkb))
            if layer.CreateFeature(feature) != 0:
                raise OSError(f"Could not write vector feature to {out_base}{suffix}")
        dataset = None


def summarize_vectors(path):
    try:
        from osgeo import ogr
    except ImportError:
        import geopandas as gpd

        frame = gpd.read_file(path)
        crs = CRS.from_user_input(frame.crs)
        lines = list(frame.geometry)
    else:
        from shapely import wkb

        dataset = ogr.Open(str(path))
        layer = dataset.GetLayer(0)
        crs = CRS.from_wkt(layer.GetSpatialRef().ExportToWkt())
        lines = [wkb.loads(bytes(feature.GetGeometryRef().ExportToWkb())) for feature in layer]
    if not lines:
        return {"count": 0, "total_length": 0, "mean_length": 0, "min_length": 0,
                "max_length": 0, "units": "N/A", "crs": str(crs)}
    if crs.is_projected:
        factor = crs.axis_info[0].unit_conversion_factor
        lengths = np.array([line.length*factor for line in lines])
        units = 'meters'
    else:
        geod = crs.get_geod()
        lengths = np.array([abs(geod.geometry_length(line)) for line in lines])
        units = 'meters (geodesic)'
    return {"count": len(lines), "total_length": float(lengths.sum()),
            "mean_length": float(lengths.mean()), "max_length": float(lengths.max()),
            "min_length": float(lengths.min()), "units": units, "crs": str(crs)}
