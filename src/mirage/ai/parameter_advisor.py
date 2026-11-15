import time

import numpy as np

from scipy.ndimage import gaussian_filter
from skimage import color, feature, filters, transform


ANALYSIS_MAX_DIM = 512


def _gpu_probe():
    try:
        import cupy as cp  # type: ignore

        count = int(cp.cuda.runtime.getDeviceCount())
        if count <= 0:
            return False, "No CUDA devices", None
        return True, f"{count} CUDA device(s)", cp
    except Exception:
        return False, "CuPy/CUDA not available", None


def _benchmark_cpu_gpu(sample, cp):
    """
    Compare a tiny representative workload on CPU vs GPU and return preferred backend.
    """
    sample = np.asarray(sample, dtype=np.float32)
    sample = np.nan_to_num(sample)

    t0 = time.perf_counter()
    cpu_work = np.abs(filters.sobel(gaussian_filter(sample, sigma=1.2)))
    _ = float(np.mean(cpu_work))
    cpu_s = time.perf_counter() - t0

    try:
        from cupyx.scipy.ndimage import gaussian_filter as cp_gaussian_filter  # type: ignore
        from cupyx.scipy.ndimage import sobel as cp_sobel  # type: ignore
    except Exception:
        return "cpu", cpu_s, None

    try:
        _ = cp.asarray(sample[:8, :8], dtype=cp.float32)
        cp.cuda.runtime.deviceSynchronize()
    except Exception:
        return "cpu", cpu_s, None

    t1 = time.perf_counter()
    gpu_arr = cp.asarray(sample, dtype=cp.float32)
    gpu_blur = cp_gaussian_filter(gpu_arr, sigma=1.2)
    gx = cp_sobel(gpu_blur, axis=0)
    gy = cp_sobel(gpu_blur, axis=1)
    _ = float(cp.mean(cp.sqrt(gx * gx + gy * gy)).get())
    cp.cuda.runtime.deviceSynchronize()
    gpu_s = time.perf_counter() - t1

    chosen = "gpu" if gpu_s < cpu_s * 0.92 else "cpu"
    return chosen, cpu_s, gpu_s


def resolve_compute_mode(compute_mode="auto", image_shape=None):
    """
    Resolve compute backend preference.
    Returns a dict with requested mode, selected mode, availability, and reason.
    """
    requested = str(compute_mode or "auto").strip().lower()
    if requested not in {"auto", "cpu", "gpu"}:
        requested = "auto"

    gpu_available, gpu_detail, cp = _gpu_probe()

    if requested == "cpu":
        selected = "cpu"
        reason = "CPU selected by user."
    elif requested == "gpu":
        selected = "gpu" if gpu_available else "cpu"
        reason = "GPU selected by user." if gpu_available else "GPU requested but unavailable; falling back to CPU."
    else:
        if not gpu_available:
            selected = "cpu"
            reason = f"Auto mode selected CPU ({gpu_detail})."
        elif image_shape is None:
            selected = "gpu"
            reason = f"Auto mode selected GPU ({gpu_detail})."
        else:
            h, w = image_shape
            bench_h = int(min(384, max(96, h)))
            bench_w = int(min(384, max(96, w)))
            yy = np.linspace(0.0, 1.0, bench_h, dtype=np.float32)
            xx = np.linspace(0.0, 1.0, bench_w, dtype=np.float32)
            sample = np.outer(yy, xx)
            chosen, cpu_s, gpu_s = _benchmark_cpu_gpu(sample, cp)
            selected = chosen
            if gpu_s is None:
                reason = "Auto mode benchmark could not run on GPU kernels; selected CPU."
            else:
                reason = (
                    f"Auto benchmark selected {selected.upper()} "
                    f"(cpu={cpu_s:.4f}s, gpu={gpu_s:.4f}s)."
                )

    return {
        "requested": requested,
        "selected": selected,
        "gpu_available": bool(gpu_available),
        "detail": gpu_detail,
        "reason": reason,
    }


def _prepare_analysis_image(image):
    """
    Keep recommendation fast by limiting analysis resolution on very large rasters.
    """
    if image.ndim != 2:
        return image
    h, w = image.shape
    max_dim = max(h, w)
    if max_dim <= ANALYSIS_MAX_DIM:
        return image

    scale = ANALYSIS_MAX_DIM / float(max_dim)
    out_h = max(64, int(round(h * scale)))
    out_w = max(64, int(round(w * scale)))
    resized = transform.resize(
        image,
        (out_h, out_w),
        order=1,
        preserve_range=True,
        anti_aliasing=True,
    )
    return resized.astype(np.float32, copy=False)


