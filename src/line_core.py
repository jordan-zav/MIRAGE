import math

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.enums import ColorInterp

from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter1d, gaussian_filter, convolve
from shapely.geometry import LineString
from skimage import feature, filters, measure, morphology


def _remove_small_components(mask, min_size):
    if min_size <= 1:
        return mask

    labels = measure.label(mask)
    cleaned = mask.copy()
    for region in measure.regionprops(labels):
        if region.area < min_size:
            cleaned[labels == region.label] = False
    return cleaned


# --- GEOPHYSICS PROCESSING SUITE (MADELINE LEE 2012 / EVANS 1979 / ROBERTS 2001) ---

K_A = np.array([
    [1, -2, 1],
    [1, -2, 1],
    [1, -2, 1]
], dtype=float) / 6.0

K_B = np.array([
    [1, 1, 1],
    [-2, -2, -2],
    [1, 1, 1]
], dtype=float) / 6.0

K_C = np.array([
    [-1, 0, 1],
    [ 0, 0, 0],
    [ 1, 0, -1]
], dtype=float) / 4.0

K_D = np.array([
    [-1, 0, 1],
    [-1, 0, 1],
    [-1, 0, 1]
], dtype=float) / 6.0

K_E = np.array([
    [ 1,  1,  1],
    [ 0,  0,  0],
    [-1, -1, -1]
], dtype=float) / 6.0


def get_dilated_kernel(base_kernel, stride):
    if stride <= 1:
        return base_kernel
    h, w = base_kernel.shape
    dilated = np.zeros((h + (h - 1) * (stride - 1), w + (w - 1) * (stride - 1)))
    for r in range(h):
        for c in range(w):
            dilated[r * stride, c * stride] = base_kernel[r, c]
    return dilated


def first_vertical_derivative(image, pixel_size=1.0):
    ny, nx = image.shape
    ky = np.fft.fftfreq(ny, d=pixel_size) * 2.0 * np.pi
    kx = np.fft.fftfreq(nx, d=pixel_size) * 2.0 * np.pi
    KX, KY = np.meshgrid(kx, ky)
    k = np.sqrt(KX**2 + KY**2)
    
    f_img = np.fft.fft2(image)
    f_vdr1 = f_img * k
    vdr1 = np.real(np.fft.ifft2(f_vdr1))
    return vdr1


def second_vertical_derivative(image, pixel_size=1.0):
    ny, nx = image.shape
    ky = np.fft.fftfreq(ny, d=pixel_size) * 2.0 * np.pi
    kx = np.fft.fftfreq(nx, d=pixel_size) * 2.0 * np.pi
    KX, KY = np.meshgrid(kx, ky)
    k2 = KX**2 + KY**2
    
    f_img = np.fft.fft2(image)
    f_vdr2 = f_img * k2
    vdr2 = np.real(np.fft.ifft2(f_vdr2))
    return vdr2


def compute_potential_field_filter(image, filter_name, pixel_size=1.0):
    filter_name = str(filter_name).upper().strip()
    if filter_name == "NONE":
        return image
    
    gy, gx = np.gradient(image, pixel_size)
    thdr = np.sqrt(gx**2 + gy**2)
    
    if filter_name == "THDR":
        return thdr
        
    vdr1 = first_vertical_derivative(image, pixel_size)
    if filter_name == "VDR1":
        return vdr1
        
    if filter_name == "VDR2":
        return second_vertical_derivative(image, pixel_size)
        
    if filter_name == "AS":
        return np.sqrt(thdr**2 + vdr1**2)
        
    if filter_name == "TDR":
        return np.arctan2(vdr1, np.where(thdr < 1e-8, 1e-8, thdr))
        
    return image


def fit_quadratic_derivatives(image, pixel_size=1.0, stride=1):
    L_eff = float(stride * pixel_size)
    ka = get_dilated_kernel(K_A, stride) / (L_eff**2)
    kb = get_dilated_kernel(K_B, stride) / (L_eff**2)
    kc = get_dilated_kernel(K_C, stride) / (L_eff**2)
    kd = get_dilated_kernel(K_D, stride) / L_eff
    ke = get_dilated_kernel(K_E, stride) / L_eff
    
    a = convolve(image, ka, mode='nearest')
    b = convolve(image, kb, mode='nearest')
    c = convolve(image, kc, mode='nearest')
    d = convolve(image, kd, mode='nearest')
    e = convolve(image, ke, mode='nearest')
    
    return a, b, c, d, e


