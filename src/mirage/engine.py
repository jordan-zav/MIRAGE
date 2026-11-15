"""Array-first routes; all edge maps share MIRAGE's curve linking engine.

New implementations from Fourier continuation and structure tensor definitions.
No SGTool or bsdwormer source is incorporated.
"""
from dataclasses import dataclass, field
import math

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
from shapely.geometry import LineString
from skimage import measure, morphology

from .line_core import (_build_geophysics_skeleton, _normalize_image,
                        extract_centerline, link_segments)


@dataclass
class Result:
    """Lines in map coordinates; rows correspond one-to-one to attributes.

    Strength and optional azimuth arrays retain the input shape. Worm vertices
    store x,y,height,amplitude independently of line simplification.
    """
    lines: list
    attributes: list
    strength: np.ndarray
    azimuth: np.ndarray | None = None
    points: list = field(default_factory=list)

    def write(self, destination, crs, *, raster=None, transform=None):
        from .outputs import write_result
        return write_result(self, destination, crs, raster=raster, transform=transform)


def _grid(image, pixel_size):
    array = np.asarray(image, dtype=np.float64)
    if array.ndim != 2 or min(array.shape) < 8 or not np.isfinite(array).all():
        raise ValueError('A finite 2D grid of at least 8 by 8 cells is required.')
    if not np.isfinite(pixel_size) or pixel_size <= 0:
        raise ValueError('pixel_size must be positive and finite.')
    return array


def upward(image, height, pixel_size=1.):
    """Harmonic upward continuation, reflected padding of one image width.

    FFT multiplier exp(-height * radial angular wavenumber). Height is a
    continuation level, never an inferred source depth.
    """
    image = _grid(image, pixel_size)
    if not np.isfinite(height) or height < 0:
        raise ValueError('Continuation height must be nonnegative and finite.')
    ny, nx = image.shape
    padded = np.pad(image, ((ny, ny), (nx, nx)), mode='reflect')
    ky = 2*np.pi*np.fft.fftfreq(3*ny, pixel_size)
    kx = 2*np.pi*np.fft.rfftfreq(3*nx, pixel_size)
    multiplier = np.exp(-height*np.hypot(ky[:, None], kx[None, :]))
    return np.fft.irfft2(np.fft.rfft2(padded)*multiplier, s=padded.shape)[ny:2*ny, nx:2*nx]


def anisotropy(image, pixel_size=1., sigma=2.):
    """Structure-tensor tangent azimuth (clockwise from north) and coherence.

    Rows increase southward. Zero coherence means no preferred direction.
    """
    image = _grid(image, pixel_size)
    if not np.isfinite(sigma) or sigma <= 0:
        raise ValueError('sigma must be positive and finite.')
    gy, gx = np.gradient(gaussian_filter(image, 1.), pixel_size)
    xx = gaussian_filter(gx*gx, sigma)
    yy = gaussian_filter(gy*gy, sigma)
    xy = gaussian_filter(gx*gy, sigma)
    strength = np.divide(np.hypot(xx-yy, 2*xy), xx+yy,
                         out=np.zeros_like(xx), where=(xx+yy) > 0)
    tangent = .5*np.arctan2(2*xy, xx-yy) + np.pi/2
    azimuth = np.degrees(np.arctan2(np.cos(tangent), -np.sin(tangent))) % 180
    return azimuth, np.clip(strength, 0, 1)


def _ridges(strength, threshold):
    """Nonmaximum suppression normal to the gradient-magnitude ridges."""
    gy, gx = np.gradient(strength)
    # Hessian eigenvector with most negative curvature estimates ridge normal.
    gyy, gyx = np.gradient(gy)
    _, gxx = np.gradient(gx)
    theta = .5*np.arctan2(2*gyx, gxx-gyy) + np.pi/2
    rr, cc = np.indices(strength.shape, dtype=float)
    dr, dc = np.sin(theta), np.cos(theta)
    before = map_coordinates(strength, [rr-dr, cc-dc], order=1, mode='nearest')
    after = map_coordinates(strength, [rr+dr, cc+dc], order=1, mode='nearest')
    curvature = .5 * (gxx + gyy - np.hypot(gxx - gyy, 2 * gyx))
    mask = (strength > threshold) & (strength >= before) & (strength >= after) & (curvature < -1e-12)
    mask[[0, -1], :] = False
    mask[:, [0, -1]] = False
    return morphology.skeletonize(mask)


def curves(mask, *, minimum_cells=4, gap_cells=3., angle=20.):
    """Same v1.2 centerline extraction and endpoint linking for both routes."""
    skeleton = morphology.skeletonize(mask)
    components = [region.coords for region in measure.regionprops(measure.label(skeleton))]
    lines = [extract_centerline(coords) for coords in components if len(coords) >= minimum_cells]
    return link_segments([line for line in lines if len(line) >= 2], gap_cells, angle,
                         extraction_mode='geophysics')


