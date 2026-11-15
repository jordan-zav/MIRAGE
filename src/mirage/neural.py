"""Explicit, hash-verified external ONNX models. No downloads during inference."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

import numpy as np


def download_model(url, sha256, destination):
    """Download only on explicit invocation; never overwrite a prior artifact."""
    if not url.startswith('https://') or len(sha256) != 64:
        raise ValueError('An HTTPS URL and SHA-256 digest are required.')
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    with urlopen(url, timeout=120) as response:
        data = response.read(100_000_001)
    if len(data) > 100_000_000 or hashlib.sha256(data).hexdigest() != sha256.lower():
        raise ValueError('Model size or SHA-256 verification failed; no file written.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as handle:
        handle.write(data)
    return destination


def infer(image, manifest):
    """Manifest: path, sha256, code_license, weights_license, input convention.

    Contract: NCHW float32 RGB in [0,255], BGR mean subtraction as configured;
    one NCHW probability output. Tiling is intentionally unsupported.
    """
    if manifest is None:
        raise ValueError('Select an external ONNX model manifest explicitly.')
    if isinstance(manifest, (str, Path)):
        manifest_path = Path(manifest)
        config = json.loads(manifest_path.read_text(encoding='utf-8'))
        path = manifest_path.parent / config['path']
    else:
        config = dict(manifest)
        path = Path(config['path'])
    if config.get('code_license') not in ('MIT', 'Apache-2.0', 'BSD-3-Clause') or config.get('weights_license') not in ('MIT', 'Apache-2.0', 'BSD-3-Clause', 'CC0-1.0'):
        raise ValueError('Code and weights require separately recorded permissive licenses.')
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != config['sha256']:
        raise ValueError('ONNX model SHA-256 mismatch.')
    import onnxruntime as ort
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(data, options, providers=['CPUExecutionProvider'])
    values = np.asarray(image, dtype=np.float32)
    span = np.ptp(values)
    values = (values-values.min()) / span if span > 0 else np.zeros_like(values)
    multiple = int(config.get('multiple', 8))
    ny, nx = values.shape
    values = np.pad(values, ((0, (-ny) % multiple), (0, (-nx) % multiple)), mode='reflect')
    values = np.repeat(values[None, None], 3, axis=1)*float(config.get('input_scale', 255.))
    values -= np.asarray(config.get('mean', [103.939, 116.779, 123.68]), dtype=np.float32)[None, :, None, None]
    output = session.run(None, {session.get_inputs()[0].name: values})[-1]
    output = np.asarray(output).squeeze()
    if output.ndim != 2 or output.shape[0] < ny or output.shape[1] < nx or not np.isfinite(output).all():
        raise ValueError('Invalid ONNX output shape or values.')
    if config.get('logits', False):
        output = 1/(1+np.exp(-np.clip(output, -80, 80)))
    if np.min(output) < 0 or np.max(output) > 1:
        raise ValueError('The ONNX output must contain probabilities.')
    return output[:ny, :nx]
