"""Safe, small-file IQ loading and simple export serialization."""

import csv
import io
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

from rf_analyzer.analysis import Detection, Spectrum, validate_iq

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_UPLOAD_SAMPLES = 262_144


def load_iq_bytes(content: bytes, filename: str) -> np.ndarray:
    """Parse an ordinary .npy complex array or CSV with I and Q columns.

    Rejects pickled numpy arrays, oversized files, and non-finite values.
    """
    if not content:
        raise ValueError("The uploaded file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("File exceeds the 8 MB upload limit.")
    suffix = Path(filename).suffix.lower()
    if suffix == ".npy":
        try:
            arr = np.load(io.BytesIO(content), allow_pickle=False)
        except (ValueError, OSError) as exc:
            raise ValueError("Invalid NumPy .npy data (pickled arrays are not permitted).") from exc
        if not np.iscomplexobj(arr):
            raise ValueError("The .npy file must contain a one-dimensional complex IQ array.")
    elif suffix == ".csv":
        try:
            text = content.decode("utf-8-sig")
            rows = csv.DictReader(io.StringIO(text))
            if not rows.fieldnames or not {"I", "Q"}.issubset(rows.fieldnames):
                raise ValueError("CSV must have columns named I,Q (case sensitive).")
            samples = []
            for row in rows:
                if len(samples) >= MAX_UPLOAD_SAMPLES:
                    raise ValueError("Uploaded IQ contains too many samples.")
                samples.append(complex(float(row["I"]), float(row["Q"])))
            arr = np.asarray(samples, dtype=np.complex64)
        except (UnicodeDecodeError, KeyError, TypeError, OverflowError) as exc:
            raise ValueError("Could not read the CSV's I,Q samples.") from exc
    else:
        raise ValueError("Only .npy and .csv IQ files are supported.")
    if arr.size > MAX_UPLOAD_SAMPLES:
        raise ValueError("Uploaded IQ contains too many samples.")
    return validate_iq(arr).astype(np.complex64)


def iq_npy_bytes(iq: np.ndarray) -> bytes:
    binary = io.BytesIO()
    np.save(binary, np.asarray(iq, dtype=np.complex64), allow_pickle=False)
    return binary.getvalue()


def detections_csv_bytes(detections: list[Detection]) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["frequency_hz", "offset_hz", "psd_db_per_hz_relative", "above_floor_db"])
    for d in detections:
        writer.writerow([f"{d.frequency_hz:.3f}", f"{d.offset_hz:.3f}",
                         f"{d.psd_db_hz:.3f}", f"{d.above_floor_db:.3f}"])
    return output.getvalue().encode("utf-8")


def spectrum_csv_bytes(spectrum: Spectrum) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["frequency_hz", "psd_db_per_hz_relative"])
    writer.writerows((f"{f:.3f}", f"{v:.5f}")
                     for f, v in zip(spectrum.frequency_hz, spectrum.psd_db_hz))
    return output.getvalue().encode("utf-8")


def report_json_bytes(
    *, sample_rate_hz: float, center_frequency_hz: float, sample_count: int,
    spectrum: Spectrum, detections: list[Detection], source: str,
) -> bytes:
    report = {
        "project": "RF Spectrum Lab",
        "source": source,
        "sample_rate_hz": sample_rate_hz,
        "center_frequency_hz": center_frequency_hz,
        "sample_count": sample_count,
        "noise_floor_db_per_hz_relative": spectrum.noise_floor_db_hz,
        "detector": "Welch PSD + thresholded local peaks",
        "disclaimer": "Relative spectral power. Not calibrated dBm, SNR or drone identification.",
        "detections": [asdict(detection) for detection in detections],
    }
    return json.dumps(report, indent=2, allow_nan=False).encode("utf-8")
