"""Declared input, physical scale and reproducible candidate recipes.

Texture controls edge strictness only; it never identifies a feature's origin.
"""
import json
import math
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

INPUT_KINDS = ('unknown', 'terrain', 'magnetic', 'gravity', 'optical')
GOALS = ('continuity', 'detail', 'geometry')
PARAMETERS = ('RADI', 'GTHR', 'LTHR', 'FTHR', 'ATHR', 'DTHR')


def metric_resolution(crs, transform):
    if __package__:
        from .raster_backend import reference_crs
    else:
        from raster_backend import reference_crs
    reference = reference_crs(crs)
    axes = reference.axis_info[:2]
    if not reference.is_projected or len(axes) != 2 or not all(
            np.isclose(axis.unit_conversion_factor, 1) for axis in axes):
        raise ValueError('Physical-scale recipes require a projected CRS in metres. Reproject first.')
    a, b, _, d, e, _ = tuple(transform)[:6]
    x, y = math.hypot(a, d), math.hypot(b, e)
    if not np.isfinite([a, b, d, e]).all() or min(x, y) <= 0 or not np.isclose(x, y, rtol=1e-6) or not np.isclose(a*b+d*e, 0, atol=x*y*1e-6):
        raise ValueError('Physical-scale recipes require square, orthogonal pixels. Warp first.')
    return x


def recommend_adaptive(image, pixel_size_m, *, input_kind='unknown', goal='continuity',
                       minimum_length_m=280, smoothing_m=30, linking_gap_m=120,
                       simplification_m=4, analysis_pixel_size_m=None):
    if input_kind not in INPUT_KINDS or goal not in GOALS:
        raise ValueError('Unknown declared input type or goal.')
    numbers = [pixel_size_m, minimum_length_m, smoothing_m, linking_gap_m, simplification_m]
    if not np.isfinite(numbers).all() or pixel_size_m <= 0 or minimum_length_m <= 0 or min(numbers[2:]) < 0:
        raise ValueError('Use finite positive resolution/length and nonnegative tolerances.')
    analysis_pixel_size_m = pixel_size_m if analysis_pixel_size_m is None else analysis_pixel_size_m
    if not np.isfinite(analysis_pixel_size_m) or analysis_pixel_size_m <= 0:
        raise ValueError('Analysis resolution must be finite and positive.')
    values = np.ma.asarray(image, dtype=float).filled(np.nan)
    if values.ndim == 3:
        values = np.mean(values[:3], axis=0)
    if values.ndim != 2 or min(values.shape) < 3:
        raise ValueError('Use a 2D raster sample or band-first RGB sample, at least 3 by 3.')
    finite = np.isfinite(values)
    if not finite.any():
        raise ValueError('No finite sample pixels.')
    lo, hi = np.percentile(values[finite], [2, 98])
    values = np.where(finite, values, np.median(values[finite]))
    normalized = np.clip((values-lo)/(hi-lo+1e-12), 0, 1)
    residual = float(np.std(normalized-gaussian_filter(normalized, 1)))
    # A bounded texture adjustment. Physical distances always use native pixels,
    # including when the statistics came from a downsampled analysis image.
    threshold = int(np.clip(56+residual*55+(4 if goal == 'continuity' else -4), 48, 72))
    mode = 'geometry' if goal == 'geometry' else 'geophysics' if input_kind in ('magnetic', 'gravity') else 'signature'
    warnings = ['Heuristic candidates; counts and texture do not establish geological or archaeological identity.']
    if input_kind == 'unknown':
        warnings.append('Input type unknown: no potential-field or archaeological origin is inferred.')
    if minimum_length_m < 2*pixel_size_m:
        warnings.append('Requested length is below two native pixels; the numerical minimum is two pixels.')
    if hi <= lo:
        warnings.append('The sample has no usable contrast; empty results are expected.')
    base_radius = max(0, int(round(smoothing_m/pixel_size_m)))
    if base_radius < 2:
        warnings.append("RADI is rounded to native pixels. Tonal edges retain a minimum sigma of 1.2 pixels; geophysics retains 0.5. Zero is not a no-filter mode.")
    length = max(2, int(math.ceil(minimum_length_m/pixel_size_m)))
    gap = linking_gap_m/pixel_size_m
    if base_radius > 100 or length > 100000 or gap > 100000 or simplification_m > 100000:
        raise ValueError('Scale exceeds supported parameter limits. Use a suitable resolution.')
    candidates = []
    for name, delta, radius in [('balanced', 0, base_radius),
                                ('conservative', 10, min(100, base_radius+1)),
                                ('detail', -10, max(0, base_radius-1))]:
        params = dict(RADI=radius, GTHR=int(np.clip(threshold+delta, 0, 100)),
                      LTHR=length, FTHR=float(simplification_m), ATHR=16, DTHR=float(gap))
        candidates.append({'id':name, 'params':params, 'mode':mode,
                           'filter':'TDR' if mode == 'geophysics' else 'NONE', 'feature':'trough',
                           'realized_scale_m':{'minimum_length':length*pixel_size_m,
                                               'smoothing_radius':radius*pixel_size_m,
                                               'linking_gap':linking_gap_m}})
    return {'schema':'mirage-adaptive-1', 'input_kind':input_kind, 'goal':goal,
            'native_pixel_size_m':float(pixel_size_m),
            'analysis_pixel_size_m':float(analysis_pixel_size_m),
            'requested_scale_m':dict(minimum_length=minimum_length_m, smoothing=smoothing_m,
                                     linking_gap=linking_gap_m, simplification=simplification_m),
            'sample_metrics':{'residual_std':residual, 'contrast_span':float(hi-lo)},
            'candidates':candidates, 'warnings':warnings,
            'method':'declared input and physical scale; heuristic texture adjustment; human selection'}


def source_identity(path):
    path = Path(path).resolve()
    stat = path.stat()
    return {'path':str(path), 'bytes':stat.st_size, 'mtime_ns':stat.st_mtime_ns}


def select_recipe(plan, candidate_id):
    candidate = next((c for c in plan['candidates'] if c['id'] == candidate_id), None)
    if candidate is None:
        raise ValueError('Unknown candidate.')
    # JSON round trip isolates the saved selection from later UI edits.
    recipe = json.loads(json.dumps(plan))
    recipe['selected'] = candidate_id
    return recipe


def validate_recipe(recipe, source):
    if recipe.get('schema') != 'mirage-adaptive-1' or recipe.get('source') != source_identity(source):
        raise ValueError('Recipe source changed or schema is unsupported. Preview this raster again.')
    selected = next((c for c in recipe.get('candidates', []) if c['id'] == recipe.get('selected')), None)
    if selected is None or set(selected.get('params', {})) != set(PARAMETERS):
        raise ValueError('Recipe has no valid selected candidate.')
    if selected.get('mode') not in ('signature', 'geometry', 'geophysics'):
        raise ValueError('Invalid recipe extraction mode.')
    if not np.isfinite(list(selected['params'].values())).all():
        raise ValueError('Recipe parameters must be finite.')
    return selected
