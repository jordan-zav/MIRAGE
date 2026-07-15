import json
import sys
import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.enums import ColorInterp
from rasterio.transform import from_origin

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai.parameter_advisor import recommend_settings
from pipeline import run_extraction_job, validate_rgb_geotiff


def _write_test_raster(path, data, count=3):
    if data.ndim == 2:
        if count == 1:
            data = data[np.newaxis, :, :]
        else:
            data = np.stack([data, data, data], axis=0)
    elif data.ndim == 3 and data.shape[0] == 3:
        pass
    else:
        raise ValueError("Test raster data must be 2D or 3xHxW.")

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=data.shape[1],
        width=data.shape[2],
        count=data.shape[0],
        dtype=data.dtype,
        crs="EPSG:4326",
        transform=from_origin(-70.0, -10.0, 0.0001, 0.0001),
    ) as dst:
        dst.write(data)


class MIRAGETests(unittest.TestCase):
    def test_recommend_settings_returns_expected_structure(self):
        image = np.zeros((64, 64), dtype=np.float32)
        image[16:48, 20:44] = 1.0

        recommendation = recommend_settings(image, pixel_size=10.0)

        self.assertIn(recommendation["feature_mode"], {
            "Geological signature",
            "Archaeological signature",
        })
        self.assertIn("params", recommendation)
        self.assertIn("compute", recommendation)
        self.assertEqual(recommendation["compute"]["selected"], "cpu")
        self.assertEqual(set(recommendation["params"].keys()), {"RADI", "GTHR", "LTHR", "FTHR", "ATHR", "DTHR"})

    def test_pipeline_writes_report_and_attributes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            raster_path = tmpdir / "line.tif"
            out_dir = tmpdir / "out"
            data = np.zeros((96, 96), dtype=np.uint8)
            data[46:50, 18:78] = 255
            _write_test_raster(raster_path, data)

            summary = run_extraction_job(
                geotiff=str(raster_path),
                out_dir=str(out_dir),
                radi=2,
                gthr=60,
                lthr=8,
                fthr=0.0,
                athr=20.0,
                dthr=10.0,
                extraction_mode="signature",
            )

            report_path = Path(summary["outputs"]["report"])
            report_md_path = Path(summary["outputs"]["report_markdown"])
            shp_path = Path(summary["outputs"]["lineaments"])
            gpkg_path = Path(summary["outputs"]["geopackage"])

            self.assertTrue(report_path.exists())
            self.assertTrue(report_md_path.exists())
            self.assertTrue(shp_path.exists())
            self.assertTrue(gpkg_path.exists())
            self.assertIn("Reporte de Ejecución", report_md_path.read_text(encoding="utf-8"))
            self.assertGreaterEqual(summary["lineaments"]["count"], 1)

            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["parameters"]["extraction_mode"], "signature")
            self.assertIn("lineaments", payload)
            self.assertEqual(payload["outputs"]["report"], str(report_path))
            self.assertEqual(payload["outputs"]["geopackage"], str(gpkg_path))
            gdf = gpd.read_file(shp_path)
            self.assertIn("mode", gdf.columns)
            self.assertIn("pix_len", gdf.columns)
            self.assertGreaterEqual(len(gdf), 1)
            gpkg_gdf = gpd.read_file(gpkg_path, layer="lineaments")
            self.assertEqual(len(gpkg_gdf), len(gdf))

    def test_pipeline_accepts_single_band_geotiff(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            raster_path = tmpdir / "single_band.tif"
            out_dir = tmpdir / "out"
            data = np.zeros((96, 96), dtype=np.uint8)
            data[46:50, 18:78] = 255
            _write_test_raster(raster_path, data, count=1)

            summary = run_extraction_job(
                geotiff=str(raster_path),
                out_dir=str(out_dir),
                radi=2,
                gthr=60,
                lthr=8,
                fthr=0.0,
                athr=20.0,
                dthr=10.0,
                extraction_mode="signature",
            )

            self.assertTrue(Path(summary["outputs"]["lineaments"]).exists())
            self.assertTrue(Path(summary["outputs"]["geopackage"]).exists())
            self.assertGreaterEqual(summary["lineaments"]["count"], 1)

    def test_recommend_settings_detects_circular_anthropogenic_pattern(self):
        size = 160
        yy, xx = np.indices((size, size))
        cy = cx = size // 2
        radius = 36.0
        dist = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)

        ring = ((dist >= radius - 2.2) & (dist <= radius + 2.2)).astype(np.float32)
        rng = np.random.default_rng(7)
        noise = rng.normal(0.0, 0.06, ring.shape).astype(np.float32)
        image = np.clip(0.25 + 0.9 * ring + noise, 0.0, 1.0).astype(np.float32)

        recommendation = recommend_settings(image, pixel_size=10.0)
        self.assertEqual(recommendation["feature_mode"], "Archaeological signature")
        self.assertGreaterEqual(recommendation["metrics"].get("circle_evidence", 0.0), 0.10)

    def test_recommend_settings_detects_road_like_anthropogenic_pattern(self):
        size = 180
        image = np.full((size, size), 0.35, dtype=np.float32)

        yy, xx = np.indices((size, size))
        road_1 = np.abs((yy - (0.55 * xx + 26.0))) <= 1.6
        road_2 = np.abs((yy - (0.55 * xx + 42.0))) <= 1.6
        road_3 = np.abs((yy - (-0.75 * xx + 168.0))) <= 1.5
        image[road_1 | road_2 | road_3] = 0.95

        rng = np.random.default_rng(12)
        image = np.clip(image + rng.normal(0.0, 0.028, image.shape).astype(np.float32), 0.0, 1.0)

        recommendation = recommend_settings(image, pixel_size=10.0)
        self.assertEqual(recommendation["feature_mode"], "Archaeological signature")
        self.assertGreaterEqual(recommendation["metrics"].get("road_evidence", 0.0), 0.08)

    def test_recommend_settings_prefers_geological_on_dense_geophysical_texture(self):
        size = 220
        yy, xx = np.indices((size, size), dtype=np.float32)
        ridge_1 = np.sin(0.085 * xx + 0.12 * yy)
        ridge_2 = np.sin(0.11 * xx - 0.07 * yy + 1.2)
        texture = 0.5 + 0.20 * ridge_1 + 0.20 * ridge_2

        cy, cx = size / 2.0, size / 2.0
        dist = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
        ring = ((dist >= 44.0) & (dist <= 47.5)).astype(np.float32) * 0.22

        rng = np.random.default_rng(21)
        noise = rng.normal(0.0, 0.07, (size, size)).astype(np.float32)
        image = np.clip(texture + ring + noise, 0.0, 1.0).astype(np.float32)

        recommendation = recommend_settings(image, pixel_size=10.0)
        self.assertEqual(recommendation["feature_mode"], "Geological signature")

    def test_recommend_settings_detects_satellite_optical_family(self):
        h, w = 180, 180
        yy, xx = np.indices((h, w), dtype=np.float32)
        r = np.clip(0.2 + 0.6 * (xx / max(1.0, w - 1.0)), 0.0, 1.0)
        g = np.clip(0.15 + 0.65 * (yy / max(1.0, h - 1.0)), 0.0, 1.0)
        b = np.clip(0.10 + 0.55 * np.sin(0.08 * xx + 0.05 * yy), 0.0, 1.0)
        rgb = np.stack([r, g, b], axis=0).astype(np.float32)

        recommendation = recommend_settings(
            rgb,
            pixel_size=10.0,
            source_hint={"is_true_color_rgb": True},
        )
        self.assertEqual(recommendation["raster_family"], "satellite optical raster")
        self.assertEqual(recommendation["raster_family"], "satellite optical raster")

    def test_recommend_settings_detects_satellite_optical_family_earthy_scene(self):
        h, w = 200, 160
        yy, xx = np.indices((h, w), dtype=np.float32)
        base = 0.25 + 0.45 * (yy / max(1.0, h - 1.0))
        relief = 0.18 * np.sin(0.04 * xx + 0.03 * yy) + 0.12 * np.cos(0.06 * yy)
        r = np.clip(base + 0.20 + 0.10 * relief, 0.0, 1.0)
        g = np.clip(base + 0.12 + 0.07 * relief, 0.0, 1.0)
        b = np.clip(base + 0.03 + 0.14 * relief, 0.0, 1.0)
        rgb = np.stack([r, g, b], axis=0).astype(np.float32)

        recommendation = recommend_settings(
            rgb,
            pixel_size=10.0,
            source_hint={"is_true_color_rgb": True},
        )
        self.assertEqual(recommendation["raster_family"], "satellite optical raster")

    def test_recommend_settings_detects_morphometric_enhancement_family(self):
        h, w = 220, 180
        yy, xx = np.indices((h, w), dtype=np.float32)
        relief = (
            0.50
            + 0.18 * np.sin(0.06 * xx + 0.04 * yy)
            + 0.12 * np.cos(0.05 * yy)
            + 0.08 * np.sin(0.09 * xx - 0.03 * yy)
        )
        relief = np.clip(relief, 0.0, 1.0).astype(np.float32)
        rgb = np.stack([relief, relief, relief], axis=0).astype(np.float32)

        recommendation = recommend_settings(
            rgb,
            pixel_size=10.0,
            source_hint={"is_true_color_rgb": True},
        )
        self.assertEqual(recommendation["raster_family"], "morphometric enhancement raster")
        self.assertEqual(recommendation["feature_mode"], "Geological signature")

    def test_directional_dominance_reduces_archaeological_bias(self):
        h, w = 220, 180
        image = np.full((h, w), 0.45, dtype=np.float32)
        yy, xx = np.indices((h, w))

        # Strong dominant strike: subparallel lineaments.
        line_a = np.abs(yy - (0.95 * xx + 18.0)) <= 1.2
        line_b = np.abs(yy - (0.95 * xx + 34.0)) <= 1.2
        line_c = np.abs(yy - (0.95 * xx + 50.0)) <= 1.2
        image[line_a | line_b | line_c] = 0.88

        rng = np.random.default_rng(33)
        image = np.clip(image + rng.normal(0.0, 0.02, image.shape).astype(np.float32), 0.0, 1.0)
        rgb = np.stack([image, image, image], axis=0).astype(np.float32)

        recommendation = recommend_settings(
            rgb,
            pixel_size=10.0,
            source_hint={"is_true_color_rgb": True},
        )
        self.assertEqual(recommendation["feature_mode"], "Geological signature")
        self.assertGreaterEqual(recommendation["metrics"].get("lineation_directionality", 0.0), 0.20)

    def test_recommend_settings_detects_archaeological_magnetic_context(self):
        h, w = 260, 260
        yy, xx = np.indices((h, w), dtype=np.float32)
        image = np.full((h, w), 0.72, dtype=np.float32)

        # Localized survey strip-like valid region
        mask = (yy > 20) & (yy < 170) & (xx > 20) & (xx < 240)
        image[~mask] = 0.92

        # Ring-like anomalies inside valid strip
        cy, cx = 92.0, 122.0
        dist = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
        ring1 = (dist >= 30.0) & (dist <= 33.0)
        ring2 = (dist >= 54.0) & (dist <= 57.0)
        image[ring1 | ring2] = 0.22

        rng = np.random.default_rng(41)
        image[mask] = np.clip(image[mask] + rng.normal(0.0, 0.06, np.count_nonzero(mask)).astype(np.float32), 0.0, 1.0)
        rgb = np.stack([image, image, image], axis=0).astype(np.float32)

        recommendation = recommend_settings(
            rgb,
            pixel_size=10.0,
            source_hint={"is_true_color_rgb": False},
        )
        self.assertEqual(recommendation["feature_mode"], "Archaeological signature")
        self.assertEqual(recommendation["raster_family"], "archaeological magnetic raster")

    def test_validate_rgb_geotiff_accepts_rgba_with_alpha(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            raster_path = tmpdir / "rgba_alpha.tif"
            data = np.zeros((4, 32, 32), dtype=np.uint8)
            data[0] = 120
            data[1] = 100
            data[2] = 80
            data[3] = 255

            with rasterio.open(
                raster_path,
                "w",
                driver="GTiff",
                height=32,
                width=32,
                count=4,
                dtype=data.dtype,
                crs="EPSG:4326",
                transform=from_origin(-70.0, -10.0, 0.0001, 0.0001),
            ) as dst:
                dst.colorinterp = (ColorInterp.red, ColorInterp.green, ColorInterp.blue, ColorInterp.alpha)
                dst.write(data)

            # Should not raise
            validate_rgb_geotiff(str(raster_path))

    def test_cli_multi_file_support(self):
        import cli
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            raster_path1 = tmpdir / "img1.tif"
            raster_path2 = tmpdir / "img2.tif"
            out_dir = tmpdir / "out"

            data = np.zeros((96, 96), dtype=np.uint8)
            data[46:50, 18:78] = 255
            _write_test_raster(raster_path1, data)
            _write_test_raster(raster_path2, data)

            argv = [
                "-i", str(raster_path1), str(raster_path2),
                "-o", str(out_dir),
                "--profile", "Structural continuity",
                "--feature-mode", "Geological signature",
                "--radi", "2",
                "--gthr", "60",
                "--lthr", "8",
                "--fthr", "0.0",
                "--athr", "20.0",
                "--dthr", "10.0"
            ]

            exit_code = cli.main(argv)
            self.assertEqual(exit_code, 0)

            out1 = out_dir / "img1"
            out2 = out_dir / "img2"
            self.assertTrue(out1.exists())
            self.assertTrue(out2.exists())
            self.assertTrue((out1 / "mirage_report.json").exists())
            self.assertTrue((out2 / "mirage_report.json").exists())
            self.assertTrue((out1 / "lineaments.shp").exists())
            self.assertTrue((out2 / "lineaments.shp").exists())


if __name__ == "__main__":
    unittest.main()
