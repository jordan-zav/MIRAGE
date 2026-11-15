"""Bounded CPU TEED fine tuning and ONNX-only evaluation; development use only."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import random
import sys
import time
import types

import numpy as np


def load_upstream(source):
    """Remove one unused reporting import, without changing the network graph."""
    source = Path(source)
    sys.path.insert(0,str(source))
    tree = ast.parse((source/'ted.py').read_text())
    tree.body = [node for node in tree.body if not (isinstance(node,ast.ImportFrom) and node.module == 'utils.img_processing')]
    module = types.ModuleType('mirage_research_teed')
    exec(compile(tree,str(source/'ted.py'),'exec'),module.__dict__)
    return module.TED


def prepare(image):
    import torch
    image = np.asarray(image,dtype=np.float32)
    image = (image-image.min())/max(float(np.ptp(image)),1e-12)
    image = np.repeat(image[None],3,axis=0)*255.
    image -= np.asarray([103.939,116.779,123.68],dtype=np.float32)[:,None,None]
    return torch.from_numpy(image)


def export(model, destination, upstream_hash, phase):
    import torch
    import onnxruntime as ort
    class Probability(torch.nn.Module):
        def __init__(self,network):
            super().__init__()
            self.network = network
        def forward(self,values):
            return torch.sigmoid(self.network(values)[-1])
    wrapper = Probability(model.eval())
    dummy = torch.randn(1,3,64,64)
    destination = Path(destination)
    torch.onnx.export(wrapper,dummy,str(destination),input_names=['image'],output_names=['probability'],
                      dynamic_axes={'image':{0:'batch',2:'height',3:'width'},'probability':{0:'batch',2:'height',3:'width'}},
                      opset_version=17,dynamo=False)
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    session = ort.InferenceSession(str(destination),options,providers=['CPUExecutionProvider'])
    with torch.no_grad():
        expected = wrapper(dummy).numpy()
    actual = session.run(None,{'image':dummy.numpy()})[0]
    error = float(np.max(np.abs(expected-actual)))
    if not np.allclose(expected,actual,rtol=1e-4,atol=1e-5):
        raise ValueError('ONNX parity failed: '+str(error))
    manifest = {'path':destination.name,'sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),
                'code_license':'MIT','weights_license':'MIT',
                'weights_license_basis':'Repository-wide MIT LICENSE at pinned TEED commit; checkpoint is tracked in that repository with no separate exception. Synthetic fine-tuning changes are by the MIRAGE author.',
                'upstream_commit':'40fa4b1391dc6424f88989d0ca75d5b592c8681d',
                'upstream_weights_sha256':upstream_hash,'phase':phase,'multiple':8,
                'input_scale':255.,'mean':[103.939,116.779,123.68],'logits':False,
                'onnx_max_abs_error':error,'seed':20261115}
    path = destination.with_suffix('.json')
    path.write_text(json.dumps(manifest,indent=2))
    return str(path)


def main(session, sources):
    import torch
    from benchmark_lineaments import generate,evaluate
    session = Path(session)
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.manual_seed(20261115)
    random.seed(20261115)
    np.random.seed(20261115)
    torch.use_deterministic_algorithms(True)
    bank = session/'bank'
    manifest = generate(bank) if not bank.exists() else json.loads((bank/'manifest.json').read_text())
    assert not (set(row['group'] for row in manifest['records'] if row['split']=='train') & set(row['group'] for row in manifest['records'] if row['split']!='train'))
    model = load_upstream(sources)()
    weights = session/'models/teed-pretrained.pth'
    upstream_hash = hashlib.sha256(weights.read_bytes()).hexdigest()
    model.load_state_dict(torch.load(weights,map_location='cpu',weights_only=True),strict=True)
    pretrained = export(model,session/'models/teed-pretrained.onnx',upstream_hash,'pretrained')
    train,validation = [],[]
    for record in manifest['records']:
        if record['split'] == 'test':
            continue
        data = np.load(bank/record['file'])
        pair = (prepare(data['image']),torch.from_numpy(data['truth'].astype(np.float32)[None]))
        (train if record['split']=='train' else validation).append(pair)
    optimizer = torch.optim.Adam(model.parameters(),lr=1e-4,weight_decay=1e-5)
    loss_function = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(12.))
    history,best,best_epoch,stale = [],float('inf'),0,0
    started = time.perf_counter()
    for epoch in range(1,13):
        model.train()
        indices = np.random.default_rng(20261115+epoch).permutation(len(train))
        losses = []
        for offset in range(0,len(train),8):
            batch = [train[index] for index in indices[offset:offset+8]]
            images = torch.stack([pair[0] for pair in batch])
            targets = torch.stack([pair[1] for pair in batch])
            optimizer.zero_grad()
            predictions = model(images)
            loss = sum(loss_function(prediction,targets) for prediction in predictions)/len(predictions)
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach()))
        model.eval()
        with torch.no_grad():
            val_loss = float(np.mean([float(loss_function(model(image[None])[-1],target[None])) for image,target in validation]))
        history.append({'epoch':epoch,'train_bce':float(np.mean(losses)), 'validation_bce':val_loss,'seconds':time.perf_counter()-started})
        print(history[-1],flush=True)
        if val_loss < best:
            best,best_epoch,stale = val_loss,epoch,0
            torch.save(model.state_dict(),session/'models/teed-finetuned.pth')
        else:
            stale += 1
        if stale >= 3 or time.perf_counter()-started >= 180:
            break
    model.load_state_dict(torch.load(session/'models/teed-finetuned.pth',map_location='cpu',weights_only=True))
    finetuned = export(model,session/'models/teed-finetuned.onnx',upstream_hash,'fine_tuned')
    record = {'history':history,'selected_epoch':best_epoch,'parameters':sum(parameter.numel() for parameter in model.parameters()),
              'max_epochs':12,'budget_seconds':180,'patience':3,'threads':2,'seed':20261115,
              'selection':'minimum validation BCE; test scenes never enter optimization',
              'upstream_transform':'removed unused count_parameters import by AST only; network graph unchanged'}
    (session/'training.json').write_text(json.dumps(record,indent=2))
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    fig,ax = plt.subplots(figsize=(7,4))
    ax.plot([row['epoch'] for row in history],[row['train_bce'] for row in history],label='Training BCE')
    ax.plot([row['epoch'] for row in history],[row['validation_bce'] for row in history],label='Validation BCE')
    ax.axvline(best_epoch,color='gray',linestyle='--')
    ax.set(xlabel='Epoch',ylabel='Weighted BCE')
    ax.legend()
    fig.tight_layout()
    fig.savefig(session/'training-curves.png',dpi=150)
    methods = {'A_legacy':{'method':'legacy'},'A_thdr':{'method':'thdr'},
               'A_worming':{'method':'worming'},'A_wavelets':{'method':'wavelets'},
               'B_pretrained':{'route':'neural','method':'onnx','model':pretrained},
               'B_finetuned':{'route':'neural','method':'onnx','model':finetuned}}
    summary = evaluate(bank,methods,session/'metrics')
    print(json.dumps(summary,indent=2),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session')
    parser.add_argument('sources')
    args = parser.parse_args()
    main(args.session,args.sources)