def compute_principal_curvatures(a, b, c):
    term = np.sqrt((a - b)**2 + c**2) / 2.0
    lam1 = (a + b) / 2.0 + term
    lam2 = (a + b) / 2.0 - term
    
    use_lam1 = np.abs(lam1) >= np.abs(lam2)
    lam = np.where(use_lam1, lam1, lam2)
    
    vx = c / 2.0
    vy = lam - a
    norm = np.sqrt(vx**2 + vy**2)
    
    mask_zero = norm < 1e-8
    vx = np.where(mask_zero, 1.0, vx / np.where(mask_zero, 1.0, norm))
    vy = np.where(mask_zero, 0.0, vy / np.where(mask_zero, 1.0, norm))
    
    mask_c_zero = np.abs(c) < 1e-8
    vx = np.where(mask_c_zero, np.where(a >= b, 1.0, 0.0), vx)
    vy = np.where(mask_c_zero, np.where(a >= b, 0.0, 1.0), vy)
    
    return lam, vx, vy


def detect_curvature_features(image, pixel_size=1.0, stride=1, extract_type="trough", threshold=0.01):
    a, b, c, d, e = fit_quadratic_derivatives(image, pixel_size, stride)
    lam, vx, vy = compute_principal_curvatures(a, b, c)
    
    g_dir = d * vx + e * vy
    L_eff = float(stride * pixel_size)
    zero_crossing = np.abs(g_dir) < L_eff * np.abs(lam)
    
    max_lam = np.max(np.abs(lam))
    curvature_ok = np.abs(lam) >= threshold * max_lam
    
    if extract_type == "trough":
        type_ok = lam > 0
    else:
        type_ok = lam < 0
        
    return zero_crossing & curvature_ok & type_ok


def _build_geophysics_skeleton(image, radi, gthr, filter_name, extract_type, stride, pixel_size=1.0):
    if radi > 0:
        smooth = gaussian_filter(image, sigma=max(0.5, float(radi)))
    else:
        smooth = image.copy()
        
    filtered = compute_potential_field_filter(smooth, filter_name, pixel_size)
    filtered_norm = _normalize_image(filtered)
    
    threshold = float(gthr) / 1000.0
    mask = detect_curvature_features(
        filtered_norm,
        pixel_size=pixel_size,
        stride=stride,
        extract_type=extract_type,
        threshold=threshold
    )
    
    mask = _remove_small_components(mask, min_size=3)
    return morphology.skeletonize(mask)


def prune_skeleton(skel, min_branch_length=10):
    """
    Remove short spurious connected components from a skeleton.
    """
    return _remove_small_components(skel, min_branch_length)


def _read_grayscale_image(src):
    count = int(src.count)
    if count == 1:
        return src.read(1).astype(np.float32)
    if count == 3:
        data = src.read(indexes=[1, 2, 3]).astype(np.float32)
        return np.mean(data, axis=0)
    if count == 4:
        interps = tuple(src.colorinterp or ())
        if len(interps) >= 4 and interps[3] == ColorInterp.alpha:
            data = src.read(indexes=[1, 2, 3]).astype(np.float32)
            return np.mean(data, axis=0)
        raise ValueError(
            "MIRAGE accepts single-band, RGB GeoTIFF (3 bands), or RGBA where band 4 is alpha."
        )
    raise ValueError(
        f"MIRAGE accepts single-band, RGB GeoTIFF (3 bands), or RGBA where band 4 is alpha. "
        f"Detected {count} band(s)."
    )


def _normalize_image(image):
    image = np.nan_to_num(image, nan=0.0, posinf=0.0, neginf=0.0)
    imin, imax = np.nanmin(image), np.nanmax(image)
    return (image - imin) / (imax - imin + 1e-6)


