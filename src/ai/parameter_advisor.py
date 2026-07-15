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
    """
    Classify raster style and recommend mode, profile, and parameters.
    """
    gray, rgb = _split_gray_and_rgb(image)
    has_rgb = rgb is not None
    compute = resolve_compute_mode(compute_mode, image_shape=getattr(gray, "shape", None))
    if compute["selected"] == "gpu":
        metrics = _analyze_raster_gpu(gray, rgb=rgb)
    else:
        metrics = _analyze_raster_cpu(gray, rgb=rgb)
    contrast = metrics["contrast"]
    gradient_std = metrics["gradient_std"]
    unique_ratio = metrics["unique_ratio"]
    edge_density = metrics["edge_density"]
    local_variance = metrics["local_variance"]
    circle_evidence = metrics["circle_evidence"]
    road_evidence = metrics["road_evidence"]
    lineation_directionality = metrics["lineation_directionality"]
    anomaly_salience = metrics["anomaly_salience"]
    orientation_coherence = metrics["orientation_coherence"]
    colorfulness = metrics["colorfulness"]
    saturation_mean = metrics["saturation_mean"]
    channel_divergence = metrics["channel_divergence"]

    contrast_n = _normalize_metric(contrast, 2.0, 6.0)
    grad_n = _normalize_metric(gradient_std, 0.02, 0.12)
    edge_n = _normalize_metric(edge_density, 0.10, 0.24)
    local_var_n = _normalize_metric(local_variance, 0.008, 0.05)
    unique_n = _normalize_metric(unique_ratio, 0.002, 0.010)
    circle_n = _normalize_metric(circle_evidence, 0.10, 0.62)
    road_n = _normalize_metric(road_evidence, 0.10, 0.72)
    lineation_n = _normalize_metric(lineation_directionality, 0.22, 0.78)
    anomaly_n = _normalize_metric(anomaly_salience, 0.025, 0.22)
    sparse_anomaly_n = anomaly_n * (1.0 - edge_n)
    orient_n = _normalize_metric(orientation_coherence, 0.18, 0.82)
    color_n = _normalize_metric(colorfulness, 0.06, 0.36)
    sat_n = _normalize_metric(saturation_mean, 0.12, 0.62)
    chdiv_n = _normalize_metric(channel_divergence, 0.04, 0.24)
    sparse_context_n = float(np.clip((0.23 - edge_density) / 0.23, 0.0, 1.0))
    geophys_texture_n = float(
        np.clip(
            0.45 * _normalize_metric(edge_density, 0.14, 0.42)
            + 0.35 * _normalize_metric(local_variance, 0.014, 0.075)
            + 0.20 * grad_n,
            0.0,
            1.0,
        )
    )
    satellite_optical_n = float(
        np.clip(
            0.45 * color_n
            + 0.30 * sat_n
            + 0.25 * chdiv_n,
            0.0,
            1.0,
        )
    )
    graylike_rgb = has_rgb and (
        (color_n <= 0.16 and sat_n <= 0.16 and chdiv_n <= 0.10)
        or channel_divergence <= 0.025
    )
    morphometric_family = graylike_rgb and (
        edge_density >= 0.008 or gradient_std >= 0.004 or local_variance >= 0.002
    )
    circle_effect_n = circle_n * (0.30 + 0.70 * sparse_context_n)
    road_effect_n = road_n * (0.40 + 0.60 * sparse_context_n)

    signature_score = (
        3.0 * contrast_n
        + 2.4 * grad_n
        + 1.8 * local_var_n
        - 0.2 * edge_n
        - 0.6 * unique_n
        - 1.6 * circle_effect_n
        - 1.4 * road_effect_n
        - 1.4 * sparse_anomaly_n
        + 2.6 * geophys_texture_n
        + 2.1 * orient_n
        + 2.4 * lineation_n
    )
    geometry_score = (
        2.4 * edge_n
        + 1.5 * (1.0 - abs(contrast_n - 0.35))
        + 1.2 * (1.0 - abs(local_var_n - 0.18))
        + 0.8 * (1.0 - unique_n)
        + 3.0 * circle_effect_n
        + 2.3 * road_effect_n
        + 1.8 * sparse_anomaly_n
        - 0.9 * geophys_texture_n
        - 1.1 * orient_n
        - 2.2 * lineation_n
    )

    # Hard bias when a robust ring is present: prioritize anthropogenic interpretation.
    if circle_n >= 0.72 and sparse_context_n >= 0.45 and geophys_texture_n <= 0.55:
        geometry_score += 1.4
        signature_score -= 0.7
    if road_n >= 0.65 and sparse_anomaly_n >= 0.35 and geophys_texture_n <= 0.6:
        geometry_score += 1.0
        signature_score -= 0.5
    if edge_density >= 0.16 and sparse_context_n <= 0.35 and circle_n >= 0.45 and road_n >= 0.30:
        signature_score += 8.0
        geometry_score -= 4.0
    if morphometric_family:
        # Default hillshade/RRIM behavior: favor geological unless anthropogenic
        # indicators are clearly strong.
        strong_anthropogenic = (
            (
                (circle_n >= 0.55 and sparse_context_n >= 0.30)
                or (road_n >= 0.72 and sparse_anomaly_n >= 0.25)
            )
            and lineation_n <= 0.65
        )
        if strong_anthropogenic:
            geometry_score += 1.2
        else:
            signature_score += 8.0
            geometry_score -= 6.0
    mode_scores = {
        "Geological signature": signature_score,
        "Archaeological signature": geometry_score,
    }
    feature_mode = max(mode_scores, key=mode_scores.get)

    source_hint = source_hint or {}
    is_true_color_rgb = bool(source_hint.get("is_true_color_rgb", False))
    magnetic_context = bool(has_rgb and graylike_rgb and not is_true_color_rgb)

    optical_family = (not morphometric_family) and has_rgb and (
        is_true_color_rgb
        or
        (
        satellite_optical_n >= 0.40
        or (color_n >= 0.26 and chdiv_n >= 0.22)
        or (sat_n >= 0.34 and chdiv_n >= 0.20)
        )
    )

    is_geophysics = False
    if feature_mode == "Geological signature" and (magnetic_context or (geophys_texture_n >= 0.6 and orient_n >= 0.5)):
        is_geophysics = True

    if is_geophysics:
        feature_mode = "Geophysics Potential Fields"
        if local_variance >= 0.012 or edge_density >= 0.12:
            profile = "Magnetometry"
            raster_family = "geological magnetic raster"
            reason = "High-frequency anomalies and strong lineation continuity indicate a geological magnetic dataset; prioritizing magnetometry settings."
            reason_es = "Anomalías de alta frecuencia y fuerte continuidad de lineamientos indican un conjunto de datos magnéticos geológicos; priorizando parámetros de magnetometría."
            params = {
                "RADI": 3,
                "GTHR": 60,
                "LTHR": 20,
                "FTHR": 3,
                "ATHR": 14,
                "DTHR": 10,
            }
        else:
            profile = "Gravimetry"
            raster_family = "geological structural raster"
            reason = "Smoother, regional variations suggest a potential field dataset like gravity; prioritizing gravimetry settings."
            reason_es = "Variaciones regionales más suaves sugieren un conjunto de datos de campo potencial como gravedad; priorizando parámetros de gravimetría."
            params = {
                "RADI": 5,
                "GTHR": 55,
                "LTHR": 25,
                "FTHR": 4,
                "ATHR": 16,
                "DTHR": 12,
            }
    elif feature_mode == "Geological signature":
        if magnetic_context:
            raster_family = "geological magnetic raster"
        elif morphometric_family:
            raster_family = "morphometric enhancement raster"
        elif optical_family:
            raster_family = "satellite optical raster"
        else:
            raster_family = "geological structural raster"
        profile = "Structural continuity"
        if magnetic_context:
            reason = "Magnetic-style grayscale context is dominant and lineation continuity prevails, so geological magnetic interpretation is prioritized."
            reason_es = "Predomina un contexto magn\u00e9tico en escala de grises con continuidad de lineamientos, por lo que se prioriza la interpretaci\u00f3n geol\u00f3gica magn\u00e9tica."
        elif morphometric_family:
            reason = "Relief-shaded morphology is dominant (hillshade/RRIM-like grayscale response), so geological interpretation is prioritized from terrain structure."
            reason_es = "Predomina la morfolog\u00eda sombreada del relieve (respuesta en grises tipo hillshade/RRIM), por lo que se prioriza la interpretaci\u00f3n geol\u00f3gica desde la estructura del terreno."
        elif is_true_color_rgb:
            reason = "Raster RGB metadata indicates true-color optical imagery, and structural continuity suggests geological interpretation."
            reason_es = "La metadata RGB del r\u00e1ster indica imagen \u00f3ptica en color real, y la continuidad estructural sugiere interpretaci\u00f3n geol\u00f3gica."
        elif optical_family:
            reason = "True-color optical response is dominant (high chromatic diversity/saturation), and structural continuity suggests geological interpretation."
            reason_es = "Predomina una respuesta \u00f3ptica de color real (alta diversidad crom\u00e1tica/saturaci\u00f3n), y la continuidad estructural sugiere interpretaci\u00f3n geol\u00f3gica."
        elif geophys_texture_n >= 0.6:
            reason = "Dense geophysical texture and high structural continuity dominate the scene, so geological interpretation is prioritized despite local curvatures."
            reason_es = "La textura geof\u00edsica densa y la alta continuidad estructural dominan la escena, por lo que se prioriza la interpretaci\u00f3n geol\u00f3gica pese a curvaturas locales."
        else:
            reason = "Directional tendency, repeated structure, and fractal-like organization suggest a geological signature under natural terrain noise."
            reason_es = "La tendencia direccional, la estructura repetida y la organizaci\u00f3n tipo fractal sugieren una firma geol\u00f3gica bajo ruido natural del terreno."
        params = {
            "RADI": int(np.clip(pixel_size * 0.04, 2, 4)),
            "GTHR": int(np.clip(64 + (contrast - 3.0) * 7, 60, 82)),
            "LTHR": 28,
            "FTHR": 4,
            "ATHR": 16,
            "DTHR": 12,
        }
    else:
        if magnetic_context:
            raster_family = "archaeological magnetic raster"
        elif morphometric_family:
            raster_family = "morphometric enhancement raster"
        elif optical_family:
            raster_family = "satellite optical raster"
        else:
            raster_family = "archaeological geometry raster"
        profile = "Geo-arch balance"
        if magnetic_context:
            reason = "Magnetic-style grayscale context with discrete anthropogenic-like morphology (rings/pipes/localized traces) is dominant, so archaeological magnetic interpretation is prioritized."
            reason_es = "Predomina un contexto magn\u00e9tico en escala de grises con morfolog\u00eda discreta tipo antropog\u00e9nica (anillos/pipes/trazas localizadas), por lo que se prioriza la interpretaci\u00f3n arqueol\u00f3gica magn\u00e9tica."
        elif morphometric_family:
            reason = "Relief enhancement is dominant and localized morphology is strong, so archaeological geometry is prioritized on terrain-shaded evidence."
            reason_es = "Predomina el realce de relieve y la morfolog\u00eda localizada es fuerte, por lo que se prioriza la geometr\u00eda arqueol\u00f3gica sobre evidencia de sombreado del terreno."
        elif is_true_color_rgb:
            reason = "Raster RGB metadata indicates true-color optical imagery, and localized morphology favors archaeological geometry."
            reason_es = "La metadata RGB del r\u00e1ster indica imagen \u00f3ptica en color real, y la morfolog\u00eda localizada favorece la geometr\u00eda arqueol\u00f3gica."
        elif circle_n >= 0.55 and sparse_context_n >= 0.4:
            reason = "Strong circular/ring morphology is present, so anthropogenic interpretation is prioritized to preserve circles, pipes, and discrete geometric traces."
            reason_es = "Hay una morfolog\u00eda circular/anular fuerte, por lo que se prioriza la interpretaci\u00f3n antropog\u00e9nica para preservar c\u00edrculos, pipes y trazas geom\u00e9tricas discretas."
        elif road_n >= 0.5:
            reason = "Sparse background with strong linear anthropogenic traces (roads/pipes/channels) is present, so archaeological geometry mode is prioritized."
            reason_es = "Hay fondo relativamente disperso con trazas lineales antropog\u00e9nicas fuertes (caminos/pipes/canales), por lo que se prioriza el modo de geometr\u00eda arqueol\u00f3gica."
        else:
            reason = "Localized geometry with weaker directional preference suggests anthropogenic traces where circles, pipes, and figures should be preserved."
            reason_es = "La geometr\u00eda localizada con menor preferencia direccional sugiere trazas antropog\u00e9nicas, donde deben preservarse c\u00edrculos, pipes y figuras discretas."
        params = {
            "RADI": int(np.clip(pixel_size * 0.05, 3, 5)),
            "GTHR": int(np.clip(56 + (contrast - 2.2) * 7, 52, 74)),
            "LTHR": 22,
            "FTHR": 3,
            "ATHR": 18,
            "DTHR": 14,
        }

    return {
        "raster_family": raster_family,
        "profile": profile,
        "feature_mode": feature_mode,
        "reason": reason,
        "reason_es": reason_es,
        "compute": compute,
        "metrics": {key: round(value, 4) for key, value in metrics.items()},
        "mode_scores": {key: round(value, 3) for key, value in mode_scores.items()},
        "params": params,
    }


def suggest_parameters(image, pixel_size):
    """
    Backward-compatible parameter suggestion helper.
    """
    return recommend_settings(image, pixel_size, compute_mode="auto")["params"]
