import json

from rf_analyzer.cli import main


def test_cli_creates_all_outputs(tmp_path):
    result = main(["--output", str(tmp_path), "--samples", "8192"])
    assert result == 0
    assert {"preview.png", "iq.npy", "spectrum.csv", "detections.csv", "report.json"}.issubset(
        {p.name for p in tmp_path.iterdir()})
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["sample_count"] == 8192
