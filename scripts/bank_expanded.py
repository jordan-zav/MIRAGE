"""Frozen 3000-scene physical benchmark. No private survey inputs."""
import argparse
import hashlib
import json
from pathlib import Path

import harmonica as hm
import numpy as np
from scipy.ndimage import distance_transform_edt


def generate(destination):
    destination = Path(destination)
    destination.mkdir(exist_ok=False)
    yy, xx = np.mgrid[:128, :128]
    records = []
    for index in range(3000):
        seed = 941113 + 104729 * index
        rng = np.random.default_rng(seed)
        split = 'train' if index < 1800 else 'validation' if index < 2400 else 'test'
        kind = ('contact', 'fault', 'dike', 'body', 'cross')[index % 5]
        field = ('gravity', 'TMI', 'RTP')[(index // 5) % 3]
        pixel = float(rng.choice([25, 50, 100]))
        x, y = (xx - 63.5) * pixel, (63.5 - yy) * pixel
        depth, flight = rng.uniform(40, 400), rng.uniform(20, 200)
        dip = rng.uniform(0, 40)
        contrast = rng.uniform(100, 700) if field == 'gravity' else rng.uniform(.2, 3)
        inclination, declination = rng.uniform(35, 80), rng.uniform(-30, 30)
        direction = np.array([np.cos(np.radians(inclination)) * np.sin(np.radians(declination)),
                              np.cos(np.radians(inclination)) * np.cos(np.radians(declination)),
                              -np.sin(np.radians(inclination))])
        image = np.zeros((128, 128))
        truth = np.zeros((128, 128), dtype=bool)
        truth_angle = np.full((128, 128), np.nan)
        geometry = []
        base_rotation = rng.uniform(0, np.pi)
        for structure in range(2 if kind == 'cross' else 1):
            rotation = base_rotation + structure * rng.uniform(np.pi / 4, 3 * np.pi / 4)
            u, v = np.cos(rotation) * x + np.sin(rotation) * y, -np.sin(rotation) * x + np.cos(rotation) * y
            edge = rng.uniform(-15, 15) * pixel
            width = rng.uniform(3, 12) * pixel
            extent = 512 * pixel
            half_length = rng.uniform(15, 35) * pixel if kind == 'body' else extent
            prisms = []
            step = 100.
            for layer in range(8):
                top = -depth - step * layer
                shift = step * layer * np.tan(np.radians(dip))
                east = edge + width + shift if kind in ('dike', 'body') else extent
                prisms.append([edge + shift, east, -half_length, half_length, top - step, top])
                if kind == 'fault' and layer >= 2:
                    prisms.append([-extent, edge + shift, -extent, extent, top - step, top])
            coords = (u, v, np.full_like(u, flight))
            if field == 'gravity':
                response = hm.prism_gravity(coords, prisms, np.full(len(prisms), contrast), field='g_z', parallel=False)
            else:
                rotated = [np.cos(rotation) * direction[0] + np.sin(rotation) * direction[1],
                           -np.sin(rotation) * direction[0] + np.cos(rotation) * direction[1], direction[2]]
                components = hm.prism_magnetic(coords, prisms,
                    tuple(np.full(len(prisms), contrast * d) for d in rotated), field='b', parallel=False)
                response = sum(a * b for a, b in zip(components, rotated))
            image += response
            # Upper projected polygon boundaries, restricted to the model footprint.
            distances = [np.abs(u - edge)]
            if kind in ('dike', 'body'):
                distances.append(np.abs(u - edge - width))
            boundary = (np.minimum.reduce(distances) <= pixel / 2) & (np.abs(v) <= half_length)
            truth[boundary] = True
            truth_angle[boundary] = -np.degrees(rotation) % 180
            if kind == 'body':
                caps = (np.abs(np.abs(v) - half_length) <= pixel / 2) & (u >= edge) & (u <= edge + width)
                truth[caps] = True
                truth_angle[caps] = (90 - np.degrees(rotation)) % 180
            geometry.append(dict(rotation=float(rotation), edge_m=edge, width_m=width,
                                 half_length_m=half_length, prisms=prisms))
        if field == 'RTP':
            import xarray as xr
            data = xr.DataArray(image[::-1], coords={'northing': y[::-1, 0], 'easting': x[0]}, dims=('northing', 'easting'))
            image = hm.reduction_to_pole(data, inclination=inclination, declination=declination).values[::-1]
        amplitude = float(np.ptp(image))
        white, corrugation = rng.uniform(0, .05), rng.uniform(0, .03)
        image += rng.normal(0, white * amplitude, image.shape)
        spacing = int(rng.choice([1, 2, 4]))
        line_offsets = rng.normal(0, corrugation * amplitude, (128 + spacing - 1) // spacing)
        image += np.repeat(line_offsets, spacing)[:128, None]
        # Sample along flight lines, then interpolate to the delivered grid.
        for column in range(128):
            image[:, column] = np.interp(np.arange(128), np.arange(0, 128, spacing), image[::spacing, column])
        valid = rng.random(image.shape) >= rng.uniform(0, .03)
        observed = np.where(valid, image, np.nan)
        nearest = distance_transform_edt(~valid, return_distances=False, return_indices=True)
        filled = observed[tuple(nearest)]
        name = f'{index:04d}-{split}.npz'
        np.savez_compressed(destination / name, image=filled.astype('float32'), observed=observed.astype('float32'),
                            valid=valid, truth=truth, truth_angle=truth_angle.astype('float32'))
        records.append(dict(id=index, group=seed, seed=seed, split=split, file=name,
                            sha256=hashlib.sha256((destination / name).read_bytes()).hexdigest(),
                            field=field, kind=kind, pixel_size_m=pixel, top_depth_m=depth,
                            flight_height_m=flight, dip_from_vertical=dip, contrast=contrast,
                            inclination=inclination, declination=declination,
                            white_noise_fraction=white, line_noise_fraction=corrugation,
                            flight_line_spacing_m=spacing * pixel, geometry=geometry))
        if index % 25 == 0:
            print(f'Generated {index + 1}/3000', flush=True)
            (destination / 'progress.json').write_text(json.dumps({'generated': index + 1}))
    manifest = dict(size=128, modelling='Harmonica 0.7 prisms; eight-layer dipping approximation', records=records)
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('Generated 3000 scenes; manifest sealed', flush=True)


def score(result, truth, truth_angle, valid, pixel, tolerance=2):
    """Raster distance agreement; all coordinates use actual scene resolution."""
    n, m = truth.shape
    valid = valid.copy()
    valid[[0, -1], :] = False
    valid[:, [0, -1]] = False
    prediction = np.zeros_like(truth)
    angles = np.full(truth.shape, np.nan)
    for line in result.lines:
        coords = np.asarray(line.coords)
        for start, end in zip(coords[:-1], coords[1:]):
            points = np.linspace(start, end, max(2, int(np.ceil(np.linalg.norm(end - start) / (pixel / 2))) + 1))
            rows, cols = np.floor(n - points[:, 1] / pixel).astype(int), np.floor(points[:, 0] / pixel).astype(int)
            inside = (rows >= 0) & (rows < n) & (cols >= 0) & (cols < m)
            rows, cols = rows[inside], cols[inside]
            prediction[rows, cols] = True
            delta = end - start
            angles[rows, cols] = np.degrees(np.arctan2(delta[0], delta[1])) % 180
    prediction &= valid
    truth = truth & valid
    distance_truth, nearest = distance_transform_edt(~truth, return_indices=True)
    distance_pred = distance_transform_edt(~prediction) if prediction.any() else np.full(truth.shape, np.hypot(n, m))
    precision = float(np.mean(distance_truth[prediction] <= tolerance)) if prediction.any() else 0.
    recall = float(np.mean(distance_pred[truth] <= tolerance))
    matched = prediction & (distance_truth <= tolerance)
    delta = np.abs(angles[matched] - truth_angle[tuple(nearest[:, matched])]) % 180
    return dict(precision=precision, recall=recall, f1=2 * precision * recall / (precision + recall) if precision + recall else 0.,
                mean_position_error_cells=float(np.mean(distance_pred[truth])),
                mean_azimuth_error_degrees=float(np.nanmean(np.minimum(delta, 180 - delta))) if matched.any() else None)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination')
    generate(parser.parse_args().destination)
