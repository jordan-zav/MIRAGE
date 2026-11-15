"""Independent physical prism scenes, sealed splits and common vector metrics.

Small development benchmark, not field validation. No private geophysical data.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

import harmonica as hm
import numpy as np
from scipy.ndimage import distance_transform_edt


def generate(destination, size=64):
    """Stepped prisms approximate dipping contacts/faults/dikes analytically."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    yy, xx = np.mgrid[:size, :size]
    x = (xx-(size-1)/2)*25
    y = ((size-1)/2-yy)*25
    records = []
    # Each scene has one partition. No rotated/noisy/RTP twin crosses splits.
    for index in range(96):
        split = 'train' if index < 48 else 'validation' if index < 72 else 'test'
        seed = 183071 + index*7919
        rng = np.random.default_rng(seed)
        kind = ('contact', 'fault', 'dike')[index % 3]
        field = ('magnetic', 'gravity')[(index//3) % 2]
        dip = (0., 30.)[(index//6) % 2]
        depth = (50., 125.)[(index//12) % 2]
        noisy = bool((index//2) % 2)
        rtp = field == 'magnetic' and bool((index//4) % 2)
        rotation = rng.uniform(0, np.pi)
        u = np.cos(rotation)*x+np.sin(rotation)*y
        v = -np.sin(rotation)*x+np.cos(rotation)*y
        edge = rng.uniform(-200, 200)
        width = rng.uniform(75, 150)
        prisms, densities = [], []
        for layer in range(8):
            top = -depth-75*layer
            bottom = top-75
            shift = layer*75*np.tan(np.radians(dip))
            west, east = edge+shift, (edge+width+shift if kind == 'dike' else 4000)
            prisms.append([west, east, -4000, 4000, bottom, top])
            densities.append(400.)
            if kind == 'fault' and layer >= 2:
                prisms.append([-4000, west, -4000, 4000, bottom, top])
                densities.append(400.)
        coords = (u, v, np.zeros_like(u))
        if field == 'gravity':
            image = hm.prism_gravity(coords, prisms, densities, field='g_z', parallel=False)
        else:
            # Inclination and declination in the observation frame.
            inclination = 55.
            declination = np.radians(12.)
            inc = np.radians(inclination)
            east = np.cos(inc)*np.sin(declination)
            north = np.cos(inc)*np.cos(declination)
            up = -np.sin(inc)
            mu = np.cos(rotation)*east+np.sin(rotation)*north
            mv = -np.sin(rotation)*east+np.cos(rotation)*north
            magnetic = hm.prism_magnetic(coords, prisms, tuple(np.full(len(prisms), component) for component in (mu, mv, up)), field='b', parallel=False)
            image = sum(component*direction for component, direction in zip(magnetic, (mu, mv, up)))
        if noisy:
            image = image + rng.normal(0, .025*np.ptp(image), image.shape)
        if rtp:
            import xarray as xr
            data = xr.DataArray(image[::-1], coords={'northing':y[::-1,0], 'easting':x[0]}, dims=('northing','easting'))
            image = hm.reduction_to_pole(data, inclination=55., declination=12.).values[::-1]
        boundaries = [edge, edge+width] if kind == 'dike' else [edge]
        truth = np.min([np.abs(u-boundary) for boundary in boundaries], axis=0) <= 12.5
        # Rotated line rasterization can span >one pixel. Keep physical mask.
        name = f'{index:03d}-{split}.npz'
        np.savez_compressed(destination/name, image=image, truth=truth, azimuth=(-np.degrees(rotation)) % 180)
        records.append({'id': index, 'group': seed, 'split': split, 'file': name,
                        'sha256': hashlib.sha256((destination/name).read_bytes()).hexdigest(),
                        'field': field, 'kind': kind, 'dip_from_vertical': dip,
                        'top_depth_m': depth, 'noise_fraction': .025 if noisy else 0.,
                        'rtp_harmonica_applied': rtp, 'rotation': rotation,
                        'edge_m': edge, 'width_m': width, 'pixel_size_m': 25.,
                        'prisms': prisms, 'density': densities})
    manifest = {'seed_protocol': '183071 + scene_id*7919; whole scenes disjoint',
                'modelling': 'Harmonica prisms; dipping bodies approximated by 8 layers; RTP filter applied to selected noisy magnetic fields at inclination 55, declination 12 degrees',
                'size': size, 'records': records}
    (destination/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest


def score(result, truth, true_azimuth, tolerance=2):
    """Position metrics on densified returned curves, avoiding pixel-count bias."""
    ny, nx = truth.shape
    prediction = np.zeros_like(truth)
    angles = np.full(truth.shape, np.nan)
    longest = 0.
    truth_distance = distance_transform_edt(~truth)
    angle_errors = []
    for line, attributes in zip(result.lines, result.attributes):
        distances = np.linspace(0, line.length, max(2, int(np.ceil(line.length/12.5))))
        coords = np.array([line.interpolate(distance).coords[0] for distance in distances])
        rows = np.clip(np.floor(ny-coords[:,1]/25).astype(int), 0, ny-1)
        cols = np.clip(np.floor(coords[:,0]/25).astype(int), 0, nx-1)
        prediction[rows, cols] = True
        angles[rows, cols] = attributes['azimuth']
        matched = truth_distance[rows, cols] <= tolerance
        if matched.any():
            delta = abs(attributes['azimuth']-float(true_azimuth)) % 180
            angle_errors.extend([min(delta, 180-delta)]*int(matched.sum()))
            # Longest curve's matched fraction over truth size, capped at one.
            longest = max(longest, float(np.unique(np.stack([rows[matched],cols[matched]],axis=1),axis=0).shape[0])/max(int(truth.sum()),1))
    pred_distance = distance_transform_edt(~prediction) if prediction.any() else np.full(truth.shape, np.hypot(ny,nx))
    precision = float(np.mean(truth_distance[prediction] <= tolerance)) if prediction.any() else 0.
    recall = float(np.mean(pred_distance[truth] <= tolerance))
    return {'precision': precision, 'recall': recall,
            'f1': 2*precision*recall/(precision+recall) if precision+recall else 0.,
            'mean_position_error_cells': float(np.mean(pred_distance[truth])),
            'mean_azimuth_error_degrees': float(np.mean(angle_errors)) if angle_errors else None,
            'continuity_longest_matched_curve_fraction': min(longest, 1.)}


def evaluate(bank, methods, destination):
    from mirage import extract
    bank, destination = Path(bank), Path(destination)
    manifest = json.loads((bank/'manifest.json').read_text())
    validation, testing = [], []
    for name, parameters in methods.items():
        # Only validation selects a threshold. Test is untouched until locked.
        candidates = []
        for threshold in (.1, .2, .35, .5):
            rows = []
            for record in manifest['records']:
                if record['split'] != 'validation':
                    continue
                data = np.load(bank/record['file'])
                result = extract(data['image'], pixel_size=25., threshold=threshold,
                                 scales=(25.,50.,100.), heights=(0.,50.,100.), **parameters)
                rows.append(score(result, data['truth'], data['azimuth']))
            candidates.append((float(np.mean([row['f1'] for row in rows])), threshold))
        _, chosen = max(candidates, key=lambda item: item[0])
        validation.append({'method': name, 'threshold': chosen, 'candidates': candidates})
        print('Locked', name, chosen, flush=True)
        for record in manifest['records']:
            if record['split'] != 'test':
                continue
            data = np.load(bank/record['file'])
            started = time.perf_counter()
            result = extract(data['image'], pixel_size=25., threshold=chosen,
                             scales=(25.,50.,100.), heights=(0.,50.,100.), **parameters)
            elapsed = time.perf_counter()-started
            testing.append({'method': name, 'case': record['id'], 'seconds': elapsed,
                            **score(result, data['truth'], data['azimuth'])})
    destination.mkdir(parents=True, exist_ok=True)
    (destination/'thresholds-validation.json').write_text(json.dumps(validation, indent=2))
    (destination/'test-metrics.json').write_text(json.dumps(testing, indent=2))
    summary = {}
    for name in methods:
        rows = [row for row in testing if row['method'] == name]
        summary[name] = {key: float(np.mean([row[key] for row in rows if row[key] is not None]))
                         for key in rows[0] if key not in ('method','case') and any(row[key] is not None for row in rows)}
    (destination/'summary.json').write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bank')
    args = parser.parse_args()
    generate(args.bank)
