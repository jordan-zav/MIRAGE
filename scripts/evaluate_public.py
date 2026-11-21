"""Concordance with published faults, never field truth or fault classification."""
import json
from pathlib import Path
import sys

import numpy as np
import pyproj
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import reproject, Resampling, transform_bounds
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree
from shapely.geometry import shape, box
from shapely.ops import transform as transform_geometry

from mirage import extract


def samples(lines, spacing=50):
    points, angles, weights = [], [], []
    for line in lines:
        if line.is_empty:
            continue
        if line.geom_type != 'LineString':
            subpoints, subangles, subweights = samples(list(line.geoms), spacing)
            points.extend(subpoints)
            angles.extend(subangles)
            weights.extend(subweights)
            continue
        n = max(1, int(np.ceil(line.length / spacing)))
        step = line.length / n
        for i in range(n):
            start = line.interpolate(i * step)
            end = line.interpolate((i + 1) * step)
            delta = np.subtract(end.coords[0], start.coords[0])
            points.append(line.interpolate((i + .5) * step).coords[0])
            angles.append(np.degrees(np.arctan2(delta[0], delta[1])) % 180)
            weights.append(step)
    return np.array(points).reshape(-1, 2), np.array(angles), np.array(weights)


def observed_mask(points, valid, transform):
    """Membership in valid north-up square raster cells, without mutating inputs."""
    dx, shear, xmin, shear_y, dy, ymax = transform
    if dx <= 0 or dy >= 0 or shear or shear_y or not np.isclose(dx, -dy):
        raise ValueError('Expected north-up square cells')
    row = np.floor((points[:, 1] - ymax) / dy).astype(int)
    col = np.floor((points[:, 0] - xmin) / dx).astype(int)
    inside = (row >= 0) & (row < valid.shape[0]) & (col >= 0) & (col < valid.shape[1])
    inside[inside] &= valid[row[inside], col[inside]]
    return inside


def chance_fractions(truth_points, valid, transform, tolerances=(250, 500, 1000)):
    """Area quadrature at valid cell centers against 50 m fault samples."""
    if not valid.any() or not len(truth_points):
        raise ValueError('Observed area and fault samples must be nonempty')
    dx, _, xmin, _, dy, ymax = transform
    row, col = np.nonzero(valid)
    centers = np.column_stack((xmin + (col + .5) * dx, ymax + (row + .5) * dy))
    distances = cKDTree(truth_points).query(centers)[0]
    return {t: float(np.mean(distances <= t)) for t in tolerances}


def structural_null(points, weights, truth_points, valid, transform,
                    tolerances=(250, 500, 1000), realizations=1000, seed=20261116,
                    min_retained=.6, max_attempts=None):
    """Rigidly rotate all samples and relocate their weighted center uniformly.

    Rotation is uniform on [0, 2*pi); center is uniform over valid raster area.
    Reject placements retaining less than min_retained of original length.
    Score only retained length. No wrapping, rescaling or independent line moves.
    The shifted-null interval is observed minus null quantiles, not a confidence
    interval for field accuracy. Plus-one upper-tail p includes ties.
    """
    if realizations < 1000 or not .5 < min_retained <= 1:
        raise ValueError('Require >=1000 realizations and majority retention')
    if len(points) != len(weights) or np.any(weights <= 0):
        raise ValueError('Positive sample lengths required')
    if not valid.any() or not len(truth_points):
        raise ValueError('Observed area and fault samples must be nonempty')
    if not len(points):
        return dict(summaries={t: dict(matched_fraction=None, null_mean=None,
                    excess=None, excess_reference95=None, p_upper=None) for t in tolerances},
                    fractions=np.empty((0, len(tolerances))), retained=np.array([]), attempts=0)
    if not observed_mask(points, valid, transform).all():
        raise ValueError('Input detection samples must lie in observed cells')
    tree = cKDTree(truth_points)
    tolerances = np.asarray(tolerances)
    total = weights.sum()
    matched = (weights[:, None] * (tree.query(points)[0][:, None] <= tolerances)).sum(axis=0) / total
    centered = points - np.average(points, axis=0, weights=weights)
    rows, cols = np.nonzero(valid)
    dx, _, xmin, _, dy, ymax = transform
    rng = np.random.default_rng(seed)
    fractions, retained = [], []
    attempts = 0
    limit = max_attempts if max_attempts is not None else realizations * 1000
    while len(fractions) < realizations and attempts < limit:
        attempts += 1
        angle = rng.uniform(0, 2 * np.pi)
        rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        cell = rng.integers(len(rows))
        center = [xmin + (cols[cell] + rng.random()) * dx,
                  ymax + (rows[cell] + rng.random()) * dy]
        moved = centered @ rotation.T + center
        keep = observed_mask(moved, valid, transform)
        length = weights[keep].sum()
        if length < min_retained * total:
            continue
        distances = tree.query(moved[keep])[0]
        fractions.append((weights[keep, None] * (distances[:, None] <= tolerances)).sum(axis=0) / length)
        retained.append(float(length / total))
    if len(fractions) < realizations:
        raise RuntimeError(f'Only {len(fractions)} accepted placements in {attempts} attempts')
    fractions = np.asarray(fractions)
    summaries = {}
    for i, tolerance in enumerate(tolerances):
        null = fractions[:, i]
        summaries[int(tolerance)] = dict(matched_fraction=float(matched[i]), null_mean=float(null.mean()),
            excess=float(matched[i] - null.mean()),
            excess_reference95=(matched[i] - np.quantile(null, [.975, .025])).tolist(),
            p_upper=float((1 + np.count_nonzero(null >= matched[i])) / (realizations + 1)))
    return dict(summaries=summaries, fractions=fractions, retained=np.asarray(retained), attempts=attempts)


