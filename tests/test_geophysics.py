import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import geopandas as gpd
import rasterio
from rasterio.transform import from_origin

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from line_core import (
    first_vertical_derivative,
    second_vertical_derivative,
    compute_potential_field_filter,
    fit_quadratic_derivatives,
    detect_curvature_features,
    lineament_extraction_multiband
)
from ai.parameter_advisor import recommend_settings
from pipeline import run_extraction_job


def _write_test_raster(path, data, count=1):
    if data.ndim == 2:
        if count == 1:
            data = data[np.newaxis, :, :]
        else:
            data = np.stack([data, data, data], axis=0)
    
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=data.shape[1],
        width=data.shape[2],
        count=data.shape[0],
        dtype=data.dtype,
        crs="EPSG:32718",  # Projected UTM (Peru Zone 18S)
        transform=from_origin(300000.0, 8900000.0, 10.0, 10.0),  # 10m cell size
    ) as dst:
        dst.write(data)


class GeophysicsTests(unittest.TestCase):
    def test_vertical_derivatives(self):
        # Create a simple 2D sine wave grid
        y, x = np.indices((64, 64))
        img = np.sin(x * 0.2) + np.cos(y * 0.2)
        
        vdr1 = first_vertical_derivative(img, pixel_size=10.0)
        vdr2 = second_vertical_derivative(img, pixel_size=10.0)
        
        self.assertEqual(vdr1.shape, img.shape)
        self.assertEqual(vdr2.shape, img.shape)
        # FFT of continuous sin/cos shouldn't have NaNs or Inf
        self.assertTrue(np.all(np.isfinite(vdr1)))
        self.assertTrue(np.all(np.isfinite(vdr2)))

    def test_geophysics_filters(self):
        img = np.zeros((32, 32), dtype=np.float32)
        img[10:22, 10:22] = 1.0
        
        tdr = compute_potential_field_filter(img, "TDR", pixel_size=1.0)
        analytic_sig = compute_potential_field_filter(img, "AS", pixel_size=1.0)
        thdr = compute_potential_field_filter(img, "THDR", pixel_size=1.0)
        
        self.assertEqual(tdr.shape, img.shape)
        self.assertEqual(analytic_sig.shape, img.shape)
        self.assertEqual(thdr.shape, img.shape)
        
        # Tilt angle is bounded between -pi/2 and pi/2
        self.assertTrue(np.all(tdr >= -np.pi/2))
        self.assertTrue(np.all(tdr <= np.pi/2))

    def test_quadratic_fitting_and_trough_detection(self):
        # Create a synthetic trough (valley along y axis: min at x=0)
        y, x = np.indices((9, 9))
        dist_x = x - 4  # Center column is x = 4
        # z = x^2 (positive second derivative, so it's a valley/trough)
        img = (dist_x**2).astype(np.float32)
        
        a, b, c, d, e = fit_quadratic_derivatives(img, pixel_size=1.0, stride=1)
        
        # Check coefficients at the center (4, 4)
        # z = 1 * x^2 + 0 * y^2 + 0 * xy + 0 * x + 0 * y + 0
        # So a should be positive (~1.0), and others should be close to 0
        self.assertAlmostEqual(a[4, 4], 1.0, places=2)
        self.assertAlmostEqual(b[4, 4], 0.0, places=2)
        self.assertAlmostEqual(c[4, 4], 0.0, places=2)
        self.assertAlmostEqual(d[4, 4], 0.0, places=2)
        self.assertAlmostEqual(e[4, 4], 0.0, places=2)
        
        # Trough detection should mark the center column
        mask_trough = detect_curvature_features(img, pixel_size=1.0, stride=1, extract_type="trough", threshold=0.01)
        self.assertTrue(mask_trough[4, 4])  # Center cell must be detected as trough
        
        # Ridge detection should NOT mark it
        mask_ridge = detect_curvature_features(img, pixel_size=1.0, stride=1, extract_type="ridge", threshold=0.01)
        self.assertFalse(mask_ridge[4, 4])

    def test_parameter_advisor_geophysics_recommendation(self):
        # Create a synthetic magnetic grid: high variance, strong linear structure
        y, x = np.indices((128, 128))
        dikes = (np.abs(x - 64) < 4).astype(np.float32) + (np.abs(y - x) < 3).astype(np.float32)
        rng = np.random.default_rng(42)
        noise = rng.normal(0.0, 0.05, dikes.shape).astype(np.float32)
        image = np.clip(dikes + noise, 0.0, 1.0)
        
        # Source hint that it's a potential field / non-true color
        source_hint = {"is_true_color_rgb": False}
        
        # Call recommend_settings (we use a 3-band array to trigger graylike_rgb)
        rgb_data = np.stack([image, image, image], axis=0)
        recommendation = recommend_settings(rgb_data, pixel_size=10.0, source_hint=source_hint)
        
        self.assertEqual(recommendation["feature_mode"], "Geophysics Potential Fields")
        self.assertIn(recommendation["profile"], {"Magnetometry", "Gravimetry"})
        
    def test_geophysics_pipeline_job(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            raster_path = tmpdir / "magnetic_survey.tif"
            out_dir = tmpdir / "out"
            
            # Create a simple synthetic line (dike) on a grid
            y, x = np.indices((96, 96))
            dike = (np.abs(x - 48) < 4).astype(np.float32) * 255.0
            _write_test_raster(raster_path, dike)
            
            summary = run_extraction_job(
                geotiff=str(raster_path),
                out_dir=str(out_dir),
                radi=2,
                gthr=60,
                lthr=8,
                fthr=0.0,
                athr=20.0,
                dthr=10.0,
                extraction_mode="geophysics",
                geophys_filters="TDR,AS",
                geophys_extract_type="trough",
                geophys_stride=1
            )
            
            self.assertTrue(Path(summary["outputs"]["report"]).exists())
            self.assertTrue(Path(summary["outputs"]["lineaments"]).exists())
            self.assertTrue(Path(summary["outputs"]["geopackage"]).exists())
            
            # Check shapefile contents
            gdf = gpd.read_file(summary["outputs"]["lineaments"])
            self.assertIn("gp_filt", gdf.columns)
            self.assertIn("gp_type", gdf.columns)
            self.assertIn("gp_stride", gdf.columns)
            self.assertGreaterEqual(len(gdf), 1)


if __name__ == "__main__":
    unittest.main()
