"""Validation-only parameter lock followed by untouched full-scene test."""
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from mirage import extract

from bank_expanded import score

THRESHOLDS = (.1, .2, .35, .5, .65, .8)


def run(session):
    session = Path(session)
    bank = session / 'bank-complete'
    records = json.loads((bank / 'manifest.json').read_text())['records']
    selection = json.loads((session / 'training-selection.json').read_text())
    methods = {f'A_{method}': dict(method=method) for method in ('thdr', 'worming', 'wavelets')}
    for seed in (20261115, 20261116, 20261117):
        methods[f'B_{seed}'] = dict(route='neural', method='onnx', model=str(session / 'models' / f'teed-{seed}.json'))
    destination = session / 'metrics'
    destination.mkdir(exist_ok=False)
    validation, locked = [], {}
    for name, parameters in methods.items():
        candidates = []
        for threshold in THRESHOLDS:
            rows = []
            for record in records:
                if record['split'] != 'validation':
                    continue
                with np.load(bank / record['file']) as data:
                    pixel = record['pixel_size_m']
                    result = extract(data['image'], pixel_size=pixel, threshold=threshold,
                                     scales=tuple(pixel * s for s in (1, 2, 4)), heights=tuple(pixel * s for s in (0, 2, 4)), **parameters)
                    row = score(result, data['truth'], data['truth_angle'], data['valid'], pixel)
                rows.append(row)
            candidate = dict(method=name, threshold=threshold,
                             f1=float(np.mean([r['f1'] for r in rows])),
                             position=float(np.mean([r['mean_position_error_cells'] for r in rows])))
            candidates.append(candidate)
            validation.append(candidate)
            print('Validation', candidate, flush=True)
            (destination / 'validation-search.json').write_text(json.dumps(validation, indent=2))
        chosen = min(candidates, key=lambda row: (-row['f1'], row['position'], row['threshold']))
        locked[name] = dict(parameters=parameters, threshold=chosen['threshold'], validation=chosen)
    a = min((name for name in methods if name.startswith('A_')),
            key=lambda name: (-locked[name]['validation']['f1'], locked[name]['validation']['position'], name, locked[name]['threshold']))
    b = f"B_{selection['selected_seed']}"
    lock = dict(methods=locked, selected_a=a, selected_b=b, selection='validation only; B seed by BCE',
                bank_manifest_sha256=hashlib.sha256((bank / 'manifest.json').read_bytes()).hexdigest())
    lock_path = destination / 'parameters-locked-before-test.json'
    with lock_path.open('x') as stream:
        json.dump(lock, stream, indent=2)
    print('LOCKED', a, b, hashlib.sha256(lock_path.read_bytes()).hexdigest(), flush=True)
    rows = []
    for record in records:
        if record['split'] != 'test':
            continue
        with np.load(bank / record['file']) as data:
            pixel = record['pixel_size_m']
            for name, config in locked.items():
                started = time.perf_counter()
                result = extract(data['image'], pixel_size=pixel, threshold=config['threshold'],
                                 scales=tuple(pixel * s for s in (1, 2, 4)), heights=tuple(pixel * s for s in (0, 2, 4)), **config['parameters'])
                row = dict(method=name, scene=record['id'], field=record['field'], seconds=time.perf_counter() - started,
                           **score(result, data['truth'], data['truth_angle'], data['valid'], pixel))
                row['f1_tolerance_1'] = score(result, data['truth'], data['truth_angle'], data['valid'], pixel, 1)['f1']
                row['f1_tolerance_4'] = score(result, data['truth'], data['truth_angle'], data['valid'], pixel, 4)['f1']
                rows.append(row)
        if record['id'] % 25 == 0:
            print('Test scene', record['id'], flush=True)
            (destination / 'test-progress.json').write_text(json.dumps(rows))
    (destination / 'test-metrics.json').write_text(json.dumps(rows, indent=2))
    summary = {}
    for name in methods:
        subset = [row for row in rows if row['method'] == name]
        summary[name] = {key: float(np.mean([row[key] for row in subset if row[key] is not None]))
                         for key in subset[0] if key not in ('method', 'scene', 'field') and any(row[key] is not None for row in subset)}
    (destination / 'summary.json').write_text(json.dumps(summary, indent=2))
    comparisons = {}
    for name in methods:
        if not name.startswith('B_'):
            continue
        paired_a = sorted([row for row in rows if row['method'] == a], key=lambda r: r['scene'])
        paired_b = sorted([row for row in rows if row['method'] == name], key=lambda r: r['scene'])
        fields = np.array([r['field'] for r in paired_a])
        rng = np.random.default_rng(88419)
        indices = np.concatenate([rng.choice(np.flatnonzero(fields == field), (10000, sum(fields == field)), replace=True)
                                  for field in sorted(set(fields))], axis=1)
        stats = {}
        for key in ('f1', 'mean_position_error_cells'):
            delta = np.array([rb[key] - ra[key] for ra, rb in zip(paired_a, paired_b)])
            stats[key] = dict(mean=float(delta.mean()), ci95=np.percentile(delta[indices].mean(axis=1), [2.5, 97.5]).tolist())
        stats['superior'] = stats['f1']['ci95'][0] > 0 and stats['mean_position_error_cells']['ci95'][1] <= .5
        comparisons[name] = stats
    (destination / 'paired-comparisons.json').write_text(json.dumps(dict(selected_a=a, selected_b=b, comparisons=comparisons,
                                                                       superior=comparisons[b]['superior']), indent=2))
    print('Completed test', summary, comparisons, flush=True)


if __name__ == '__main__':
    run(sys.argv[1])