def run(session):
    session = Path(session)
    source = session / 'real'
    regions = json.loads((source / 'provenance.json').read_text())
    assert 'CC BY 4.0' in (source / 'magnetic-metadata.das').read_text()
    assert 'Attribution 4.0' in (source / 'faults-license-metadata.json').read_text()
    locked = json.loads((session / 'metrics/parameters-locked-before-test.json').read_text())
    methods = {name: config for name, config in locked['methods'].items() if name.startswith('A_') or name == locked['selected_b']}
    destination = session / 'real-metrics'
    destination.mkdir(exist_ok=False)
    all_blocks, results = [], []
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    for region in regions:
        name = region['region']
        epsg = region['target_epsg']
        with rasterio.open(source / region['grid_file']) as src:
            bounds = transform_bounds(src.crs, f'EPSG:{epsg}', *src.bounds, densify_pts=21)
            width, height = int(np.ceil((bounds[2] - bounds[0]) / 100)), int(np.ceil((bounds[3] - bounds[1]) / 100))
            width, height = min(width, 512), min(height, 512)
            xmin = (bounds[0] + bounds[2] - width * 100) / 2
            ymax = (bounds[1] + bounds[3] + height * 100) / 2
            affine = from_origin(xmin, ymax, 100, 100)
            image = np.full((height, width), np.nan, dtype='float32')
            reproject(rasterio.band(src, 1), image, src_transform=src.transform, src_crs=src.crs,
                      dst_transform=affine, dst_crs=f'EPSG:{epsg}', src_nodata=src.nodata,
                      dst_nodata=np.nan, resampling=Resampling.bilinear)
        valid = np.isfinite(image)
        indices = distance_transform_edt(~valid, return_distances=False, return_indices=True)
        filled = image[tuple(indices)]
        extent = box(xmin, ymax - height * 100, xmin + width * 100, ymax)
        project = pyproj.Transformer.from_crs(4326, epsg, always_xy=True).transform
        features = json.loads((source / region['faults_file']).read_text())['features']
        faults = [transform_geometry(project, shape(feature['geometry'])).intersection(extent) for feature in features]
        faults = [line for line in faults if not line.is_empty]
        truth_points, truth_angles, truth_weights = samples(faults)
        def observed(points):
            r = np.floor((ymax - points[:, 1]) / 100).astype(int)
            c = np.floor((points[:, 0] - xmin) / 100).astype(int)
            inside = (r >= 0) & (r < height) & (c >= 0) & (c < width)
            inside[inside] &= valid[r[inside], c[inside]]
            return inside
        keep = observed(truth_points)
        truth_points, truth_angles, truth_weights = truth_points[keep], truth_angles[keep], truth_weights[keep]
        if not len(truth_points):
            raise ValueError('No observed fault length: ' + name)
        # Fixed local 5-km blocks; block units reused across methods.
        ncols = int(np.ceil(width / 50))
        nrows = int(np.ceil(height / 50))
        def block_ids(points):
            col = np.floor((points[:, 0] - xmin) / 5000).astype(int)
            row = np.floor((ymax - points[:, 1]) / 5000).astype(int)
            return row * ncols + col
        truth_blocks = block_ids(truth_points)
        yy, xx = np.indices(image.shape)
        cellblocks = yy // 50 * ncols + xx // 50
        areas = np.bincount(cellblocks[valid], minlength=ncols * nrows) * .01
        tree_truth = cKDTree(truth_points)
        chance = chance_fractions(truth_points, valid, tuple(affine)[:6])
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        for ax, (method, config) in zip(axes.flat, methods.items()):
            result = extract(filled, pixel_size=100., transform=tuple(affine)[:6], threshold=config['threshold'],
                             scales=(100, 200, 400), heights=(0, 200, 400), **config['parameters'])
            pred_points, pred_angles, pred_weights = samples(result.lines)
            keep = observed(pred_points)
            pred_points, pred_angles, pred_weights = pred_points[keep], pred_angles[keep], pred_weights[keep]
            null = structural_null(pred_points, pred_weights, truth_points, valid, tuple(affine)[:6])
            np.savez_compressed(destination / f'{name}-{method}-null.npz',
                                fractions=null['fractions'], retained=null['retained'])
            pred_blocks = block_ids(pred_points)
            if len(pred_points):
                td = cKDTree(pred_points).query(truth_points)[0]
                pd, nearest = tree_truth.query(pred_points)
                delta = np.abs(pred_angles - truth_angles[nearest]) % 180
                delta = np.minimum(delta, 180 - delta)
            else:
                td = np.full(len(truth_points), np.inf)
                pd, delta = np.array([]), np.array([])
            for tolerance in (250, 500, 1000):
                rows = []
                for block in range(ncols * nrows):
                    ft, fp = truth_blocks == block, pred_blocks == block
                    near = fp & (pd <= tolerance)
                    rows.append(dict(region=name, method=method, tolerance_m=tolerance, block=block, area_km2=areas[block],
                                     fault_length_m=float(truth_weights[ft].sum()),
                                     detected_fault_m=float(truth_weights[ft & (td <= tolerance)].sum()),
                                     unmatched_detection_km=float(pred_weights[fp & (pd > tolerance)].sum() / 1000),
                                     angle_weight_m=float(pred_weights[near].sum()),
                                     angle_sum=float((delta[near] * pred_weights[near]).sum())))
                all_blocks.extend(rows)
                summary = aggregate(rows)
                results.append(dict(region=name, method=method, tolerance_m=tolerance, **summary,
                                    chance_fraction=chance[tolerance], **null['summaries'][tolerance],
                                    null_attempts=null['attempts'], null_seed=20261116,
                                    null_realizations=1000, null_min_retained=.6))
            ax.imshow(image, extent=(xmin, xmin + width * 100, ymax - height * 100, ymax), cmap='gray',
                      vmin=np.nanpercentile(image, 2), vmax=np.nanpercentile(image, 98))
            for line in faults:
                for part in [line] if line.geom_type == 'LineString' else list(line.geoms):
                    ax.plot(*part.xy, color='cyan', linewidth=.6)
            for line in result.lines:
                ax.plot(*line.xy, color='orange', linewidth=.5, alpha=.6)
            ax.set_title(f'{name}: {method} / published faults cyan')
            ax.set_aspect('equal')
        fig.tight_layout()
        fig.savefig(destination / f'{name}-concordance.png', dpi=150)
        plt.close(fig)
        np.savez_compressed(destination / f'{name}-projected.npz', image=image, valid=valid, transform=tuple(affine)[:6], epsg=epsg)
        print('Real region evaluated', name, valid.sum(), 'cells', flush=True)
    (destination / 'regions.json').write_text(json.dumps(results, indent=2))
    (destination / 'blocks.json').write_text(json.dumps(all_blocks, indent=2))
    a, b = locked['selected_a'], locked['selected_b']
    paired = {}
    for method in (a, b):
        paired[method] = sorted([r for r in all_blocks if r['method'] == method and r['tolerance_m'] == 500], key=lambda r: (r['region'], r['block']))
    regions_array = np.array([r['region'] for r in paired[a]])
    rng = np.random.default_rng(88420)
    indices = np.concatenate([rng.choice(np.flatnonzero(regions_array == region), (10000, sum(regions_array == region)), replace=True)
                              for region in sorted(set(regions_array))], axis=1)
    boot = {}
    for method in (a, b):
        arrays = {key: np.array([r[key] for r in paired[method]])[indices].sum(axis=1) for key in
                  ('detected_fault_m', 'fault_length_m', 'unmatched_detection_km', 'area_km2', 'angle_sum', 'angle_weight_m')}
        boot[method] = dict(coverage=arrays['detected_fault_m'] / arrays['fault_length_m'],
                            density=arrays['unmatched_detection_km'] / arrays['area_km2'],
                            azimuth=arrays['angle_sum'] / np.maximum(arrays['angle_weight_m'], 1e-12))
    intervals = {key: np.percentile(boot[b][key] - boot[a][key], [2.5, 97.5]).tolist() for key in boot[a]}
    density_margin = .1 * aggregate(paired[a])['unmatched_detection_km_per_km2']
    superior = intervals['coverage'][0] > 0 and intervals['density'][1] <= density_margin and intervals['azimuth'][1] <= 5
    comparison = dict(selected_a=a, selected_b=b, ci95_difference=intervals, density_margin=density_margin,
                      superior=bool(superior), interpretation='Concordance with mapped faults; not geological truth', regions=len(regions))
    (destination / 'comparison.json').write_text(json.dumps(comparison, indent=2))


def aggregate(rows):
    sums = {key: sum(row[key] for row in rows) for key in
            ('detected_fault_m', 'fault_length_m', 'unmatched_detection_km', 'area_km2', 'angle_sum', 'angle_weight_m')}
    return dict(mapped_fault_coverage=sums['detected_fault_m'] / sums['fault_length_m'] if sums['fault_length_m'] else None,
                unmatched_detection_km_per_km2=sums['unmatched_detection_km'] / sums['area_km2'],
                axial_azimuth_error_degrees=sums['angle_sum'] / sums['angle_weight_m'] if sums['angle_weight_m'] else None)


if __name__ == '__main__':
    run(sys.argv[1])
