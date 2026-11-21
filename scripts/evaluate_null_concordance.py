"""Read-only replay of frozen public campaign, then rigid-placement inference.

Usage: python scripts/evaluate_null_concordance.py CAMPAIGN OUTPUT
No training, threshold selection or modification of the source campaign.
"""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pyproj
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree
from shapely.geometry import box, mapping, shape
from shapely.ops import transform as transform_geometry

from mirage import extract
import mirage

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
from evaluate_public import chance_fractions, observed_mask, samples, structural_null  # noqa: E402

TOLERANCES = (250, 500, 1000)


def main(campaign, output):
    if not Path(mirage.__file__).resolve().is_relative_to(REPO / 'src'):
        raise RuntimeError('Set PYTHONPATH to this development repository src')
    output.mkdir(exist_ok=False)
    inputs = {}

    def record(path):
        inputs[path.relative_to(campaign).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        return path

    locked = json.loads(record(campaign / 'metrics/parameters-locked-before-test.json').read_text())
    regions = json.loads(record(campaign / 'real/provenance.json').read_text())
    model = record(campaign / 'models/teed-20261115.json')
    manifest = json.loads(model.read_text())
    assert manifest['seed'] == 20261115 and locked['selected_b'] == 'B_20261115'
    assert locked['methods']['A_worming']['threshold'] == .5
    assert locked['methods']['B_20261115']['threshold'] == .65
    record(model.parent / manifest['path'])
    methods = [('worming_050', .5, dict(method='worming')),
               ('worming_020_diagnostic', .2, dict(method='worming')),
               ('B_20261115', .65, dict(route='neural', method='onnx', model=str(model)))]
    results = []
    for region in regions:
        name = region['region']
        with np.load(record(campaign / 'real-metrics' / f'{name}-projected.npz')) as data:
            image, valid, transform = data['image'], data['valid'], data['transform']
            epsg = int(data['epsg'])
        dx, _, xmin, _, dy, ymax = transform
        height, width = image.shape
        filled = image[tuple(distance_transform_edt(~valid, return_distances=False, return_indices=True))]
        extent = box(xmin, ymax + height * dy, xmin + width * dx, ymax)
        project = pyproj.Transformer.from_crs(4326, epsg, always_xy=True).transform
        features = json.loads(record(campaign / 'real' / region['faults_file']).read_text())['features']
        faults = [transform_geometry(project, shape(f['geometry'])).intersection(extent) for f in features]
        tp, _, tw = samples([g for g in faults if not g.is_empty])
        keep = observed_mask(tp, valid, transform)
        tp, tw = tp[keep], tw[keep]
        chance = chance_fractions(tp, valid, transform)
        area = valid.sum() * dx * -dy / 1e6
        for method, threshold, parameters in methods:
            print(f'Extracting {name} {method}', flush=True)
            prediction = extract(filled, pixel_size=100., transform=tuple(transform), threshold=threshold,
                                 scales=(100, 200, 400), heights=(0, 200, 400), **parameters)
            (output / f'{name}-{method}-lines.geojson').write_text(json.dumps(dict(
                type='FeatureCollection', crs=dict(type='name', properties=dict(name=f'EPSG:{epsg}')),
                features=[dict(type='Feature', properties={}, geometry=mapping(g)) for g in prediction.lines])))
            pp, _, pw = samples(prediction.lines)
            keep = observed_mask(pp, valid, transform)
            pp, pw = pp[keep], pw[keep]
            null = structural_null(pp, pw, tp, valid, transform)
            np.savez_compressed(output / f'{name}-{method}-null.npz', fractions=null['fractions'],
                                retained=null['retained'], tolerances=TOLERANCES)
            distances = cKDTree(pp).query(tp)[0] if len(pp) else np.full(len(tp), np.inf)
            for tolerance in TOLERANCES:
                row = dict(region=name, method=method, threshold=threshold, tolerance_m=tolerance,
                           chance_fraction=chance[tolerance], **null['summaries'][tolerance],
                           coverage=float(tw[distances <= tolerance].sum() / tw.sum()),
                           detected_length_km=float(pw.sum() / 1000), area_km2=float(area),
                           detected_km_per_km2=float(pw.sum() / 1000 / area),
                           null_attempts=null['attempts'],
                           retained_min=float(null['retained'].min()) if len(pw) else None,
                           retained_mean=float(null['retained'].mean()) if len(pw) else None)
                results.append(row)
                if tolerance == 500:
                    print(json.dumps(row), flush=True)
            (output / 'results.json').write_text(json.dumps(results, indent=2))
    metadata = dict(input_sha256=inputs, null_seed=20261116, realizations=1000,
                    min_retained=.6, sample_spacing_m=50, area_quadrature_m=100,
                    tolerances_m=TOLERANCES, diagnostic_only='worming_020_diagnostic',
                    interval='observed minus null 97.5% and 2.5% quantiles; reference, not confidence',
                    p_value='(1 + count(null >= observed)) / 1001; unadjusted')
    (output / 'metadata.json').write_text(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    main(Path(sys.argv[1]), Path(sys.argv[2]))
