import numpy as np
import pytest
from src.metrics import calibrate, fit_calibrator, metrics, select_threshold

def test_threshold_regression_is_finite_and_keeps_sensitivity():
    y = np.array([0, 0, 0, 0, 1, 1])
    probabilities = np.array([.1, .2, .3, .4, .8, .9])
    threshold = select_threshold(y, probabilities)
    report = metrics(y, probabilities, threshold)
    assert np.isfinite(threshold)
    assert report["sensitivity"] == 1
    assert report["specificity"] >= .9

def test_unattainable_positive_operating_point_reports_zero_sensitivity():
    threshold = select_threshold([0, 1], [.9, .1])
    assert np.isfinite(threshold)
    assert metrics([0, 1], [.9, .1], threshold)["sensitivity"] == 0

def test_calibration_is_fitted_finite_and_monotonic():
    scores = np.array([-3., -2., -1., 0., 1., 2., 3., 4.])
    calibration = fit_calibrator(scores, [0, 0, 1, 0, 1, 1, 0, 1])
    probabilities = calibrate(scores, calibration)
    assert calibration["scale"] > 0
    assert np.isfinite(probabilities).all()
    assert (np.diff(probabilities) > 0).all()
    with pytest.raises(ValueError):
        fit_calibrator([0., 1.], [1, 1])
