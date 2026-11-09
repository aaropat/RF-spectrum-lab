"""Plotly figures shared by the interactive Streamlit app."""

import numpy as np
import plotly.graph_objects as go

from rf_analyzer.analysis import Detection, Spectrum, Waterfall

BG = "#0e1826"
GRID = "rgba(176, 196, 218, 0.12)"
GREEN = "#66e7bf"
GOLD = "#f8c46c"


def style_figure(fig: go.Figure, *, height: int = 410) -> go.Figure:
    fig.update_layout(
        template="plotly_dark", height=height,
        paper_bgcolor=BG, plot_bgcolor=BG,
        margin={"l": 22, "r": 22, "t": 24, "b": 34},
        font={"family": "Arial, sans-serif", "color": "#dce7f3"},
        legend={"orientation": "h", "y": 1.10, "x": 0},
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID)
    return fig


def spectrum_figure(spectrum: Spectrum, detections: list[Detection], threshold_db: float) -> go.Figure:
    f = spectrum.frequency_hz / 1e6
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=f, y=spectrum.psd_db_hz, mode="lines", name="Welch PSD",
        line={"color": GREEN, "width": 1.7},
        hovertemplate="%{x:.4f} MHz<br>%{y:.1f} dB/Hz<extra></extra>",
    ))
    fig.add_hline(
        y=spectrum.noise_floor_db_hz + threshold_db,
        line={"color": GOLD, "width": 1.5, "dash": "dash"},
        annotation_text="Detection threshold", annotation_position="top right",
        annotation_font_color=GOLD,
    )
    if detections:
        fig.add_trace(go.Scatter(
            x=[d.frequency_hz / 1e6 for d in detections],
            y=[d.psd_db_hz for d in detections], mode="markers", name="Peak detections",
            marker={"size": 11, "color": GOLD, "line": {"width": 2, "color": BG}},
            hovertemplate="%{x:.4f} MHz<br>%{y:.1f} dB/Hz<extra>Peak</extra>",
        ))
    fig.update_xaxes(title_text="RF frequency (MHz)")
    fig.update_yaxes(title_text="Relative PSD (dB/Hz)")
    return style_figure(fig)


def waterfall_figure(waterfall: Waterfall) -> go.Figure:
    fig = go.Figure(go.Heatmap(
        x=waterfall.time_s * 1e3,
        y=waterfall.frequency_hz / 1e6,
        z=waterfall.psd_db_hz,
        colorscale="Turbo",
        colorbar={"title": "dB/Hz", "len": 0.95, "thickness": 14},
        hovertemplate="Time %{x:.2f} ms<br>Frequency %{y:.4f} MHz<br>PSD %{z:.1f} dB/Hz<extra></extra>",
    ))
    fig.update_xaxes(title_text="Time (ms)")
    fig.update_yaxes(title_text="RF frequency (MHz)")
    return style_figure(fig, height=490)


def waveform_figure(iq: np.ndarray, sample_rate_hz: float) -> go.Figure:
    step = max(1, int(np.ceil(iq.size / 2_200)))
    indices = np.arange(0, iq.size, step)
    times_ms = indices / sample_rate_hz * 1e3
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=times_ms, y=iq[indices].real,
                             mode="lines", name="In-phase (I)",
                             line={"width": 1.2, "color": GREEN}))
    fig.add_trace(go.Scatter(x=times_ms, y=iq[indices].imag,
                             mode="lines", name="Quadrature (Q)",
                             line={"width": 1.2, "color": "#83a3fd"}))
    fig.update_xaxes(title_text="Time (ms)")
    fig.update_yaxes(title_text="Amplitude (a.u.)")
    return style_figure(fig)
