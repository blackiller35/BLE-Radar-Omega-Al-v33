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


def test_dashboard_contains_session_catalog_panels(monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setattr(
        dashboard,
        "latest_session_overview",
        lambda: {
            "stamp": "2026-04-17_20-00-00",
            "device_count": 5,
            "critical": 1,
            "watch_hits": 1,
            "tracker_candidates": 2,
            "top_vendor": "TestVendor",
            "top_device_name": "Beacon-One",
            "top_device_score": 72,
        },
    )
    monkeypatch.setattr(
        dashboard,
        "build_session_catalog",
        lambda limit=5: [
            {
                "stamp": "2026-04-17_20-00-00",
                "device_count": 5,
                "critical": 1,
                "watch_hits": 1,
                "tracker_candidates": 2,
                "top_vendor": "TestVendor",
            },
            {
                "stamp": "2026-04-17_19-55-00",
                "device_count": 3,
                "critical": 0,
                "watch_hits": 0,
                "tracker_candidates": 1,
                "top_vendor": "TrackCorp",
            },
        ],
    )

    html = dashboard.render_dashboard_html(SAMPLE_DEVICES, "2026-04-17_20-01-00")

    assert "Latest session overview" in html
    assert "Sessions récentes" in html
    assert "Stamp: 2026-04-17_20-00-00" in html
    assert "Devices: 5" in html
    assert "top_vendor=TestVendor" in html
    assert "top_vendor=TrackCorp" in html


def test_dashboard_handles_empty_session_catalog(monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setattr(
        dashboard,
        "latest_session_overview",
        lambda: {
            "stamp": "unknown",
            "device_count": 0,
            "critical": 0,
            "watch_hits": 0,
            "tracker_candidates": 0,
            "top_vendor": "Unknown",
            "top_device_name": "Inconnu",
            "top_device_score": 0,
        },
    )
    monkeypatch.setattr(dashboard, "build_session_catalog", lambda limit=5: [])

    html = dashboard.render_dashboard_html(SAMPLE_DEVICES, "2026-04-17_20-02-00")

    assert "Latest session overview" in html
    assert "Sessions récentes" in html
    assert "Aucune session récente" in html


def test_save_html_keeps_session_catalog_panels(monkeypatch, tmp_path):
    _patch_common(monkeypatch)
    monkeypatch.setattr(reports, "REPORTS_DIR", tmp_path / "reports")
    reports.REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        dashboard,
        "latest_session_overview",
        lambda: {
            "stamp": "2026-04-17_20-03-00",
            "device_count": 4,
            "critical": 1,
            "watch_hits": 1,
            "tracker_candidates": 1,
            "top_vendor": "TestVendor",
            "top_device_name": "Beacon-One",
            "top_device_score": 72,
        },
    )
    monkeypatch.setattr(
        dashboard,
        "build_session_catalog",
        lambda limit=5: [
            {
                "stamp": "2026-04-17_20-03-00",
                "device_count": 4,
                "critical": 1,
                "watch_hits": 1,
                "tracker_candidates": 1,
                "top_vendor": "TestVendor",
            }
        ],
    )

    path = reports.save_html(SAMPLE_DEVICES, "2026-04-17_20-04-00")
    text = path.read_text(encoding="utf-8")

    assert "Latest session overview" in text
    assert "Sessions récentes" in text
    assert "Stamp: 2026-04-17_20-03-00" in text


def test_readme_mentions_dashboard_session_catalog():
    text = open("README.md", "r", encoding="utf-8").read()

    assert "## Dashboard session catalog" in text
    assert "Latest session overview" in text


def test_project_status_mentions_v047():
    text = open("PROJECT_STATUS.md", "r", encoding="utf-8").read()

    assert "v0.4.7 : session catalog dans le dashboard" in text


def test_changelog_mentions_v047():
    text = open("CHANGELOG.md", "r", encoding="utf-8").read()

    assert "## v0.4.7" in text
    assert "Sessions récentes".lower()[:12] in text.lower() or "dashboard html" in text.lower()
