"""Frequency-domain analysis and reproducible relative-energy peak detection."""

from dataclasses import dataclass

import numpy as np
from scipy import signal

_EPS = np.finfo(np.float64).tiny


@dataclass(frozen=True)
class Spectrum:
    frequency_hz: np.ndarray
    psd_db_hz: np.ndarray
    noise_floor_db_hz: float
    center_frequency_hz: float
    bin_width_hz: float


@dataclass(frozen=True)
class Waterfall:
    frequency_hz: np.ndarray
    time_s: np.ndarray
    psd_db_hz: np.ndarray  # (frequency bins, time windows)


@dataclass(frozen=True)
class Detection:
    frequency_hz: float
    offset_hz: float
    psd_db_hz: float
    above_floor_db: float


def validate_iq(iq: np.ndarray) -> np.ndarray:
    arr = np.asarray(iq)
    if arr.ndim != 1 or arr.size < 1_024:
        raise ValueError("IQ data must be one-dimensional and contain at least 1,024 samples.")
    if not np.issubdtype(arr.dtype, np.number):
        raise ValueError("IQ data must contain numeric samples.")
    if not np.all(np.isfinite(arr)):
        raise ValueError("IQ samples must not contain NaN or infinity.")
    return arr.astype(np.complex128, copy=False)


def _validate_frequency_params(sample_rate_hz: float, center_frequency_hz: float) -> None:
    if not np.isfinite(sample_rate_hz) or sample_rate_hz <= 0:
        raise ValueError("Sample rate must be positive and finite.")
    if not np.isfinite(center_frequency_hz) or center_frequency_hz <= 0:
        raise ValueError("Center frequency must be positive and finite.")


def compute_spectrum(
    iq: np.ndarray,
    sample_rate_hz: float,
    center_frequency_hz: float,
    fft_size: int = 4_096,
) -> Spectrum:
    """Welch-averaged, two-sided complex-IQ PSD in relative dB/Hz.

    These dB values represent 10log10(power spectral density / 1 unit²/Hz).
    They are *not* calibrated dBm or radio receiver power readings.
    """
    _validate_frequency_params(sample_rate_hz, center_frequency_hz)
    iq = validate_iq(iq)
    if not isinstance(fft_size, int) or fft_size < 256:
        raise ValueError("fft_size must be an integer >= 256.")
    segment = min(fft_size, iq.size)
    freq, psd = signal.welch(
        iq,
        fs=sample_rate_hz,
        window="hann",
        nperseg=segment,
        noverlap=segment // 2,
        detrend=False,
        scaling="density",
        return_onesided=False,
        average="mean",
    )
    frequency_hz = np.fft.fftshift(freq) + center_frequency_hz
    psd_db_hz = 10 * np.log10(np.maximum(np.fft.fftshift(psd), _EPS))
    # Robust median prevents strong, narrowband signals from setting the floor.
    noise_floor_db_hz = float(np.median(psd_db_hz))
    return Spectrum(frequency_hz, psd_db_hz, noise_floor_db_hz,
                    center_frequency_hz, sample_rate_hz / segment)


def detect_peaks(
    spectrum: Spectrum,
    threshold_above_floor_db: float = 12.0,
    min_prominence_db: float = 6.0,
    min_separation_hz: float = 20_000.0,
    max_detections: int = 10,
) -> list[Detection]:
    """Find local PSD peaks above the estimated global background.

    This is a narrowband peak detector, not a signal classifier or a drone
    detector. Above-floor values are relative spectral excess, not true SNR.
    """
    if not np.isfinite(threshold_above_floor_db) or threshold_above_floor_db < 0:
        raise ValueError("Threshold must be finite and nonnegative.")
    if not np.isfinite(min_prominence_db) or min_prominence_db < 0:
        raise ValueError("Prominence must be finite and nonnegative.")
    if not np.isfinite(min_separation_hz) or min_separation_hz < 0:
        raise ValueError("Peak spacing must be finite and nonnegative.")
    if not isinstance(max_detections, int) or max_detections < 1:
        raise ValueError("max_detections must be a positive integer.")
    spacing_bins = max(1, int(np.ceil(min_separation_hz / spectrum.bin_width_hz)))
    peaks, _ = signal.find_peaks(
        spectrum.psd_db_hz,
        height=spectrum.noise_floor_db_hz + threshold_above_floor_db,
        prominence=min_prominence_db,
        distance=spacing_bins,
    )
    peaks = sorted(peaks, key=lambda i: spectrum.psd_db_hz[i], reverse=True)[:max_detections]
    return [
        Detection(
            frequency_hz=float(spectrum.frequency_hz[i]),
            offset_hz=float(spectrum.frequency_hz[i] - spectrum.center_frequency_hz),
            psd_db_hz=float(spectrum.psd_db_hz[i]),
            above_floor_db=float(spectrum.psd_db_hz[i] - spectrum.noise_floor_db_hz),
        ) for i in peaks
    ]


def compute_waterfall(
    iq: np.ndarray,
    sample_rate_hz: float,
    center_frequency_hz: float,
    fft_size: int = 1_024,
) -> Waterfall:
    """Generate a time-frequency spectrogram for complex IQ data."""
    _validate_frequency_params(sample_rate_hz, center_frequency_hz)
    iq = validate_iq(iq)
    if not isinstance(fft_size, int) or fft_size < 256:
        raise ValueError("fft_size must be an integer >= 256.")
    segment = min(fft_size, iq.size)
    frequencies, times, power = signal.spectrogram(
        iq,
        fs=sample_rate_hz,
        window="hann",
        nperseg=segment,
        noverlap=segment * 3 // 4,
        detrend=False,
        scaling="density",
        return_onesided=False,
        mode="psd",
    )
    frequencies = np.fft.fftshift(frequencies) + center_frequency_hz
    power = np.fft.fftshift(power, axes=0)
    return Waterfall(frequencies, times, 10 * np.log10(np.maximum(power, _EPS)))
