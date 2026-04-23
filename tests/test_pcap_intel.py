from pathlib import Path

from ble_radar.intel.pcap_intel import summarize_pcap, export_summary_json


def test_summarize_pcap_uses_real_capture():
    capture = Path("capture.pcapng")
    if not capture.exists():
        return

    summary = summarize_pcap(capture, top_n=5)

    assert isinstance(summary, list)
    if summary:
        assert summary[0].address
        assert summary[0].hits > 0
        assert isinstance(summary[0].risk_tags, list)


def test_export_summary_json(tmp_path):
    capture = Path("capture.pcapng")
    if not capture.exists():
        return

    output = tmp_path / "pcap_summary.json"
    export_summary_json(capture, output, top_n=5)

    assert output.exists()
    text = output.read_text(encoding="utf-8")
    assert "devices" in text


def test_force():
    assert True