def _is_binary_like(image):
    step_y = max(1, image.shape[0] // 256)
    step_x = max(1, image.shape[1] // 256)
    sample = np.round(image[::step_y, ::step_x], 3)
    unique_count = np.unique(sample).size
    extreme_fraction = np.mean((sample <= 0.05) | (sample >= 0.95))
    return unique_count <= 16 or extreme_fraction >= 0.97


def _build_binary_mask(image):
    threshold = filters.threshold_otsu(image)
    bright = image >= threshold
    dark = image <= threshold

    bright_ratio = np.mean(bright)
    dark_ratio = np.mean(dark)

    candidates = [
        mask for mask, ratio in ((bright, bright_ratio), (dark, dark_ratio))
        if 0.0005 <= ratio <= 0.35
    ]

    if not candidates:
        candidates = [bright if bright_ratio <= dark_ratio else dark]

    mask = min(candidates, key=np.mean)
    mask = _remove_small_components(mask, min_size=6)
    return morphology.skeletonize(mask)


def _build_edge_skeleton(image, radi, gthr):
    high = np.clip(gthr / 255.0, 0.12, 0.95)
    low = np.clip(high * 0.65, 0.05, high - 0.01)

    edges = feature.canny(
        image,
        sigma=max(1.2, float(radi)),
        low_threshold=low,
        high_threshold=high,
    )
    edges = _remove_small_components(edges, min_size=3)
    return morphology.thin(edges)


def _adjacency_from_coords(coords):
    pts = np.column_stack((coords[:, 1], coords[:, 0]))  # x, y
    tree = cKDTree(pts)
    neighbors = tree.query_ball_tree(tree, r=1.5)
    return {i: sorted(set(neighbors[i]) - {i}) for i in range(len(pts))}


def extract_centerline(coords):
    """
    Return skeleton pixels ordered along the longest walkable path.
    """
    if coords.shape[0] < 2:
        return coords

    adj = _adjacency_from_coords(coords)
    endpoints = [i for i, neigh in adj.items() if len(neigh) == 1]

    def bfs(start):
        parents = {start: None}
        distance = {start: 0}
        queue = [start]

        for node in queue:
            for neighbor in adj[node]:
                if neighbor not in parents:
                    parents[neighbor] = node
                    distance[neighbor] = distance[node] + 1
                    queue.append(neighbor)

        farthest = max(distance, key=distance.get)
        return farthest, parents

    start = endpoints[0] if endpoints else 0
    farthest, _ = bfs(start)
    other_end, parents = bfs(farthest)

    ordered = []
    current = other_end
    while current is not None:
        ordered.append(current)
        current = parents[current]

    ordered.reverse()
    return coords[np.array(ordered)]


def _line_metrics(coords):
    if len(coords) < 2:
        return {
            "pixel_length": 0.0,
            "chord": 0.0,
            "straightness": 0.0,
            "elongation": 0.0,
            "path_ratio": 0.0,
            "turn_density": 0.0,
            "max_turn_deg": 0.0,
        }

    coords = coords.astype(float)
    diffs = np.diff(coords, axis=0)
    segment_lengths = np.linalg.norm(diffs, axis=1)
    pixel_length = float(segment_lengths.sum())
    chord = float(np.linalg.norm(coords[-1] - coords[0]))
    straightness = chord / (pixel_length + 1e-6)
    path_ratio = pixel_length / (chord + 1e-6)

    if len(coords) >= 3:
        centered = coords - coords.mean(axis=0, keepdims=True)
        cov = np.cov(centered.T)
        eigvals = np.sort(np.linalg.eigvalsh(cov))[::-1]
        elongation = float((eigvals[0] + 1e-6) / (eigvals[-1] + 1e-6))
    else:
        elongation = float("inf")

    if len(coords) >= 3:
        segments = np.diff(coords, axis=0)
        angles = np.arctan2(segments[:, 0], segments[:, 1])
        turn = np.diff(angles)
        turn = (turn + np.pi) % (2.0 * np.pi) - np.pi
        abs_turn = np.abs(turn)
        turn_density = float(abs_turn.sum() / (pixel_length + 1e-6))
        max_turn_deg = float(np.degrees(abs_turn.max())) if abs_turn.size else 0.0
    else:
        turn_density = 0.0
        max_turn_deg = 0.0

    return {
        "pixel_length": pixel_length,
        "chord": chord,
        "straightness": straightness,
        "elongation": elongation,
        "path_ratio": path_ratio,
        "turn_density": turn_density,
        "max_turn_deg": max_turn_deg,
    }


def _mode_config(extraction_mode):
    modes = {
        "signature": {
            "min_chord_factor": 0.65,
            "min_straightness": 0.55,
            "min_elongation": 4.0,
            "duplicate_spacing_factor": 0.6,
            "duplicate_angle": 12.0,
            "curve_link_angle_boost": 1.0,
            "curve_link_distance_factor": 0.0,
        },
        "geometry": {
            "min_chord_factor": 0.30,
            "min_straightness": 0.22,
            "min_elongation": 1.4,
            "min_path_ratio": 1.35,
            "min_turn_density": 0.08,
            "min_max_turn_deg": 24.0,
            "duplicate_spacing_factor": 0.35,
            "duplicate_angle": 10.0,
            "curve_link_angle_boost": 1.9,
            "curve_link_distance_factor": 0.65,
        },
        "geophysics": {
            "min_chord_factor": 0.35,
            "min_straightness": 0.28,
            "min_elongation": 1.6,
            "duplicate_spacing_factor": 0.2,
            "duplicate_angle": 8.0,
            "curve_link_angle_boost": 1.0,
            "curve_link_distance_factor": 0.0,
        },
    }
    return modes.get(extraction_mode, modes["signature"])


def _is_signature_candidate(coords, lthr, extraction_mode):
    metrics = _line_metrics(coords)
    mode = _mode_config(extraction_mode)
    if metrics["pixel_length"] < max(2.0, float(lthr)):
        return False
    if metrics["chord"] < max(6.0, float(lthr) * mode["min_chord_factor"]):
        return False
    if extraction_mode == "geometry":
        elongated_branch = (
            metrics["straightness"] >= mode["min_straightness"]
            and metrics["elongation"] >= mode["min_elongation"]
        )
        curved_branch = (
            metrics["path_ratio"] >= mode["min_path_ratio"]
            and (
                metrics["turn_density"] >= mode["min_turn_density"]
                or metrics["max_turn_deg"] >= mode["min_max_turn_deg"]
            )
        )
        if not (elongated_branch or curved_branch):
            return False
    else:
        if metrics["straightness"] < mode["min_straightness"]:
            return False
        if metrics["elongation"] < mode["min_elongation"]:
            return False
    return True


def _segment_angle(coords, from_start):
    if len(coords) < 2:
        return None

    if from_start:
        p0 = coords[0]
        p1 = coords[min(2, len(coords) - 1)]
    else:
        p0 = coords[-1]
        p1 = coords[max(-3, -len(coords))]

    dy = float(p1[0] - p0[0])
    dx = float(p1[1] - p0[1])
    if dx == 0.0 and dy == 0.0:
        return None

    return math.degrees(math.atan2(dy, dx))


def _line_angle(line):
    coords = np.asarray(line.coords)
    if len(coords) < 2:
        return None
    dy = float(coords[-1, 1] - coords[0, 1])
    dx = float(coords[-1, 0] - coords[0, 0])
    if dx == 0.0 and dy == 0.0:
        return None
    return math.degrees(math.atan2(dy, dx))


def _line_record(
    idx, line, mode_name, radi, gthr, lthr, fthr, athr, dthr, pixel_size,
    geophys_filters=None, geophys_extract_type="", geophys_stride=0
):
    coords = np.asarray(line.coords)
    if len(coords) < 2:
        metrics = {"pixel_length": 0.0, "chord": 0.0, "straightness": 0.0, "elongation": 0.0}
    else:
        diffs = np.diff(coords, axis=0)
        segment_lengths = np.linalg.norm(diffs, axis=1)
        pixel_length = float(segment_lengths.sum())
        chord = float(np.linalg.norm(coords[-1] - coords[0]))
        straightness = chord / (pixel_length + 1e-6)
        if len(coords) >= 3:
            centered = coords - coords.mean(axis=0, keepdims=True)
            cov = np.cov(centered.T)
            eigvals = np.sort(np.linalg.eigvalsh(cov))[::-1]
            elongation = float((eigvals[0] + 1e-6) / (eigvals[-1] + 1e-6))
        else:
            elongation = 999999.0

        if not np.isfinite(elongation):
            elongation = 999999.0
        metrics = {
            "pixel_length": pixel_length,
            "chord": chord,
            "straightness": straightness,
            "elongation": elongation,
        }

    return {
        "id": int(idx),
        "mode": mode_name,
        "pix_len": float(metrics["pixel_length"]),
        "chord": float(metrics["chord"]),
        "straight": float(metrics["straightness"]),
        "elong": float(metrics["elongation"]),
        "angle": float(_line_angle(line) or 0.0),
        "nverts": int(len(coords)),
        "pixel_sz": float(pixel_size),
        "radii": int(radi),
        "gthr": int(gthr),
        "lthr": int(lthr),
        "fthr": float(fthr),
        "athr": float(athr),
        "dthr": float(dthr),
        "gp_filt": str(geophys_filters or ""),
        "gp_type": str(geophys_extract_type or ""),
        "gp_stride": int(geophys_stride or 0),
    }


def _angle_difference(a_deg, b_deg):
    if a_deg is None or b_deg is None:
        return 180.0

    diff = abs((a_deg - b_deg + 180.0) % 360.0 - 180.0)
    return min(diff, abs(diff - 180.0))


def _merge_pair(line_a, line_b, end_a, end_b):
    first = line_a if end_a == "end" else line_a[::-1]
    second = line_b if end_b == "start" else line_b[::-1]

    gap = second[0] - first[-1]
    if np.any(gap):
        bridge = np.vstack([first[-1], second[0]])
        return np.vstack([first, bridge[1:], second[1:]])

    return np.vstack([first, second[1:]])


def link_segments(lines, dthr, athr, extraction_mode="signature"):
    linked = [np.asarray(line, dtype=int) for line in lines if len(line) >= 2]
    if len(linked) < 2:
        return linked
    mode = _mode_config(extraction_mode)

    changed = True
    while changed:
        changed = False

        endpoints = []
        for idx, line in enumerate(linked):
            endpoints.append((idx, "start", line[0], _segment_angle(line, from_start=True)))
            endpoints.append((idx, "end", line[-1], _segment_angle(line, from_start=False)))

        if len(endpoints) < 2:
            break

        points = np.asarray([item[2] for item in endpoints], dtype=float)
        pairs = cKDTree(points).query_pairs(r=float(dthr))

        candidates = []
        for a_idx, b_idx in pairs:
            seg_a, end_a, point_a, angle_a = endpoints[a_idx]
            seg_b, end_b, point_b, angle_b = endpoints[b_idx]
            if seg_a == seg_b:
                continue

            dist = float(np.linalg.norm(point_a - point_b))
            angle_diff = _angle_difference(angle_a, angle_b)
            angle_limit = float(athr)
            boost = float(mode.get("curve_link_angle_boost", 1.0))
            dist_factor = float(mode.get("curve_link_distance_factor", 0.0))
            if boost > 1.0 and dist <= float(dthr) * dist_factor:
                angle_limit = max(angle_limit, float(athr) * boost)
            if angle_diff > angle_limit:
                continue

            candidates.append(((dist, angle_diff), seg_a, seg_b, end_a, end_b))

        if not candidates:
            break

        candidates.sort(key=lambda item: item[0])
        used_segments = set()
        merges = []

        for _, seg_a, seg_b, end_a, end_b in candidates:
            if seg_a in used_segments or seg_b in used_segments:
                continue
            merges.append((seg_a, seg_b, end_a, end_b))
            used_segments.add(seg_a)
            used_segments.add(seg_b)

        if not merges:
            break

        changed = True
        consumed = set()
        next_linked = []

        for seg_a, seg_b, end_a, end_b in merges:
            if seg_a in consumed or seg_b in consumed:
                continue
            next_linked.append(_merge_pair(linked[seg_a], linked[seg_b], end_a, end_b))
            consumed.add(seg_a)
            consumed.add(seg_b)

        for idx, line in enumerate(linked):
            if idx not in consumed:
                next_linked.append(line)

        linked = next_linked

    return linked


def _pixel_to_world(transform, coords):
    return [rasterio.transform.xy(transform, float(r), float(c)) for r, c in coords]


def _bbox_distance(b1, b2):
    dx = max(0.0, b1[0] - b2[2], b2[0] - b1[2])
    dy = max(0.0, b1[1] - b2[3], b2[1] - b1[3])
    if dx == 0.0 and dy == 0.0:
        return 0.0
    return (dx*dx + dy*dy)**0.5


def suppress_parallel_duplicates(lines, spacing, angle_threshold=12.0):
    if len(lines) < 2:
        return lines

    centroids = np.asarray([[line.centroid.x, line.centroid.y] for line in lines], dtype=float)
    lengths = np.asarray([line.length for line in lines], dtype=float)
    angles = [_line_angle(line) for line in lines]
    bounds = [line.bounds for line in lines]
    tree = cKDTree(centroids)
    order = np.argsort(-lengths)
    kept = []

    for idx in order:
        candidate = lines[idx]
        cand_bounds = bounds[idx]
        duplicate = False
        for other_idx in tree.query_ball_point(centroids[idx], r=float(spacing) * 2.5):
            if other_idx == idx or other_idx not in kept:
                continue
            if _angle_difference(angles[idx], angles[other_idx]) > angle_threshold:
                continue
            if _bbox_distance(cand_bounds, bounds[other_idx]) > spacing:
                continue
            if candidate.distance(lines[other_idx]) > spacing:
                continue
            duplicate = True
            break

        if not duplicate:
            kept.append(idx)

    kept.sort()
    return [lines[idx] for idx in kept]


def _chunk_list(lst, n):
    if n <= 1:
        return [lst]
    k, m = divmod(len(lst), n)
    return [lst[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n)]


def _process_region_chunk(args):
    chunk_list, lthr, extraction_mode = args
    results = []
    for coords in chunk_list:
        line_coords = extract_centerline(coords)
        if _is_signature_candidate(line_coords, lthr=lthr, extraction_mode=extraction_mode):
            results.append(line_coords)
    return results


def _process_polyline_chunk(args):
    chunk_list, trans_args = args
    from rasterio.transform import Affine
    from scipy.ndimage import gaussian_filter1d
    transform = Affine(*trans_args)
    
    results = []
    for coords in chunk_list:
        if len(coords) >= 3:
            smoothed_coords = gaussian_filter1d(coords.astype(float), sigma=1.2, axis=0, mode='nearest')
            smoothed_coords[0] = coords[0]
            smoothed_coords[-1] = coords[-1]
        else:
            smoothed_coords = coords

        world_coords = _pixel_to_world(transform, smoothed_coords)
        results.append(world_coords)
    return results


def lineament_extraction_multiband(
    geotiff,
    out_base,
    radi,
    gthr,
    lthr,
    fthr,
    athr,
    dthr,
    extraction_mode="signature",
    geophys_filters=None,
    geophys_extract_type="trough",
    geophys_stride=1,
):
    """
    Extract lineaments from grayscale or multiband rasters.

    RADI: smoothing radius for tonal rasters
    GTHR: edge sensitivity threshold
    LTHR: minimum skeleton length in pixels
    FTHR: simplification tolerance in map units
    ATHR: maximum angular difference when linking segments
    DTHR: maximum endpoint distance in pixels when linking segments
    """
    import os
    from concurrent.futures import ProcessPoolExecutor

    with rasterio.open(geotiff) as src:
        image = _read_grayscale_image(src)
        transform = src.transform
        crs = src.crs
        pixel_size = max(abs(src.transform.a), abs(src.transform.e))

    image = _normalize_image(image)
    
    num_workers = max(1, os.cpu_count() - 1) if os.cpu_count() else 2

    if extraction_mode == "geophysics":
        if isinstance(geophys_filters, str):
            filters_list = [f.strip() for f in geophys_filters.split(",") if f.strip()]
        elif isinstance(geophys_filters, list):
            filters_list = geophys_filters
        else:
            filters_list = ["TDR"]
            
        pixel_lines = []
        for f_name in filters_list:
            skel = _build_geophysics_skeleton(
                image,
                radi=radi,
                gthr=gthr,
                filter_name=f_name,
                extract_type=geophys_extract_type,
                stride=geophys_stride,
                pixel_size=pixel_size
            )
            skel = prune_skeleton(skel, min_branch_length=max(4, int(lthr // 2)))
            
            regions_coords = [region.coords for region in measure.regionprops(measure.label(skel))]
            chunks = _chunk_list(regions_coords, num_workers)
            task_args = [(chk, float(lthr), extraction_mode) for chk in chunks if len(chk) > 0]
            
            with ProcessPoolExecutor(max_workers=num_workers) as executor:
                results = list(executor.map(_process_region_chunk, task_args))
                
            for res_list in results:
                pixel_lines.extend(res_list)
    else:
        if _is_binary_like(image):
            skel = _build_binary_mask(image)
        else:
            skel = _build_edge_skeleton(image, radi=radi, gthr=gthr)

        skel = prune_skeleton(skel, min_branch_length=max(4, int(lthr // 2)))

        pixel_lines = []
        regions_coords = [region.coords for region in measure.regionprops(measure.label(skel))]
        chunks = _chunk_list(regions_coords, num_workers)
        task_args = [(chk, float(lthr), extraction_mode) for chk in chunks if len(chk) > 0]
        
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            results = list(executor.map(_process_region_chunk, task_args))
            
        for res_list in results:
            pixel_lines.extend(res_list)

    pixel_lines = link_segments(
        pixel_lines,
        dthr=float(dthr),
        athr=float(athr),
        extraction_mode=extraction_mode,
    )
    pixel_lines = [
        coords
        for coords in pixel_lines
        if _is_signature_candidate(coords, lthr=float(lthr), extraction_mode=extraction_mode)
    ]

    trans_args = (transform.a, transform.b, transform.c, transform.d, transform.e, transform.f)
    chunks = _chunk_list(pixel_lines, num_workers)
    poly_args = [(chk, trans_args) for chk in chunks if len(chk) > 0]
    
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        world_lines_lists = list(executor.map(_process_polyline_chunk, poly_args))

    lines = []
    for wl_list in world_lines_lists:
        for world_coords in wl_list:
            if not world_coords:
                continue
            line = LineString(world_coords)
            if fthr > 0:
                line = line.simplify(float(fthr), preserve_topology=False)
            if line.length > pixel_size * max(2.0, float(lthr) * 0.5):
                lines.append(line)

    mode = _mode_config(extraction_mode)
    duplicate_spacing = pixel_size * max(1.0, float(dthr) * mode["duplicate_spacing_factor"])
    lines = suppress_parallel_duplicates(
        lines,
        spacing=duplicate_spacing,
        angle_threshold=mode["duplicate_angle"],
    )

    if not lines:
        raise RuntimeError("No lineaments detected.")

    records = [
        _line_record(
            idx=idx,
            line=line,
            mode_name=extraction_mode,
            radi=radi,
            gthr=gthr,
            lthr=lthr,
            fthr=fthr,
            athr=athr,
            dthr=dthr,
            pixel_size=pixel_size,
            geophys_filters=geophys_filters,
            geophys_extract_type=geophys_extract_type,
            geophys_stride=geophys_stride,
        )
        for idx, line in enumerate(lines, start=1)
    ]
    gdf = gpd.GeoDataFrame(records, geometry=lines, crs=crs)
    gdf.to_file(f"{out_base}.shp")
    gdf.to_file(f"{out_base}.gpkg", layer="lineaments", driver="GPKG")

    return f"{out_base}.shp"