def _prepare_analysis_rgb(rgb):
    if rgb is None:
        return None
    rgb = np.asarray(rgb, dtype=np.float32)
    if rgb.ndim != 3:
        return None
    if rgb.shape[0] in (3, 4):
        rgb = np.transpose(rgb[:3], (1, 2, 0))
    elif rgb.shape[-1] >= 3:
        rgb = rgb[..., :3]
    else:
        return None

    h, w, _ = rgb.shape
    max_dim = max(h, w)
    if max_dim > ANALYSIS_MAX_DIM:
        scale = ANALYSIS_MAX_DIM / float(max_dim)
        out_h = max(64, int(round(h * scale)))
        out_w = max(64, int(round(w * scale)))
        rgb = transform.resize(
            rgb,
            (out_h, out_w, 3),
            order=1,
            preserve_range=True,
            anti_aliasing=True,
        )
    return rgb.astype(np.float32, copy=False)


def _split_gray_and_rgb(image):
    arr = np.asarray(image, dtype=np.float32)
    if arr.ndim == 2:
        return arr, None
    if arr.ndim == 3:
        if arr.shape[0] in (3, 4):
            rgb = arr[:3]
            gray = np.mean(rgb, axis=0)
            return gray.astype(np.float32), rgb
        if arr.shape[-1] >= 3:
            rgb = np.transpose(arr[..., :3], (2, 0, 1))
            gray = np.mean(rgb, axis=0)
            return gray.astype(np.float32), rgb
    raise ValueError("Unsupported image shape for recommendation. Expected 2D gray or RGB array.")


def _rgb_optical_metrics(rgb):
    if rgb is None:
        return {
            "colorfulness": 0.0,
            "saturation_mean": 0.0,
            "channel_divergence": 0.0,
            "green_red_index": 0.0,
        }

    rgb = np.nan_to_num(rgb).astype(np.float32)
    p2 = np.percentile(rgb, 2, axis=(0, 1), keepdims=True)
    p98 = np.percentile(rgb, 98, axis=(0, 1), keepdims=True)
    rgb_n = np.clip((rgb - p2) / (p98 - p2 + 1e-6), 0.0, 1.0)

    r = rgb_n[..., 0]
    g = rgb_n[..., 1]
    b = rgb_n[..., 2]
    rg = r - g
    yb = 0.5 * (r + g) - b
    std_rg, std_yb = np.std(rg), np.std(yb)
    mean_rg, mean_yb = np.mean(rg), np.mean(yb)
    colorfulness = float(np.sqrt(std_rg**2 + std_yb**2) + 0.3 * np.sqrt(mean_rg**2 + mean_yb**2))

    hsv = color.rgb2hsv(rgb_n)
    sat_mean = float(np.mean(hsv[..., 1]))
    channel_div = float(np.mean(np.std(rgb_n, axis=2)))
    green_red = float(np.mean((g - r) / (g + r + 1e-6)))

    return {
        "colorfulness": colorfulness,
        "saturation_mean": sat_mean,
        "channel_divergence": channel_div,
        "green_red_index": green_red,
    }


def _circular_evidence(edges):
    """
    Estimate how strongly the raster contains circular/ring-like morphology.
    Returns a score in [0, 1].
    """
    if edges.size == 0:
        return 0.0

    edge_density = float(edges.mean())
    if edge_density < 0.003:
        return 0.0

    min_dim = int(min(edges.shape))
    if min_dim > 720:
        edges = edges[::2, ::2]
        min_dim = int(min(edges.shape))
    r_min = max(8, int(min_dim * 0.06))
    r_max = max(r_min + 3, int(min_dim * 0.34))
    if r_max - r_min < 4:
        return 0.0

    step = max(4, int((r_max - r_min) / 10))
    radii = np.arange(r_min, r_max, step, dtype=int)
    if radii.size == 0:
        return 0.0

    try:
        hspaces = transform.hough_circle(edges, radii)
        accums, _cx, _cy, rad = transform.hough_circle_peaks(
            hspaces,
            radii,
            total_num_peaks=6,
            normalize=False,
        )
    except Exception:
        return 0.0

    if len(accums) == 0:
        return 0.0

    completion = [float(acc) for acc in accums]
    completion = [max(0.0, c) for c in completion]
    best = max(completion)
    mean_top = float(np.mean(sorted(completion, reverse=True)[:2]))

    # Reward one strong ring and also concentric support when present.
    signal = 0.72 * best + 0.28 * mean_top
    return float(np.clip(signal, 0.0, 1.0))


