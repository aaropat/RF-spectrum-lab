"""Reproducible headless demo: python -m rf_analyzer.cli --output outputs/demo."""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from rf_analyzer.analysis import compute_spectrum, compute_waterfall, detect_peaks
from rf_analyzer.io import (
    detections_csv_bytes,
    iq_npy_bytes,
    report_json_bytes,
    spectrum_csv_bytes,
)
from rf_analyzer.simulation import CaptureConfig, demo_emitters, simulate_capture


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simulate and inspect a complex-baseband RF capture.")
    parser.add_argument("--output", type=Path, default=Path("outputs/demo"), help="Output folder")
    parser.add_argument("--center-mhz", type=float, default=2437.0)
    parser.add_argument("--sample-rate-mhz", type=float, default=2.0)
    parser.add_argument("--samples", type=int, default=65_536)
    parser.add_argument("--noise", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--threshold-db", type=float, default=12.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = CaptureConfig(
        sample_rate_hz=args.sample_rate_mhz * 1e6,
        center_frequency_hz=args.center_mhz * 1e6,
        sample_count=args.samples, noise_std=args.noise, seed=args.seed,
    )
    iq = simulate_capture(config, demo_emitters(config.sample_rate_hz))
    spectrum = compute_spectrum(iq, config.sample_rate_hz, config.center_frequency_hz)
    waterfall = compute_waterfall(iq, config.sample_rate_hz, config.center_frequency_hz)
    detections = detect_peaks(spectrum, threshold_above_floor_db=args.threshold_db)
    args.output.mkdir(parents=True, exist_ok=True)

    (args.output / "iq.npy").write_bytes(iq_npy_bytes(iq))
    (args.output / "spectrum.csv").write_bytes(spectrum_csv_bytes(spectrum))
    (args.output / "detections.csv").write_bytes(detections_csv_bytes(detections))
    (args.output / "report.json").write_bytes(report_json_bytes(
        sample_rate_hz=config.sample_rate_hz,
        center_frequency_hz=config.center_frequency_hz,
        sample_count=config.sample_count, spectrum=spectrum,
        detections=detections, source="simulated"))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), constrained_layout=True)
    ax1.plot(spectrum.frequency_hz / 1e6, spectrum.psd_db_hz, lw=1.05, label="Welch PSD")
    ax1.axhline(spectrum.noise_floor_db_hz + args.threshold_db, linestyle="--", color="orange",
                label="Detection threshold")
    if detections:
        ax1.scatter([d.frequency_hz / 1e6 for d in detections],
                    [d.psd_db_hz for d in detections], c="red", zorder=3, label="Detections")
    ax1.set(xlabel="RF frequency (MHz)", ylabel="Relative PSD (dB/Hz)", title="Spectrum")
    ax1.grid(alpha=0.2)
    ax1.legend()
    ax2.pcolormesh(waterfall.time_s * 1e3, waterfall.frequency_hz / 1e6,
                   waterfall.psd_db_hz, shading="auto", cmap="viridis", rasterized=True)
    ax2.set(xlabel="Time (ms)", ylabel="RF frequency (MHz)", title="Waterfall / Spectrogram")
    fig.suptitle("RF Spectrum Lab · Synthetic IQ capture", fontsize=14, fontweight="bold")
    fig.savefig(args.output / "preview.png", dpi=130)
    plt.close(fig)

    print(f"Saved simulated capture, analysis and figures to: {args.output.resolve()}")
    print(f"Noise floor: {spectrum.noise_floor_db_hz:.1f} relative dB/Hz")
    print(f"Peak detections: {len(detections)}")
    for det in detections:
        print(f"  {det.frequency_hz / 1e6:.4f} MHz   +{det.above_floor_db:.1f} dB above floor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
