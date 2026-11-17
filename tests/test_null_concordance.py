"""Synthetic length-weighted concordance and rigid-placement null checks."""
import sys
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import LineString

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from evaluate_public import chance_fractions, observed_mask, samples, structural_null  # noqa: E402


TRANSFORM = (10, 0, 0, 0, -10, 1000)
VALID = np.ones((100, 100), dtype=bool)


def test_coincident_lines_have_positive_excess_and_small_p():
    points, _, weights = samples([LineString([(500, 100), (500, 900)])], spacing=5)
    result = structural_null(points, weights, points, VALID, TRANSFORM, tolerances=(25,))
    summary = result['summaries'][25]
    assert summary['matched_fraction'] == 1
    assert summary['excess'] > .8
    assert summary['excess_reference95'][0] > 0
    assert summary['p_upper'] < .01
    assert result['fractions'].shape == (1000, 1)
    assert np.min(result['retained']) >= .6


def test_unrelated_lines_have_non_small_p_and_reproducible_null():
    points, _, weights = samples([LineString([(750, 100), (750, 900)])], spacing=5)
    truth, _, _ = samples([LineString([(500, 0), (500, 1000)])], spacing=5)
    result = structural_null(points, weights, truth, VALID, TRANSFORM, tolerances=(25,))
    repeat = structural_null(points, weights, truth, VALID, TRANSFORM, tolerances=(25,))
    assert result['summaries'][25]['p_upper'] > .05
    np.testing.assert_array_equal(result['fractions'], repeat['fractions'])


def test_chance_area_known_strip_and_invalid_cells():
    # A vertical strip of width 200 through a 1000 by 1000 square has area 20%.
    truth, _, _ = samples([LineString([(500, -100), (500, 1100)])], spacing=1)
    assert chance_fractions(truth, VALID, TRANSFORM, (100,))[100] == pytest.approx(.2)
    valid = VALID.copy()
    valid[:, :20] = False
    assert chance_fractions(truth, valid, TRANSFORM, (100,))[100] == pytest.approx(.25)
    assert observed_mask(np.array([[5, 995], [505, 995], [1000, 995]]), valid, TRANSFORM).tolist() == [False, True, False]


def test_empty_detections_and_impossible_acceptance():
    truth = np.array([[500, 500]])
    result = structural_null(np.empty((0, 2)), np.array([]), truth, VALID, TRANSFORM)
    assert result['summaries'][500]['p_upper'] is None
    with pytest.raises(RuntimeError, match='accepted placements'):
        structural_null(truth, np.array([1.]), truth, VALID, TRANSFORM, max_attempts=0)
