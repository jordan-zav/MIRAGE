"""Three preregistered TEED seeds, validation stopping, external weights only."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import time

import numpy as np
import torch

from train_lineament_model import load_upstream, prepare


def main(session, continuation=False):
    session = Path(session)
    bank = session / 'bank-complete'
    models = session / 'models'
    models.mkdir(exist_ok=True)
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    records = json.loads((bank / 'manifest.json').read_text())['records']
    arrays = {}
    for split in ('train', 'validation'):
        images, truths, masks = [], [], []
        for record in records:
            if record['split'] != split:
                continue
            with np.load(bank / record['file']) as data:
                images.append(prepare(data['image']))
                truths.append(torch.from_numpy(data['truth'].astype('float32')[None]))
                mask = data['valid'].copy()
                mask[[0, -1], :] = False
                mask[:, [0, -1]] = False
                masks.append(torch.from_numpy(mask.astype('float32')[None]))
        arrays[split] = tuple(torch.stack(values).to(device) for values in (images, truths, masks))
    source = Path('O:/0. Projects/_references/TW-MIRAGE-lineamientos-20261115_104530/TEED')
    upstream = Path('D:/DevResources/Sessions/TW-MIRAGE-lineamientos-20261115_104530/models/teed-pretrained.pth')
    summaries = []
    for seed in (20261115, 20261116, 20261117):
        torch.manual_seed(seed)
        random.seed(seed)
        np.random.seed(seed)
        model = load_upstream(source)().to(device)
        model.load_state_dict(torch.load(upstream, map_location=device, weights_only=True))
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-4, weight_decay=1e-5)
        loss_fn = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(12., device=device), reduction='none')
        def loss_for(outputs, targets, masks):
            return sum((loss_fn(output, targets) * masks).sum() / masks.sum() for output in outputs) / len(outputs)
        history, best, anchor, stale, best_epoch = [], float('inf'), float('inf'), 0, 0
        restart_epoch = None
        previous_seconds = 0.
        if continuation:
            initial_path = session / f'training-{seed}.json'
            previous = json.loads(initial_path.read_text())
            preserved = session / f'training-initial-{seed}.json'
            if not preserved.exists():
                preserved.write_bytes(initial_path.read_bytes())
            if previous['stable']:
                summaries.append(previous)
                continue
            model.load_state_dict(torch.load(models / f'teed-{seed}.pth', map_location=device, weights_only=True))
            history = previous['history']
            best = anchor = previous['best_validation_bce']
            best_epoch = previous['selected_epoch']
            previous_seconds = history[-1]['seconds']
            restart_epoch = len(history) + 1
        started = time.monotonic()
        for epoch in range(len(history) + 1, 901 if continuation else 151):
            model.train()
            rng = np.random.default_rng(seed + epoch)
            order = rng.permutation(len(arrays['train'][0]))
            losses = []
            for offset in range(0, len(order), 16):
                indices = order[offset:offset + 16]
                image, target, mask = (array[indices] for array in arrays['train'])
                turns = int(rng.integers(4))
                image, target, mask = (torch.rot90(value, turns, (-2, -1)) for value in (image, target, mask))
                if rng.random() < .5:
                    image, target, mask = (value.flip(-1) for value in (image, target, mask))
                # Scale around channel mean, preserving the preprocessing contract.
                mean = image.mean(dim=(-2, -1), keepdim=True)
                image = (image - mean) * float(rng.uniform(.8, 1.2)) + mean
                optimizer.zero_grad(set_to_none=True)
                loss = loss_for(model(image), target, mask)
                loss.backward()
                optimizer.step()
                losses.append(float(loss.detach()))
            model.eval()
            val_losses = []
            with torch.no_grad():
                for offset in range(0, len(arrays['validation'][0]), 16):
                    image, target, mask = (array[offset:offset + 16] for array in arrays['validation'])
                    val_losses.append(float(loss_for(model(image), target, mask)))
            val = float(np.mean(val_losses))
            if val < best:
                best, best_epoch = val, epoch
                torch.save(model.state_dict(), models / f'teed-{seed}.pth')
            if val < anchor * .999:
                anchor, stale = val, 0
            else:
                stale += 1
            row = dict(epoch=epoch, train_bce=float(np.mean(losses)), validation_bce=val, seconds=previous_seconds + time.monotonic() - started)
            history.append(row)
            record = dict(seed=seed, device=device, history=history, selected_epoch=best_epoch,
                          best_validation_bce=best, stable=stale >= 15, max_epochs=900 if continuation else 150, optimizer_restart_epoch=restart_epoch,
                          budget_seconds=10800, patience=15, upstream_weights_sha256=hashlib.sha256(upstream.read_bytes()).hexdigest())
            (session / f'training-{seed}.json').write_text(json.dumps(record, indent=2))
            print(seed, row, 'stale', stale, flush=True)
            if (epoch >= 20 and stale >= 15) or previous_seconds + time.monotonic() - started >= 10800:
                break
        model.load_state_dict(torch.load(models / f'teed-{seed}.pth', map_location=device, weights_only=True))
        export(model.cpu(), arrays['validation'][0][:5].cpu(), models / f'teed-{seed}.onnx', seed, record)
        summaries.append(record)
    chosen = min(summaries, key=lambda row: row['best_validation_bce'])
    (session / 'training-selection.json').write_text(json.dumps(dict(selected_seed=chosen['seed'], seeds=summaries), indent=2))


def export(model, inputs, destination, seed, record):
    import onnxruntime as ort
    class Probability(torch.nn.Module):
        def __init__(self, network):
            super().__init__()
            self.network = network
        def forward(self, image):
            return torch.sigmoid(self.network(image)[-1])
    wrapper = Probability(model.eval())
    torch.onnx.export(wrapper, inputs[:1], str(destination), input_names=['image'], output_names=['probability'],
                      dynamic_axes={'image': {0: 'batch', 2: 'height', 3: 'width'}, 'probability': {0: 'batch', 2: 'height', 3: 'width'}},
                      opset_version=17, dynamo=False)
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    session = ort.InferenceSession(str(destination), options, providers=['CPUExecutionProvider'])
    with torch.no_grad():
        expected = wrapper(inputs).numpy()
    actual = session.run(None, {'image': inputs.numpy()})[0]
    np.testing.assert_allclose(expected, actual, atol=1e-5, rtol=1e-4)
    manifest = dict(path=destination.name, sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
                    checkpoint_sha256=hashlib.sha256(destination.with_suffix('.pth').read_bytes()).hexdigest(),
                    code_license='MIT', weights_license='MIT', weights_license_basis='Repository-wide MIT at TEED pinned commit; no separately scoped checkpoint grant found',
                    seed=seed, multiple=8, input_scale=255., mean=[103.939, 116.779, 123.68], logits=False,
                    onnx_max_abs_error=float(np.max(np.abs(expected - actual))), parity_inputs=5,
                    selected_epoch=record['selected_epoch'])
    destination.with_suffix('.json').write_text(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session')
    parser.add_argument('--continue-until-stable', action='store_true')
    args = parser.parse_args()
    main(args.session, args.continue_until_stable)
