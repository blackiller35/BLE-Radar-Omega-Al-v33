from ble_radar import dashboard, reports


SAMPLE_DEVICES = [
    {
        "name": "Beacon-One",
        "address": "AA:BB:CC:DD:EE:01",
        "vendor": "TestVendor",
        "profile": "general_ble",
        "rssi": -41,
        "risk_score": 20,
        "follow_score": 5,
        "confidence_score": 55,
        "final_score": 72,
        "alert_level": "critique",
        "seen_count": 4,
        "reason_short": "watch_hit",
        "flags": ["watch"],
        "watch_hit": True,
    },
    {
        "name": "Tracker-Two",
        "address": "AA:BB:CC:DD:EE:02",
        "vendor": "TrackCorp",
        "profile": "tracker_like",
        "rssi": -58,
        "risk_score": 14,
        "follow_score": 8,
        "confidence_score": 31,
        "final_score": 44,
        "alert_level": "moyen",
        "seen_count": 2,
        "reason_short": "tracker",
        "flags": ["follow"],
        "watch_hit": False,
        "possible_suivi": True,
    },
]


def _patch_common(monkeypatch):
    monkeypatch.setattr(dashboard, "load_scan_history", lambda: [])
    monkeypatch.setattr(dashboard, "get_vendor_summary", lambda devices: [("TestVendor", 1), ("TrackCorp", 1)])
    monkeypatch.setattr(dashboard, "get_tracker_candidates", lambda devices: [devices[1]])
    monkeypatch.setattr(dashboard, "list_cases", lambda: [])
    monkeypatch.setattr(dashboard, "latest_session_diff", lambda: {"has_diff": False})
    monkeypatch.setattr(
        dashboard,
        "latest_session_overview",
        lambda: {
            "stamp": "2026-04-17_21-00-00",
            "device_count": 5,
            "critical": 1,
            "watch_hits": 1,
            "tracker_candidates": 2,
            "top_vendor": "TestVendor",
            "top_device_name": "Beacon-One",
            "top_device_score": 72,
        },
    )
    monkeypatch.setattr(dashboard, "build_session_catalog", lambda limit=5: [])


def test_dashboard_contains_artifact_index_panel(monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setattr(
        dashboard,
        "build_artifact_index",
        lambda: {
            "scan_manifests": {"count": 2, "latest": "scan_manifest_x.json"},
            "session_diff_reports": {"count": 1, "latest": "session_diff_x.md"},
            "export_contexts": {"count": 3, "latest": "export_context_x.json"},
            "incident_packs": {"count": 4, "latest": "incident_pack_x"},
        },
    )

    html = dashboard.render_dashboard_html(SAMPLE_DEVICES, "2026-04-17_21-01-00")

    assert "Artifact index" in html
    assert "Scan manifests: 2 | latest=scan_manifest_x.json" in html
    assert "Session diff reports: 1 | latest=session_diff_x.md" in html
    assert "Export contexts: 3 | latest=export_context_x.json" in html
    assert "Incident packs: 4 | latest=incident_pack_x" in html


def test_save_html_keeps_artifact_index_panel(monkeypatch, tmp_path):
    _patch_common(monkeypatch)
    monkeypatch.setattr(reports, "REPORTS_DIR", tmp_path / "reports")
    reports.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        dashboard,
        "build_artifact_index",
        lambda: {
            "scan_manifests": {"count": 2, "latest": "scan_manifest_x.json"},
            "session_diff_reports": {"count": 1, "latest": "session_diff_x.md"},
            "export_contexts": {"count": 3, "latest": "export_context_x.json"},
            "incident_packs": {"count": 4, "latest": "incident_pack_x"},
        },
    )

    path = reports.save_html(SAMPLE_DEVICES, "2026-04-17_21-02-00")
    text = path.read_text(encoding="utf-8")

    assert "Artifact index" in text
    assert "Export contexts: 3 | latest=export_context_x.json" in text


def test_readme_mentions_dashboard_artifact_index():
    text = open("README.md", "r", encoding="utf-8").read()

    assert "## Dashboard artifact index" in text
    assert "Artifact index" in text


def test_project_status_mentions_v102():
    text = open("PROJECT_STATUS.md", "r", encoding="utf-8").read()

    assert "v1.0.2 : artifact index dans le dashboard" in text


def test_changelog_mentions_v102():
    text = open("CHANGELOG.md", "r", encoding="utf-8").read()

    assert "## v1.0.2" in text
    assert "Artifact index".lower()[:12] in text.lower() or "dashboard html" in text.lower()


def test_release_file_mentions_v102():
    text = open("RELEASE_v1.0.2.md", "r", encoding="utf-8").read()

    assert "BLE Radar Omega AI v1.0.2" in text
    assert "Artifact index" in text