def extract(image, *, route='geomatic', method='thdr', pixel_size=1.,
            transform=None, threshold=.2, minimum_cells=4, gap_cells=3.,
            angle=20., scales=(1., 2., 4.), heights=(0., 2., 4.),
            model=None, cancelled=None):
    """Return Result. Scales/heights are map units; thresholds are normalized.

    Input must be a north-up square finite metric grid, with transform
    (pixel_size,0,xmin,0,-pixel_size,ymax) mapping pixel corners.
    No method determines the geological origin of a feature.
    """
    image = _grid(image, pixel_size)
    if route not in ('geomatic', 'neural') or not 0 <= threshold <= 1:
        raise ValueError('Unknown route or threshold outside [0,1].')
    if minimum_cells < 2 or gap_cells < 0 or not 0 <= angle <= 180:
        raise ValueError('Invalid curve linking parameters.')
    if transform is None:
        transform = (pixel_size, 0., 0., 0., -pixel_size, image.shape[0]*pixel_size)
    a, b, c, d, e, f = tuple(transform)[:6]
    if not np.isfinite([a,b,c,d,e,f]).all() or not np.allclose([a,b,d,e], [pixel_size,0,0,-pixel_size]):
        raise ValueError('A north-up square metric transform is required.')
    if cancelled and cancelled():
        raise InterruptedError('MIRAGE processing cancelled.')
    if method == 'anisotropy' and route == 'geomatic':
        azimuth, strength = anisotropy(image, pixel_size)
        return Result([], [], strength, azimuth)
    layers = []
    if route == 'neural':
        if method != 'onnx':
            raise ValueError('The neural route requires method=onnx.')
        from .neural import infer
        layers.append((infer(image, model), None, None, None))
    elif method == 'legacy':
        strength = _normalize_image(image)
        mask = _build_geophysics_skeleton(strength, 1, 100*threshold, 'TDR', 'ridge', 1, pixel_size)
        layers.append((strength, mask, None, None))
    elif method in ('thdr', 'worming'):
        for height in heights if method == 'worming' else (0.,):
            field = upward(image, float(height), pixel_size)
            gy, gx = np.gradient(field, pixel_size)
            amplitude = np.hypot(gx, gy)
            strength = _normalize_image(amplitude)
            layers.append((strength, _ridges(strength, threshold), None, float(height), amplitude))
    elif method == 'wavelets':
        import pywt
        for scale in scales:
            if not np.isfinite(scale) or scale <= 0:
                raise ValueError('Wavelet scales must be finite and positive.')
            # CWT implicitly zero-pads. On potential fields with arbitrary DC
            # offsets that creates artificial perimeter edges dominating the
            # normalization, suppressing interior contacts at every threshold.
            # Reflect a full wavelet support before filtering and crop before
            # normalization; map coordinates and physical scales stay unchanged.
            padding = max(8, int(np.ceil(8 * scale / pixel_size)))
            padded = np.pad(image, padding, mode='reflect')
            padded = padded - np.mean(padded)
            coeff_x, _ = pywt.cwt(padded, [scale/pixel_size], 'gaus1', axis=1, method='fft')
            coeff_y, _ = pywt.cwt(padded, [scale/pixel_size], 'gaus1', axis=0, method='fft')
            amplitude = np.hypot(coeff_x[0], coeff_y[0])[padding:-padding, padding:-padding]
            strength = _normalize_image(amplitude)
            layers.append((strength, _ridges(strength, threshold), float(scale), None, amplitude))
    else:
        raise ValueError('Unknown geomatic method.')
    output = Result([], [], np.zeros_like(image))
    for layer in layers:
        if cancelled and cancelled():
            raise InterruptedError('MIRAGE processing cancelled.')
        strength, mask, scale, height = layer[:4]
        amplitude = layer[4] if len(layer) == 5 else strength
        output.strength = np.maximum(output.strength, strength)
        if mask is None:
            mask = strength >= threshold
        for path in curves(mask, minimum_cells=minimum_cells, gap_cells=gap_cells, angle=angle):
            rows, cols = path[:, 0], path[:, 1]
            line = LineString(zip(c+(cols+.5)*a, f+(rows+.5)*e))
            delta = np.subtract(line.coords[-1], line.coords[0])
            azimuth = math.degrees(math.atan2(delta[0], delta[1])) % 180
            output.lines.append(line)
            values = map_coordinates(strength, [rows, cols], order=1, mode='nearest')
            output.attributes.append({'route': route, 'method': method, 'length': line.length,
                                      'azimuth': azimuth, 'strength': float(np.mean(values)),
                                      'scale': scale, 'height': height})
            if method == 'worming':
                amplitudes = map_coordinates(amplitude, [rows, cols], order=1, mode='nearest')
                output.points.extend((float(x), float(y), height, float(v))
                                     for (x, y), v in zip(line.coords, amplitudes))
    return output
