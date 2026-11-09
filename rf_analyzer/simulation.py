"""Deterministic, offline generation of complex IQ radio signals.

All simulated frequencies are offsets from the configured RF center frequency.
No hardware is used, and nothing is transmitted or received.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np


@dataclass(frozen=True)
class CaptureConfig:
    sample_rate_hz: float = 2_000_000.0
    center_frequency_hz: float = 2_437_000_000.0
    sample_count: int = 65_536
    noise_std: float = 0.15
    seed: int = 42

    def validate(self) -> None:
        if not np.isfinite(self.sample_rate_hz) or self.sample_rate_hz <= 0:
            raise ValueError("Sample rate must be a positive, finite number.")
        if not np.isfinite(self.center_frequency_hz) or self.center_frequency_hz <= 0:
            raise ValueError("Center frequency must be a positive, finite number.")
        if not isinstance(self.sample_count, int) or not (1_024 <= self.sample_count <= 1_048_576):
            raise ValueError("Sample count must be an integer from 1,024 to 1,048,576.")
        if not np.isfinite(self.noise_std) or self.noise_std < 0:
            raise ValueError("Noise standard deviation must be finite and nonnegative.")
        if not isinstance(self.seed, int) or self.seed < 0:
            raise ValueError("Random seed must be a nonnegative integer.")


@dataclass(frozen=True)
class SyntheticEmitter:
    name: str
    kind: Literal["tone", "chirp"]
    start_offset_hz: float
    end_offset_hz: float
    amplitude: float = 1.0
    start_fraction: float = 0.0
    stop_fraction: float = 1.0

    def validate(self, sample_rate_hz: float) -> None:
        if self.kind not in ("tone", "chirp"):
            raise ValueError(f"Unsupported signal kind: {self.kind}")
        if not self.name.strip():
            raise ValueError("Signal name cannot be empty.")
        for freq in (self.start_offset_hz, self.end_offset_hz):
            if not np.isfinite(freq) or not (-sample_rate_hz / 2 < freq < sample_rate_hz / 2):
                raise ValueError(f"Signal '{self.name}' lies outside the Nyquist bandwidth.")
        if self.kind == "tone" and self.start_offset_hz != self.end_offset_hz:
            raise ValueError("A tone must have the same start and end frequencies.")
        if not np.isfinite(self.amplitude) or self.amplitude < 0:
            raise ValueError("Amplitude must be finite and nonnegative.")
        if not (0 <= self.start_fraction < self.stop_fraction <= 1):
            raise ValueError("Active time fractions must satisfy 0 <= start < stop <= 1.")


def demo_emitters(sample_rate_hz: float) -> list[SyntheticEmitter]:
    """Two narrowband signals and one shorter frequency sweep."""
    return [
        SyntheticEmitter("Beacon A", "tone", -0.32 * sample_rate_hz, -0.32 * sample_rate_hz, 0.85),
        SyntheticEmitter("Beacon B", "tone", 0.21 * sample_rate_hz, 0.21 * sample_rate_hz, 0.50),
        SyntheticEmitter("Sweeper C", "chirp", -0.11 * sample_rate_hz, 0.13 * sample_rate_hz,
                         0.36, 0.18, 0.88),
    ]


def simulate_capture(config: CaptureConfig, emitters: Sequence[SyntheticEmitter]) -> np.ndarray:
    """Return a reproducible complex64 IQ array.

    noise_std is the RMS magnitude of complex circular Gaussian noise.
    Frequencies are in Hz relative to the center frequency; amplitudes are
    arbitrary linear voltage units, not calibrated signal powers.
    """
    config.validate()
    for emitter in emitters:
        emitter.validate(config.sample_rate_hz)

    rng = np.random.default_rng(config.seed)
    n = config.sample_count
    noise_scale = config.noise_std / np.sqrt(2.0)
    iq = noise_scale * (rng.standard_normal(n) + 1j * rng.standard_normal(n))
    dt = 1.0 / config.sample_rate_hz

    for emitter in emitters:
        # Time gate, using half-open sample intervals for consistent lengths.
        first = int(np.floor(emitter.start_fraction * n))
        last = int(np.ceil(emitter.stop_fraction * n))
        active_count = last - first
        local_time = np.arange(active_count, dtype=np.float64) * dt
        if emitter.kind == "tone":
            phase = 2 * np.pi * emitter.start_offset_hz * local_time
        else:
            # Analytic linear FM chirp: integral of f(t) = f0 + (f1-f0)t/T.
            duration = active_count * dt
            slope = (emitter.end_offset_hz - emitter.start_offset_hz) / duration
            phase = 2 * np.pi * (emitter.start_offset_hz * local_time + 0.5 * slope * local_time ** 2)
        iq[first:last] += emitter.amplitude * np.exp(1j * phase)

    return iq.astype(np.complex64)
