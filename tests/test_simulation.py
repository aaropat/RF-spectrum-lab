import numpy as np
import pytest

from rf_analyzer.simulation import (
    CaptureConfig,
    SyntheticEmitter,
    demo_emitters,
    simulate_capture,
)


def test_simulation_is_deterministic():
    config = CaptureConfig(sample_count=8192, seed=3)
    assert np.array_equal(simulate_capture(config, demo_emitters(config.sample_rate_hz)),
                          simulate_capture(config, demo_emitters(config.sample_rate_hz)))


def test_seed_changes_noise():
    a = simulate_capture(CaptureConfig(sample_count=8192, seed=3), [])
    b = simulate_capture(CaptureConfig(sample_count=8192, seed=4), [])
    assert not np.array_equal(a, b)


def test_zero_noise_zero_emitters():
    config = CaptureConfig(sample_count=8192, noise_std=0)
    assert np.count_nonzero(simulate_capture(config, [])) == 0


def test_tone_magnitude_without_noise():
    config = CaptureConfig(sample_count=8192, noise_std=0)
    tone = SyntheticEmitter("T", "tone", 100_000, 100_000, 0.7)
    iq = simulate_capture(config, [tone])
    np.testing.assert_allclose(np.abs(iq), 0.7, atol=1e-6)


@pytest.mark.parametrize("config", [
    CaptureConfig(sample_rate_hz=0),
    CaptureConfig(sample_count=64),
    CaptureConfig(noise_std=-0.1),
    CaptureConfig(center_frequency_hz=-10),
])
def test_invalid_capture_configuration(config):
    with pytest.raises(ValueError):
        simulate_capture(config, [])


def test_out_of_band_emitter_rejected():
    emitter = SyntheticEmitter("Outside", "tone", 1_500_000, 1_500_000)
    with pytest.raises(ValueError, match="Nyquist"):
        simulate_capture(CaptureConfig(sample_count=8192), [emitter])


def test_invalid_active_interval():
    emitter = SyntheticEmitter("Burst", "tone", 1_000, 1_000,
                               start_fraction=0.8, stop_fraction=0.2)
    with pytest.raises(ValueError, match="Active time"):
        simulate_capture(CaptureConfig(sample_count=8192), [emitter])


def test_chirp_is_active_only_during_burst():
    config = CaptureConfig(sample_rate_hz=1_000_000, sample_count=8192, noise_std=0)
    emitter = SyntheticEmitter("Sweep", "chirp", -100_000, 100_000, 0.6, 0.25, 0.75)
    iq = simulate_capture(config, [emitter])
    assert np.count_nonzero(iq[:2048]) == 0
    assert np.count_nonzero(iq[2048:6144]) == 4096
    assert np.count_nonzero(iq[6144:]) == 0
