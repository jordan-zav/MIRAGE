"""Named scientific profiles, separate from historical display presets."""
import json
from pathlib import Path


def profiles():
    calibrated = json.loads(Path(__file__).with_name('geophysics_calibration.json').read_text(encoding='utf-8'))
    return {'geophysics': calibrated,
            'legacy-array': {'method': 'thdr', 'threshold': .2, 'scales_cells': [1, 2, 4], 'heights_cells': [0, 2, 4],
                             'description': 'Previous 1.3 development array defaults; not v1.2 file parity'},
            'legacy-v120': {'description': 'Unchanged v1.2 numerical file pipeline; file API/CLI/QGIS only'}}


def settings(profile, pixel_size):
    if profile == 'legacy-v120':
        raise ValueError('legacy-v120 requires the file pipeline; use legacy-array for previous array defaults.')
    config = profiles().get(profile)
    if config is None:
        raise ValueError('Unknown MIRAGE scientific profile: ' + str(profile))
    return dict(method=config['method'], threshold=config['threshold'],
                scales=tuple(pixel_size * value for value in config['scales_cells']),
                heights=tuple(pixel_size * value for value in config['heights_cells']))


def extract_file(geotiff, out_base, *, cancelled, minimum_length_m=None):
    """Use the calibrated array engine with the established file outputs."""
    import numpy as np

    from .engine import extract
    from .line_core import _read_grayscale_image
    from .raster_backend import open_raster, validate_geophysics_grid, write_vectors
    with open_raster(geotiff) as source:
        validate_geophysics_grid(source)
        image = _read_grayscale_image(source, rgb_conversion='average')
        if not np.isfinite(image).all():
            raise ValueError('Geophysical FFT filters require a complete grid; fill gaps explicitly before processing.')
        result = extract(image, pixel_size=source.transform.a, transform=source.transform,
                         profile='geophysics', cancelled=cancelled)
        crs = source.crs
    pairs = [(line, attributes) for line, attributes in zip(result.lines, result.attributes)
             if minimum_length_m is None or line.length >= minimum_length_m]
    records = [dict(id=index, mode='geophysics', map_len=line.length, angle=attributes['azimuth'],
                    method=attributes['method'], strength=attributes['strength'], profile='geophysics')
               for index, (line, attributes) in enumerate(pairs)]
    write_vectors(out_base, records, [line for line, _ in pairs], crs)
    return str(out_base) + '.shp'
