"""RF Spectrum Lab: interactive passive/offline signal-analysis dashboard.

Run from the project root with: streamlit run app.py
"""

import pandas as pd
import streamlit as st

from rf_analyzer.analysis import compute_spectrum, compute_waterfall, detect_peaks
from rf_analyzer.io import (
    detections_csv_bytes,
    iq_npy_bytes,
    load_iq_bytes,
    report_json_bytes,
    spectrum_csv_bytes,
)
from rf_analyzer.plotting import spectrum_figure, waterfall_figure, waveform_figure
from rf_analyzer.simulation import CaptureConfig, SyntheticEmitter, simulate_capture

st.set_page_config(page_title="RF Spectrum Lab", page_icon="📡", layout="wide",
                   initial_sidebar_state="expanded")
st.markdown("""
<style>
    .block-container {padding-top: 2.0rem; max-width: 1560px;}
    [data-testid="stMetric"] {background: #111d2c; border: 1px solid #233347;
        border-radius: 13px; padding: 15px 18px;}
    [data-testid="stMetricLabel"] {color: #9db3c9;}
    .eyebrow {letter-spacing: 0.18em; color: #66e7bf; font-size: .78rem;
        font-weight: 700; margin-bottom: .3rem;}
    .subtitle {color: #9dafc3; font-size: 1rem; margin-top: -.3rem;
        margin-bottom: 1.3rem;}
    .tiny-note {color: #8da5b8; font-size: .85rem; line-height: 1.5;}
    .stButton button, [data-testid="stDownloadButton"] button {border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="eyebrow">PYTHON · DIGITAL SIGNAL PROCESSING · PORTFOLIO DEMO</div>',
            unsafe_allow_html=True)
st.title("📡 RF Spectrum Lab")
st.markdown('<div class="subtitle">Explore complex IQ samples, frequency-domain power, '
            'and narrowband peak detection — without any RF hardware.</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("Capture controls")
    mode = st.radio("Data source", ["Synthetic signals", "Upload IQ file"], horizontal=True)
    sample_rate_mhz = st.number_input("Sample rate (MHz)", min_value=0.25, max_value=20.0,
                                      value=2.0, step=0.25, format="%.2f")
    center_mhz = st.number_input("RF center frequency (MHz)", min_value=100.0,
                                  max_value=10_000.0, value=2437.0, step=1.0, format="%.2f")
    sample_rate_hz = sample_rate_mhz * 1e6
    center_hz = center_mhz * 1e6
    uploaded = None
    emitters = []
    source_label = "simulated"
    if mode == "Synthetic signals":
        sample_count = st.select_slider("IQ samples", options=[8192, 16384, 32768, 65536, 131072],
                                        value=65536)
        noise_std = st.slider("Noise RMS (linear units)", 0.0, 0.6, 0.15, step=0.01)
        seed = st.number_input("Random seed", min_value=0, max_value=1000000, value=42, step=1)
        st.divider()
        st.subheader("Simulated emitters")
        st.caption("Offsets are percentages of Nyquist (half the sample rate).")
        enable_a = st.checkbox("Beacon A · continuous tone", value=True)
        a_offset = st.slider("Beacon A offset (%)", -90, 90, -64, disabled=not enable_a)
        a_amp = st.slider("Beacon A amplitude", 0.0, 2.0, 0.85, step=0.05, disabled=not enable_a)
        enable_b = st.checkbox("Beacon B · continuous tone", value=True)
        b_offset = st.slider("Beacon B offset (%)", -90, 90, 42, disabled=not enable_b)
        b_amp = st.slider("Beacon B amplitude", 0.0, 2.0, 0.50, step=0.05, disabled=not enable_b)
        enable_chirp = st.checkbox("Sweeper C · linear chirp burst", value=True)
        chirp_range = st.slider("Chirp sweep (%)", -90, 90, (-22, 26),
                                 disabled=not enable_chirp)
        chirp_amp = st.slider("Chirp amplitude", 0.0, 2.0, 0.36, step=0.05,
                              disabled=not enable_chirp)
        nyquist = sample_rate_hz / 2
        if enable_a:
            frequency = a_offset / 100 * nyquist
            emitters.append(SyntheticEmitter("Beacon A", "tone", frequency, frequency, a_amp))
        if enable_b:
            frequency = b_offset / 100 * nyquist
            emitters.append(SyntheticEmitter("Beacon B", "tone", frequency, frequency, b_amp))
        if enable_chirp:
            emitters.append(SyntheticEmitter("Sweeper C", "chirp",
                                             chirp_range[0] / 100 * nyquist,
                                             chirp_range[1] / 100 * nyquist,
                                             chirp_amp, 0.18, 0.88))
    else:
        uploaded = st.file_uploader("Upload a complex .npy array or CSV with I,Q columns",
                                   type=["npy", "csv"], help="8 MB maximum; 1,024–262,144 IQ samples.")
        st.caption("Your file is processed locally by the running Streamlit app. "
                   "You provide the sampling rate and RF center frequency above.")
        source_label = "uploaded"
    st.divider()
    st.subheader("Peak detection")
    fft_size = st.select_slider("Welch FFT size", options=[1024, 2048, 4096, 8192], value=4096)
    threshold = st.slider("Minimum above-floor power (dB)", min_value=6.0, max_value=30.0,
                          value=12.0, step=1.0)
    min_separation_khz = st.slider("Minimum spacing between peaks (kHz)", 1, 100, 20)
    st.caption("The detector finds narrowband energy peaks. It does not identify "
               "protocols, devices, or drones.")

if mode == "Upload IQ file" and uploaded is None:
    st.info("Upload a supported IQ file in the sidebar to view its spectrum. "
            "For the ready-to-use demo, switch to **Synthetic signals**.")
    with st.expander("Accepted IQ formats"):
        st.code("I,Q\n0.12,-0.34\n0.17,0.28\n...", language="csv")
        st.code('import numpy as np\nnp.save("capture.npy", my_complex_array)', language="python")
    st.stop()

try:
    if mode == "Synthetic signals":
        config = CaptureConfig(sample_rate_hz, center_hz, sample_count,
                               noise_std, int(seed))
        iq = simulate_capture(config, emitters)
    else:
        iq = load_iq_bytes(uploaded.getvalue(), uploaded.name)
    spectrum = compute_spectrum(iq, sample_rate_hz, center_hz, fft_size=fft_size)
    waterfall = compute_waterfall(iq, sample_rate_hz, center_hz, fft_size=1024)
    detections = detect_peaks(spectrum, threshold_above_floor_db=threshold,
                               min_prominence_db=6.0,
                               min_separation_hz=min_separation_khz * 1e3)
except (ValueError, TypeError, OSError) as error:
    st.error(f"Could not analyze this capture: {error}")
    st.stop()

strongest = max((d.above_floor_db for d in detections), default=None)
metrics = st.columns(4)
metrics[0].metric("Narrowband peaks", str(len(detections)))
metrics[1].metric("Median noise floor", f"{spectrum.noise_floor_db_hz:.1f} dB/Hz")
metrics[2].metric("Strongest peak above floor", f"{strongest:.1f} dB" if strongest is not None else "—")
metrics[3].metric("Capture length", f"{iq.size / sample_rate_hz * 1e3:.1f} ms")

st.subheader("Signal analysis")
tab_spectrum, tab_waterfall, tab_iq = st.tabs(["Frequency spectrum", "Waterfall / spectrogram", "IQ waveform"])
with tab_spectrum:
    st.plotly_chart(spectrum_figure(spectrum, detections, threshold), use_container_width=True)
    st.caption("Welch power spectral density; RF frequency = center frequency + baseband offset. "
               "Dashed line shows the selected detection threshold.")
with tab_waterfall:
    st.plotly_chart(waterfall_figure(waterfall), use_container_width=True)
    st.caption("A continuous tone appears as a horizontal line; a chirp burst sweeps across frequencies over time.")
with tab_iq:
    st.plotly_chart(waveform_figure(iq, sample_rate_hz), use_container_width=True)
    st.caption("Complex samples shown as in-phase (I) and quadrature (Q) components; downsampled for display.")

st.subheader("Peak detections")
if detections:
    table = pd.DataFrame([{
        "Frequency (MHz)": round(d.frequency_hz / 1e6, 5),
        "Offset (kHz)": round(d.offset_hz / 1e3, 2),
        "Relative PSD (dB/Hz)": round(d.psd_db_hz, 2),
        "Above noise floor (dB)": round(d.above_floor_db, 2),
    } for d in detections])
    st.dataframe(table, use_container_width=True, hide_index=True)
else:
    st.info("No narrowband peaks above the current threshold. Try lowering the threshold "
            "or enabling one of the simulated tones.")

if mode == "Synthetic signals":
    with st.expander("Show simulated ground truth (not inferred by the detector)"):
        if emitters:
            st.dataframe(pd.DataFrame([{
                "Emitter": e.name,
                "Type": e.kind,
                "Start RF frequency (MHz)": round((center_hz + e.start_offset_hz) / 1e6, 5),
                "End RF frequency (MHz)": round((center_hz + e.end_offset_hz) / 1e6, 5),
                "Amplitude": e.amplitude,
                "Active interval (%)": f"{100 * e.start_fraction:.0f}–{100 * e.stop_fraction:.0f}",
            } for e in emitters]), use_container_width=True, hide_index=True)
        else:
            st.write("No synthetic emitters are enabled — only noise is present.")
        st.caption("Ground truth comes from the simulator; real-world RF signals "
                   "would not have these labels.")

st.subheader("Export results")
report = report_json_bytes(
    sample_rate_hz=sample_rate_hz, center_frequency_hz=center_hz,
    sample_count=int(iq.size), spectrum=spectrum, detections=detections,
    source=source_label,
)
exports = st.columns(4)
exports[0].download_button("Download detections CSV", data=detections_csv_bytes(detections),
                           file_name="detections.csv", mime="text/csv", use_container_width=True)
exports[1].download_button("Download spectrum CSV", data=spectrum_csv_bytes(spectrum),
                           file_name="spectrum.csv", mime="text/csv", use_container_width=True)
exports[2].download_button("Download JSON report", data=report,
                           file_name="report.json", mime="application/json", use_container_width=True)
exports[3].download_button("Download IQ (.npy)", data=iq_npy_bytes(iq),
                           file_name="capture_iq.npy", mime="application/octet-stream", use_container_width=True)

st.divider()
st.markdown("""
<div class="tiny-note">
<b>Engineering note:</b> All powers are <b>relative, uncalibrated spectral densities</b>
(dB referenced to 1 arbitrary unit²/Hz), never dBm. The above-floor values are
spectral excess, not calibrated receiver SNR. This educational tool neither transmits
nor identifies drones or specific radio protocols. It is an independent portfolio project.
</div>
""", unsafe_allow_html=True)