def _road_evidence(edges):
    """
    Estimate evidence of anthropogenic linear traces (roads/pipes/channels)
    over otherwise sparse backgrounds. Returns a score in [0, 1].
    """
    if edges.size == 0:
        return 0.0

    edge_density = float(edges.mean())
    if edge_density < 0.002:
        return 0.0

    min_dim = int(min(edges.shape))
    min_len = max(14, int(min_dim * 0.09))
    max_gap = max(2, int(min_len * 0.18))
    try:
        lines = transform.probabilistic_hough_line(
            edges,
            threshold=10,
            line_length=min_len,
            line_gap=max_gap,
        )
    except Exception:
        return 0.0

    if not lines:
        return 0.0

    lengths = [
        float(np.hypot(p1[0] - p0[0], p1[1] - p0[1]))
        for p0, p1 in lines
    ]
    total_len = float(np.sum(lengths))
    long_lines = sum(1 for L in lengths if L >= max(24.0, min_dim * 0.16))
    line_count = len(lengths)

    # Sparse, long, coherent linear traces are stronger anthropogenic evidence.
    sparse_boost = float(np.clip((0.12 - edge_density) / 0.12, 0.0, 1.0))
    count_score = float(np.clip(line_count / 28.0, 0.0, 1.0))
    long_score = float(np.clip(long_lines / max(1.0, line_count * 0.45), 0.0, 1.0))
    coverage_score = float(np.clip(total_len / (min_dim * 9.0), 0.0, 1.0))

    signal = 0.34 * count_score + 0.34 * long_score + 0.32 * coverage_score
    signal *= (0.55 + 0.45 * sparse_boost)
    return float(np.clip(signal, 0.0, 1.0))


def _lineation_directionality(edges):
    """
    Estimate directional dominance of extracted linear traces.
    0 -> isotropic/no dominant strike, 1 -> strongly dominant orientation.
    """
    if edges.size == 0:
        return 0.0
    edge_density = float(edges.mean())
    if edge_density < 0.002:
        return 0.0

    min_dim = int(min(edges.shape))
    min_len = max(12, int(min_dim * 0.08))
    max_gap = max(2, int(min_len * 0.18))
    try:
        lines = transform.probabilistic_hough_line(
            edges,
            threshold=10,
            line_length=min_len,
            line_gap=max_gap,
        )
    except Exception:
        return 0.0

    if not lines:
        return 0.0

    angles = []
    weights = []
    for p0, p1 in lines:
        dx = float(p1[0] - p0[0])
        dy = float(p1[1] - p0[1])
        length = float(np.hypot(dx, dy))
        if length < 1.0:
            continue
        # Strike-like orientation in [0, pi)
        theta = np.mod(np.arctan2(dy, dx), np.pi)
        angles.append(theta)
        weights.append(length)

    if len(angles) < 4:
        return 0.0

    bins = 18
    hist, _ = np.histogram(
        np.asarray(angles, dtype=np.float32),
        bins=bins,
        range=(0.0, np.pi),
        weights=np.asarray(weights, dtype=np.float32),
    )
    total = float(hist.sum())
    if total <= 0.0:
        return 0.0

    dominance = float(np.max(hist) / total)
    return float(np.clip((dominance - (1.0 / bins)) / (1.0 - (1.0 / bins) + 1e-6), 0.0, 1.0))


def _orientation_coherence_from_gradients(gx, gy):
    """
    0 -> isotropic orientations, 1 -> strong preferred orientations.
    """
    if gx.size == 0 or gy.size == 0:
        return 0.0

    gx = np.asarray(gx, dtype=np.float32)
    gy = np.asarray(gy, dtype=np.float32)
    mag = np.hypot(gx, gy)
    if not np.any(np.isfinite(mag)):
        return 0.0

    mask = mag >= np.percentile(mag, 75)
    if np.count_nonzero(mask) < 64:
        return 0.0

    angles = np.mod(np.arctan2(gy[mask], gx[mask]), np.pi)
    weights = mag[mask]
    bins = 18
    hist, _ = np.histogram(angles, bins=bins, range=(0.0, np.pi), weights=weights)
    total = float(hist.sum())
    if total <= 0.0:
        return 0.0

    p = hist / total
    p = p[p > 0]
    entropy = -float(np.sum(p * np.log(p)))
    entropy_norm = entropy / np.log(bins)
    return float(np.clip(1.0 - entropy_norm, 0.0, 1.0))


