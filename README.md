# 📡 RF Spectrum Lab

**A Python software-defined-radio-style signal analysis demo.**

Offline RF signal simulation, complex IQ processing, frequency-spectrum analysis, waterfall visualization, and narrowband peak detection. **No SDR hardware required.**

> **Important:** This is an independent educational project about basic RF digital signal processing. It does **not** determine RF protocols or measure calibrated RF power. All built-in RF signals are synthetic.

![RF Spectrum Lab demonstration: spectrum and waterfall](assets/demo_preview.png)

## What it does

- **Generates reproducible complex IQ samples** with circular Gaussian noise, two continuous sinusoidal carriers, and a gated linear-frequency-modulated chirp.
- **Calculates a two-sided power spectral density** with SciPy's Welch method using Hann windows and overlapping segments.
- **Detects narrowband peaks** based on relative spectral excess above the median background and minimum peak prominence.
- **Displays an interactive dashboard** in Streamlit using Plotly: RF spectrum, waterfall (spectrogram), IQ time series, and peak table.
- **Lets you experiment** with sample rate, center frequency, noise, amplitudes, signal positions, FFT size, and detector threshold.
- **Accepts IQ recordings** as one-dimensional complex `.npy` arrays or `.csv` files with `I,Q` columns (up to 8 MB / 262,144 samples); no radio device connection or hardware drivers.
- **Exports results** as a detections CSV, spectrum CSV, JSON report, and a NumPy IQ array.
- **Runs headlessly from the command line** and includes automated tests and GitHub Actions CI.

## 1. Quick start (Windows)

**Easiest option:** after extracting the ZIP, double-click `setup_windows.bat` (installs dependencies) and then `run_windows.bat` (launches the dashboard). Python 3.11+ and an internet connection are required for the first installation. A Finnish getting-started guide is provided in [`ALOITA_TASTA.md`](ALOITA_TASTA.md).

### Manual setup (PowerShell)

