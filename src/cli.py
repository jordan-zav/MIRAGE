import argparse
import glob
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import ColorInterp, Resampling

from ai.parameter_advisor import recommend_settings
from config import FEATURE_MODES, PRESETS
from pipeline import run_extraction_job, validate_rgb_geotiff

AUTO_READ_MAX_DIM = 1400


def _build_parser():
    parser = argparse.ArgumentParser(description="MIRAGE geospatial signature extraction")
    parser.add_argument("-i", "--input", required=True, nargs="+", help="Input GeoTIFF(s)")
    parser.add_argument("-o", "--output", required=True, help="Output directory")
    parser.add_argument(
        "--profile",
        choices=list(PRESETS.keys()),
        default="Structural continuity",
        help="Starting parameter profile",
    )
    parser.add_argument(
        "--feature-mode",
        choices=list(FEATURE_MODES.keys()),
        default="Geological signature",
        help="Interpretation goal",
    )
    parser.add_argument("--radi", type=int)
    parser.add_argument("--gthr", type=int)
    parser.add_argument("--lthr", type=int)
    parser.add_argument("--fthr", type=float)
    parser.add_argument("--athr", type=float)
    parser.add_argument("--dthr", type=float)
    parser.add_argument(
        "--compute",
        choices=("auto", "cpu", "gpu"),
        default="auto",
        help="Compute backend preference for auto-recommendation (GUI remains unchanged).",
    )
    parser.add_argument("--auto", action="store_true", help="Analyze the raster and recommend settings")
    parser.add_argument(
        "--gp-filters",
        default="TDR,AS",
        help="Comma-separated geophysics filters list (TDR, AS, VDR1, VDR2, THDR, none)",
    )
    parser.add_argument(
        "--gp-type",
        choices=("trough", "ridge"),
        default="trough",
        help="Type of structure to extract: trough (lows) or ridge (highs)",
    )
    parser.add_argument(
        "--gp-stride",
        type=int,
        default=1,
        help="Grid stride / scale for local quadratic curvature analysis (1=3x3, 2=5x5, etc.)",
    )
    parser.add_argument(
        "--rgb-conversion",
        choices=("auto", "average", "gli", "vari", "luma"),
        default="auto",
        help="RGB-to-grayscale conversion method for multiband images (auto, average, gli, vari, luma)",
    )
    return parser


def _preset_parameters(profile_name):
    preset = PRESETS[profile_name]
    return {key: preset[key] for key in ("RADI", "GTHR", "LTHR", "FTHR", "ATHR", "DTHR")}


def _read_analysis_sample(src, out_h, out_w):
    if src.count == 1:
        return src.read(
            1,
            out_shape=(out_h, out_w),
            resampling=Resampling.bilinear,
        ).astype(np.float32)

    return src.read(
        indexes=[1, 2, 3],
        out_shape=(3, out_h, out_w),
        resampling=Resampling.bilinear,
    ).astype(np.float32)


def _resolve_parameters(args, infile):
    validate_rgb_geotiff(infile)
    params = _preset_parameters(args.profile)
    if args.auto:
        with rasterio.open(infile) as src:
            h, w = src.height, src.width
            scale = min(1.0, AUTO_READ_MAX_DIM / float(max(h, w)))
            out_h = max(64, int(round(h * scale)))
            out_w = max(64, int(round(w * scale)))
            interps = tuple(src.colorinterp or ())
            source_hint = {
                "is_true_color_rgb": (
                    len(interps) >= 3
                    and interps[0] == ColorInterp.red
                    and interps[1] == ColorInterp.green
                    and interps[2] == ColorInterp.blue
                )
            }
            data = _read_analysis_sample(src, out_h, out_w)
            pixel_size = abs(src.transform.a) * (h / float(out_h))
        recommendation = recommend_settings(data, pixel_size, compute_mode=args.compute, source_hint=source_hint)
        params = recommendation["params"]
        feature_mode = recommendation["feature_mode"]
        profile = recommendation["profile"]
    else:
        feature_mode = args.feature_mode
        profile = args.profile

    overrides = {
        "RADI": args.radi,
        "GTHR": args.gthr,
        "LTHR": args.lthr,
        "FTHR": args.fthr,
        "ATHR": args.athr,
        "DTHR": args.dthr,
    }
    for key, value in overrides.items():
        if value is not None:
            params[key] = value

    return params, feature_mode, profile


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Expand any glob patterns in input files
    infiles = []
    for pattern in args.input:
        matched = glob.glob(pattern)
        if matched:
            infiles.extend(matched)
        else:
            infiles.append(pattern)

    if not infiles:
        print("Error: No input files found.")
        return 1

    use_subdirs = len(infiles) > 1
    summaries = []

    for infile in infiles:
        params, feature_mode, profile = _resolve_parameters(args, infile)
        resolved_mode_val = FEATURE_MODES[feature_mode]["value"]
        
        if use_subdirs:
            out_dir = Path(args.output) / Path(infile).stem
        else:
            out_dir = Path(args.output)

        summary = run_extraction_job(
            geotiff=infile,
            out_dir=str(out_dir),
            radi=params["RADI"],
            gthr=params["GTHR"],
            lthr=params["LTHR"],
            fthr=params["FTHR"],
            athr=params["ATHR"],
            dthr=params["DTHR"],
            extraction_mode=resolved_mode_val,
            geophys_filters=args.gp_filters if resolved_mode_val == "geophysics" else None,
            geophys_extract_type=args.gp_type if resolved_mode_val == "geophysics" else "trough",
            geophys_stride=args.gp_stride if resolved_mode_val == "geophysics" else 1,
            rgb_conversion=args.rgb_conversion,
        )
        summary["profile"] = profile
        summary["compute_mode"] = args.compute
        summaries.append(summary)

    if use_subdirs:
        print(json.dumps(summaries, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(summaries[0], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