def _analyze_raster_cpu(image, rgb=None):
    image = np.nan_to_num(image).astype(np.float32)
    image = _prepare_analysis_image(image)
    rgb = _prepare_analysis_rgb(rgb)
    p2, p98 = np.percentile(image, [2, 98])
    image = np.clip((image - p2) / (p98 - p2 + 1e-6), 0.0, 1.0)

    smooth = gaussian_filter(image, sigma=1.2)
    gy, gx = np.gradient(smooth.astype(np.float32, copy=False))
    grad = np.hypot(gx, gy)
    edges = feature.canny(image, sigma=1.4, low_threshold=0.12, high_threshold=0.22)
    local_var = np.mean((image - gaussian_filter(image, sigma=3.0)) ** 2)
    circle_evidence = _circular_evidence(edges)
    road_evidence = _road_evidence(edges)
    lineation_directionality = _lineation_directionality(edges)
    anomaly_salience = float(np.percentile(grad, 99) - np.percentile(grad, 60))
    orientation_coherence = _orientation_coherence_from_gradients(gx, gy)
    optical = _rgb_optical_metrics(rgb)

    g_med = np.median(grad)
    g_p90 = np.percentile(grad, 90)
    g_std = np.std(grad)
    contrast = float(g_p90 / (g_med + 1e-6))

    step_y = max(1, image.shape[0] // 256)
    step_x = max(1, image.shape[1] // 256)
    sample = image[::step_y, ::step_x]
    unique_ratio = np.unique(np.round(sample, 3)).size / max(sample.size, 1)
    dynamic_range = float(np.percentile(image, 98) - np.percentile(image, 2))

    return {
        "contrast": float(contrast),
        "gradient_std": float(g_std),
        "unique_ratio": float(unique_ratio),
        "dynamic_range": dynamic_range,
        "edge_density": float(edges.mean()),
        "local_variance": float(local_var),
        "circle_evidence": float(circle_evidence),
        "road_evidence": float(road_evidence),
        "lineation_directionality": float(lineation_directionality),
        "anomaly_salience": float(anomaly_salience),
        "orientation_coherence": float(orientation_coherence),
        "colorfulness": float(optical["colorfulness"]),
        "saturation_mean": float(optical["saturation_mean"]),
        "channel_divergence": float(optical["channel_divergence"]),
        "green_red_index": float(optical["green_red_index"]),
    }


def _analyze_raster_gpu(image, rgb=None):
    """
    GPU-accelerated variant for blur/gradient statistics.
    Falls back to CPU-only operators for canny/hough steps.
    """
    gpu_ok, _detail, cp = _gpu_probe()
    if not gpu_ok or cp is None:
        return _analyze_raster_cpu(image, rgb=rgb)

    try:
        from cupyx.scipy.ndimage import gaussian_filter as cp_gaussian_filter  # type: ignore
        from cupyx.scipy.ndimage import sobel as cp_sobel  # type: ignore
    except Exception:
        return _analyze_raster_cpu(image, rgb=rgb)

    image = np.nan_to_num(image).astype(np.float32)
    image = _prepare_analysis_image(image)
    rgb = _prepare_analysis_rgb(rgb)
    p2, p98 = np.percentile(image, [2, 98])
    image = np.clip((image - p2) / (p98 - p2 + 1e-6), 0.0, 1.0)

    gpu_img = cp.asarray(image, dtype=cp.float32)
    smooth_gpu = cp_gaussian_filter(gpu_img, sigma=1.2)
    gy = cp_sobel(smooth_gpu, axis=0)
    gx = cp_sobel(smooth_gpu, axis=1)
    grad = cp.sqrt(gx * gx + gy * gy).get()

    edges = feature.canny(image, sigma=1.4, low_threshold=0.12, high_threshold=0.22)
    local_var = float(np.mean((image - gaussian_filter(image, sigma=3.0)) ** 2))
    circle_evidence = _circular_evidence(edges)
    road_evidence = _road_evidence(edges)
    lineation_directionality = _lineation_directionality(edges)
    anomaly_salience = float(np.percentile(grad, 99) - np.percentile(grad, 60))
    orientation_coherence = _orientation_coherence_from_gradients(gx.get(), gy.get())
    optical = _rgb_optical_metrics(rgb)

    g_med = np.median(grad)
    g_p90 = np.percentile(grad, 90)
    g_std = np.std(grad)
    contrast = float(g_p90 / (g_med + 1e-6))

    step_y = max(1, image.shape[0] // 256)
    step_x = max(1, image.shape[1] // 256)
    sample = image[::step_y, ::step_x]
    unique_ratio = np.unique(np.round(sample, 3)).size / max(sample.size, 1)
    dynamic_range = float(np.percentile(image, 98) - np.percentile(image, 2))

    return {
        "contrast": float(contrast),
        "gradient_std": float(g_std),
        "unique_ratio": float(unique_ratio),
        "dynamic_range": dynamic_range,
        "edge_density": float(edges.mean()),
        "local_variance": float(local_var),
        "circle_evidence": float(circle_evidence),
        "road_evidence": float(road_evidence),
        "lineation_directionality": float(lineation_directionality),
        "anomaly_salience": float(anomaly_salience),
        "orientation_coherence": float(orientation_coherence),
        "colorfulness": float(optical["colorfulness"]),
        "saturation_mean": float(optical["saturation_mean"]),
        "channel_divergence": float(optical["channel_divergence"]),
        "green_red_index": float(optical["green_red_index"]),
    }


def _normalize_metric(value, low, high):
    return float(np.clip((value - low) / (high - low + 1e-6), 0.0, 1.0))


def recommend_settings(image, pixel_size, compute_mode="auto", source_hint=None):
    """Legacy API: describe texture without inferring geological/archaeological origin.

    New physical-scale workflows should use adaptive.recommend_adaptive and
    explicitly distinguish native and analysis resolutions.
    """
    try:
        from ..adaptive import recommend_adaptive
    except ImportError:
        from adaptive import recommend_adaptive
    gray, rgb = _split_gray_and_rgb(image)
    compute = resolve_compute_mode(compute_mode, image_shape=gray.shape)
    metrics = (_analyze_raster_gpu(gray, rgb=rgb) if compute['selected'] == 'gpu'
               else _analyze_raster_cpu(gray, rgb=rgb))
    hint = source_hint or {}
    kind = hint.get('input_kind', 'unknown')
    goal = hint.get('goal', 'continuity')
    plan = recommend_adaptive(gray, pixel_size, input_kind=kind, goal=goal,
                              minimum_length_m=28*pixel_size, smoothing_m=3*pixel_size,
                              linking_gap_m=12*pixel_size, simplification_m=4)
    candidate = plan['candidates'][0]
    mode = candidate['mode']
    feature_mode = {'signature':'Geological signature', 'geometry':'Archaeological signature',
                    'geophysics':'Geophysics Potential Fields'}[mode]
    profile = ('Geo-arch balance' if mode == 'geometry' else
               'Magnetometry' if kind == 'magnetic' else
               'Gravimetry' if kind == 'gravity' else 'Structural continuity')
    family = 'unclassified raster morphology'
    if kind in ('magnetic', 'gravity'):
        family = 'declared potential-field raster'
    elif kind == 'terrain':
        family = 'morphometric enhancement raster'
    elif kind == 'optical' or hint.get('is_true_color_rgb'):
        # This describes an RGB appearance/context hint, not inferred origin.
        family = ('morphometric enhancement raster' if rgb is not None and
                  np.allclose(rgb[0], rgb[1], rtol=1e-4, atol=1e-6) and np.allclose(rgb[1], rgb[2], rtol=1e-4, atol=1e-6) else 'satellite optical raster')
    if goal == 'geometry':
        family = 'user-selected geometry workflow'
    return {'raster_family':family, 'profile':profile, 'feature_mode':feature_mode,
            'reason':'Input type and goal control the workflow. Texture does not identify origin; use the QGIS comparison panel for physical-scale selection.',
            'reason_es':'El tipo declarado y el objetivo controlan el flujo. La textura no identifica su origen; usar el panel QGIS para comparar a escala fisica.',
            'compute':compute, 'metrics':{key:round(value,4) for key,value in metrics.items()},
            # Retained for callers of the historical GUI. Origin scoring is disabled.
            'mode_scores':{'Geological signature':0., 'Archaeological signature':0.},
            'classification_enabled':False, 'params':candidate['params'], 'rgb_conversion':'auto'}


def suggest_parameters(image, pixel_size):
    """
    Backward-compatible parameter suggestion helper.
    """
    return recommend_settings(image, pixel_size, compute_mode="auto")["params"]