Install [Python 3.11 or newer](https://www.python.org/downloads/) and open PowerShell in the project directory.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py
```

The app opens in your browser, usually at **http://localhost:8501**.

If PowerShell blocks script activation, you can skip activation and run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

## 2. Explore the dashboard

1. Leave **Synthetic signals** selected for a ready-to-use demo.
2. Adjust the continuous-tone amplitudes or enable / disable individual emitters.
3. Increase the **Noise RMS** and observe changes in the frequency spectrum.
4. Open **Waterfall / spectrogram** to see the shorter frequency-sweeping chirp.
5. Change **Minimum above-floor power** to see how many narrowband peaks are found.
6. Export a report from the bottom of the dashboard.

Note that the chirp is broadband and may not produce a single stable narrowband peak. Its behavior is best observed in the waterfall display.

## 3. Run a headless simulation

The CLI exports a deterministic capture plus plots and CSV/JSON files:

```bash
python -m rf_analyzer.cli --output outputs/demo
```

Customize the noise, sample rate, or random seed:

```bash
python -m rf_analyzer.cli --sample-rate-mhz 2 --center-mhz 2437 --noise 0.25 --seed 99 --output outputs/noisy
```

Files written to the specified output directory:

| File | Content |
| --- | --- |
| `iq.npy` | Complex baseband IQ samples (NumPy array) |
| `spectrum.csv` | Absolute frequency (Hz), relative power spectral density (dB/Hz) |
| `detections.csv` | Identified local maxima and relative spectral excess |
| `report.json` | Capture settings, noise floor, detections and caveats |
| `preview.png` | Spectrum and waterfall preview |

## 4. Import your own IQ samples

Supported formats: a `.npy` NumPy array containing one-dimensional complex numeric IQ samples, or a UTF-8 `.csv` with two columns named exactly `I` and `Q`:

```csv
I,Q
0.12,-0.34
0.17,0.28
-0.21,0.09
```

Create a compatible synthetic `.npy` file:

```python
import numpy as np

fs = 2_000_000  # samples per second
n = 16_384
t = np.arange(n) / fs
iq = np.exp(2j * np.pi * 175_000 * t).astype(np.complex64)
np.save("sample_capture.npy", iq)
```

In the app, switch to **Upload IQ file**, select the file and enter the correct sample rate and RF center frequency. The center frequency **cannot be inferred from IQ samples**; you must know it from the recording settings. A complex IQ capture is needed to interpret positive and negative baseband offsets unambiguously.

Security precautions: uploads are limited in size, NumPy pickle loading is disabled (`allow_pickle=False`), and only finite numeric 1-D arrays are accepted. Uploaded samples are analyzed in the running app; the application itself makes no network requests to RF hardware.

## 5. Test the project

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check rf_analyzer tests app.py
```

GitHub Actions runs these tests automatically on every push or pull request for Python 3.11 and 3.13.

## DSP implementation notes

The signal model produces idealized **complex baseband samples** (I + jQ) at a sample rate `Fs`. A tone at baseband frequency offset `f` is:

`x[n] = A · exp(j · 2π · f · n / Fs)`

The simulated RF frequency is `RF_center + baseband_offset`, with offsets limited to `(-Fs/2, Fs/2)`.

- **Welch PSD:** SciPy `signal.welch`, two-sided, Hann window, 50% overlap. The median of the frequency-bin dB values is used as a simple noise-floor proxy.
- **Peak detection:** SciPy `signal.find_peaks` with a user-selected threshold over median noise, minimum prominence of 6 dB, and adjustable minimum spacing.
- **Waterfall:** SciPy `signal.spectrogram` with a Hann window and 75% overlap. FFT bins are shifted so negative-frequency offsets appear below the center.
- **Power units:** Plotted PSD values use `10 × log10(Pxx / 1 arbitrary amplitude-unit²/Hz)` and are labeled **relative dB/Hz**. This is **not dBm** because no antenna gain, impedance, reference receiver calibration, or analog RF front-end is modeled. “Above floor” is not an accurate SNR estimate.

### Limitations

- No real RF receiver, demodulator, automatic device fingerprinting, protocol recognition, geolocation, tracking, or drone recognition.
- Synthetic tones and chirps are deliberately simplified relative to real wireless emissions (multipath, fading, RF interference, oscillators, ADC limits, and receiver noise figures are not modeled).
- A median background level is a very simple estimate: it may be inaccurate in heavily occupied or nonstationary bands.
- Frequency peaks are *energy detections*; multiple peaks do not necessarily mean multiple transmitters, and chirps may produce scattered peaks.
- FFT bin width depends on `Fs / FFT_size`; this limits frequency resolution.

## Project layout

```text
rf-spectrum-lab/
├── app.py                      # Streamlit dashboard
├── rf_analyzer/
│   ├── __init__.py
│   ├── simulation.py           # IQ generator + validation
│   ├── analysis.py             # Welch PSD, peak detector, spectrogram
│   ├── plotting.py             # Interactive Plotly figures
│   ├── io.py                   # Import / CSV, JSON, .npy exports
│   └── cli.py                  # Repeatable headless demonstration
├── tests/                      # pytest regression and end-to-end tests
├── assets/demo_preview.png     # Generated screenshot-style CLI preview
├── .streamlit/config.toml      # Dark dashboard theme
├── .github/workflows/tests.yml # CI on push / PR
├── requirements.txt
├── requirements-dev.txt
├── setup_windows.bat / run_windows.bat # Windows installation and launcher
├── ALOITA_TASTA.md             # Finnish user guide
├── LICENSE
└── README.md
```

## Potential future improvements

- Realtime streamed IQ processing from a supported USB SDR receiver (receive-only).
- Quantitative comparison of alternative background / noise estimators.
- Synthetic multipath and fading models, or a simple digital modulation generator.
- A calibrated receiver with documented reference measurements.
- Benchmarking processing throughput for different FFT lengths.

## License

MIT — see [LICENSE](LICENSE).
