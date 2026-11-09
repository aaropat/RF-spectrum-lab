import io
import json

import numpy as np
import pytest

from rf_analyzer.analysis import compute_spectrum, detect_peaks
from rf_analyzer.io import (
    detections_csv_bytes,
    iq_npy_bytes,
    load_iq_bytes,
    report_json_bytes,
    spectrum_csv_bytes,
)


def test_npy_round_trip():
    iq = (np.ones(2048) + 1j * np.arange(2048)).astype(np.complex64)
    decoded = load_iq_bytes(iq_npy_bytes(iq), "sample.npy")
    assert np.array_equal(decoded, iq)


def test_csv_iq():
    content = b"I,Q\n" + b"0.5,-0.25\n" * 1024
    result = load_iq_bytes(content, "capture.csv")
    assert result.shape == (1024,)
    assert result[0] == complex(0.5, -0.25)


def test_csv_missing_columns():
    with pytest.raises(ValueError, match="columns"):
        load_iq_bytes(b"x,y\n1,2\n" * 2000, "data.csv")


def test_npy_real_rejected():
    binary = io.BytesIO()
    np.save(binary, np.ones(2048, dtype=float))
    with pytest.raises(ValueError, match="complex"):
        load_iq_bytes(binary.getvalue(), "real.npy")


def test_npy_pickle_rejected():
    binary = io.BytesIO()
    np.save(binary, np.array([{"bad": True}], dtype=object), allow_pickle=True)
    with pytest.raises(ValueError, match="pickled"):
        load_iq_bytes(binary.getvalue(), "pickled.npy")


def test_too_few_samples_rejected():
    with pytest.raises(ValueError, match="at least"):
        load_iq_bytes(b"I,Q\n1.0,2.0\n", "short.csv")


def test_csv_and_json_exports():
    iq = np.exp(2j * np.pi * 0.1 * np.arange(8192))
    spectrum = compute_spectrum(iq, 1e6, 1e9)
    peaks = detect_peaks(spectrum)
    assert detections_csv_bytes(peaks).startswith(b"frequency_hz,offset_hz")
    assert len(spectrum_csv_bytes(spectrum).splitlines()) == len(spectrum.frequency_hz) + 1
    report = json.loads(report_json_bytes(sample_rate_hz=1e6, center_frequency_hz=1e9,
                                          sample_count=len(iq), spectrum=spectrum,
                                          detections=peaks, source="simulated"))
    assert report["sample_count"] == 8192
    assert len(report["detections"]) == len(peaks)
